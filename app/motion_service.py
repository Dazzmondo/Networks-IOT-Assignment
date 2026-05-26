"""
Purpose:
    Detects motion in a video frame using the OpenCV Absolute Difference
    method and acts as the first-stage gate before YOLO inference runs.

Why motion detection as a gate?
    Without motion gating, YOLO runs on every captured frame — even when
    the room is completely empty. This wastes CPU, generates false detections
    from still scenes, and contributes to Pi overheating. 
    The correct pipeline is:

        continuous low-resolution stream
              ↓
        OpenCV motion detection (cheap)
              ↓
        motion confirmed?
              ↓ NO → continue monitoring (YOLO never runs)
              ↓ YES → capture HQ still → run YOLO → handle event

Why Absolute Difference over MOG2?
(see source: https://automaticaddison.com/motion-detection-using-opencv-on-raspberry-pi-4/)
    For a stationary indoor camera detecting dogs and humans:
    - Absolute difference is faster and lighter on the Pi
    - MOG2 adapts its background continuously, which can cause it to
      "learn" a slow-moving pet as background and stop detecting it
    - Absolute difference is deterministic and easier to tune
    - MOG2 is better for outdoor scenes with changing lighting

    Option to upgrade to MOG2 later if needed.

Motion confirmation:
    A single frame with motion can be a shadow, light flicker, or camera
    noise. MOTION_CONFIRMATION_FRAMES requires motion to persist across
    consecutive frames before triggering, eliminating most false positives.

Algorithm:
    1. Convert frame to grayscale (colour information not needed for motion)
    2. Apply Gaussian blur (reduces noise, small pixel variations)
    3. Apply morphological closing (fills gaps in detected regions)
    4. Compute absolute difference from stored background frame
    5. Threshold to binary mask (foreground vs background)
    6. Dilate to connect nearby regions
    7. Find contours in the binary mask
    8. Filter contours by minimum area (ignores tiny noise)
    9. If large enough contour found: increment confirmation counter
    10. If confirmation counter reaches threshold AND cooldown elapsed: trigger

Background reset:
    The background frame is initialised on the first call to detect_motion().
    Call reset_background() to force re-initialisation (e.g. after the camera
    moves or lighting changes significantly).
"""

import time
import cv2
import numpy as np

from config import (
    MOTION_MIN_AREA,
    MOTION_THRESHOLD,
    MOTION_BLUR_SIZE,
    MOTION_CONFIRMATION_FRAMES,
    MOTION_COOLDOWN_SECONDS,
)
from logger_service import logger


class MotionService:
    """
    Detects motion using OpenCV absolute frame differencing.

    Usage:
        motion = MotionService()

        # In the main loop:
        frame = camera_service.get_preview_frame()
        if motion.detect_motion(frame):
            # motion confirmed — capture HQ image and run YOLO
    """

    def __init__(self):
        # The background frame captured on first call to detect_motion().
        self._background_frame = None

        # Counter for consecutive frames with detected motion.
        # Motion must persist across this many frames to be considered real.
        self._motion_frame_count = 0

        # Unix timestamp of the last confirmed motion trigger.
        # Used to enforce MOTION_COOLDOWN_SECONDS between triggers.
        self._last_trigger_time = 0.0

        # Morphological kernel for closing gaps in detected regions.
        # Larger kernel = bigger gaps filled. 5x5 is a good starting point.
        self._kernel = np.ones((5, 5), np.uint8)

        logger.info("MotionService initialised (absolute difference method).")

    # ── Public API ────────────────────────────────────────────────────────────

    def detect_motion(self, frame: np.ndarray) -> bool:
        """
        Analyse a preview frame for motion.

        Args:
            frame: BGR numpy array from camera_service.get_preview_frame().
                   Should be low resolution (640x480) for efficiency.

        Returns:
            True  — motion confirmed, YOLO inference should run.
            False — no meaningful motion, continue monitoring.
        """
        if frame is None:
            return False

        # ── Step 1: Pre-process frame ─────────────────────────────────────────
        # Convert to grayscale — motion detection does not need colour.
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Gaussian blur removes high-frequency noise (small pixel variations
        # from camera sensor, compression artefacts, minor lighting changes).
        # MOTION_BLUR_SIZE must be odd. 21x21 is standard for this use case.
        gray = cv2.GaussianBlur(gray, (MOTION_BLUR_SIZE, MOTION_BLUR_SIZE), 0)

        # Morphological closing fills small gaps in the processed frame,
        # making contours more solid and easier to detect.
        gray = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, self._kernel)

        # ── Step 2: Initialise background on first frame ──────────────────────
        if self._background_frame is None:
            self._background_frame = gray
            logger.info("Motion background frame initialised.")
            return False

        # ── Step 3: Compute absolute difference ───────────────────────────────
        # Pixels that have changed significantly vs the background frame.
        frame_delta = cv2.absdiff(self._background_frame, gray)

        # ── Step 4: Threshold to binary mask ─────────────────────────────────
        # Pixels below MOTION_THRESHOLD are set to 0 (background).
        # Pixels at or above are set to 255 (foreground / changed).
        _, thresh = cv2.threshold(
            frame_delta,
            MOTION_THRESHOLD,
            255,
            cv2.THRESH_BINARY,
        )

        # ── Step 5: Dilate to connect nearby foreground regions ───────────────
        # A person walking generates multiple disconnected regions; dilation
        # merges nearby regions into one larger contour.
        thresh = cv2.dilate(thresh, None, iterations=2)

        # ── Step 6: Find contours in the binary mask ──────────────────────────
        contours, _ = cv2.findContours(
            thresh.copy(),
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        # ── Step 7: Filter contours by minimum area ───────────────────────────
        # Tiny contours are noise — shadows, a leaf blowing past a window,
        # minor exposure flicker. MOTION_MIN_AREA filters these out.
        # A dog or person typically produces a contour area of 10,000-50,000+
        # pixels at 640x480 resolution.
        significant_motion = any(
            cv2.contourArea(c) >= MOTION_MIN_AREA
            for c in contours
        )

        # ── Step 8: Motion confirmation counter ───────────────────────────────
        if significant_motion:
            self._motion_frame_count += 1
        else:
            # Reset counter — motion must be consecutive to count.
            self._motion_frame_count = 0
            return False

        # ── Step 9: Require N consecutive frames with motion ──────────────────
        if self._motion_frame_count < MOTION_CONFIRMATION_FRAMES:
            logger.debug(
                f"Motion building... "
                f"({self._motion_frame_count}/{MOTION_CONFIRMATION_FRAMES})"
            )
            return False

        # ── Step 10: Enforce cooldown between triggers ────────────────────────
        now = time.time()
        elapsed = now - self._last_trigger_time

        if elapsed < MOTION_COOLDOWN_SECONDS:
            remaining = int(MOTION_COOLDOWN_SECONDS - elapsed)
            logger.debug(f"Motion cooldown active — {remaining}s remaining.")
            return False

        # ── Motion confirmed ──────────────────────────────────────────────────
        self._last_trigger_time  = now
        self._motion_frame_count = 0    # reset for next event

        logger.info(
            f"Motion confirmed "
            f"(largest contour area approx "
            f"{max(cv2.contourArea(c) for c in contours):.0f}px)"
        )
        return True

    def reset_background(self):
        """
        Force the background frame to be re-captured on the next call
        to detect_motion().

        Call this if:
        - The camera is moved
        - Lighting changes significantly (e.g. lights switched on/off)
        - The system resumes after a long pause
        """
        self._background_frame   = None
        self._motion_frame_count = 0
        logger.info("Motion background reset — will re-initialise on next frame.")