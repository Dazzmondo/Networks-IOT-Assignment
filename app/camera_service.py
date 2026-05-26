"""
Purpose:
    Manages the Pi Camera Module using Picamera2.
    Provides TWO distinct capture modes:

        get_preview_frame()        — low-res continuous stream for motion detection
        capture_detection_image()  — high-quality still image when motion confirmed

Why two modes?
    The major cause of poor image quality on the Pi is using
    video/preview frame settings for final inference images. Video frames
    are optimised for speed — they sacrifice resolution, exposure quality,
    and sharpness. Still images are optimised for quality.

    Motion detection doesn't need detail. 640x480 grayscale frames are
    sufficient for OpenCV contour analysis. Running OpenCV on full
    1920x1080 frames wastes enormous CPU for no benefit.

    The detection image (sent to YOLO, saved to disk, uploaded to Cloudinary)
    should be the highest quality the camera can produce.

Camera quality improvements:
    The original default Picamera2 images were dark and poor quality.
    The following controls are now applied:
        Brightness  — raises overall image brightness
        Contrast    — improves separation between objects and background
        Sharpness   — improves edge definition (helps YOLO accuracy)
        Saturation  — improves colour vibrancy
        AeEnable    — auto-exposure enabled
        AwbEnable   — auto-white-balance enabled

Mode switching:
    Picamera2 supports switching between configurations at runtime using
    switch_mode(). The camera is normally in preview configuration.
    When motion is confirmed, it temporarily switches to still configuration,
    captures one image, then switches back to preview.

Disk protection:
    The images/ folder is pruned on each capture to keep the oldest images
    when MAX_STORED_IMAGES is exceeded. This prevents the Pi SD card filling
    up over time.
"""

import glob
import os
import time
from datetime import datetime

import cv2
import numpy as np
from libcamera import Transform
from picamera2 import Picamera2

from config import (
    CAMERA_BRIGHTNESS,
    CAMERA_CAPTURE_SETTLE,
    CAMERA_CONTRAST,
    CAMERA_SATURATION,
    CAMERA_SHARPNESS,
    CAMERA_WARMUP_SECONDS,
    CAPTURE_HEIGHT,
    CAPTURE_WIDTH,
    IMAGE_SAVE_DIR,
    MAX_STORED_IMAGES,
    STREAM_HEIGHT,
    STREAM_WIDTH,
)
from logger_service import logger


class CameraService:
    """
    Manages the Pi Camera in two modes: preview stream and HQ still capture.

    Usage:
        camera = CameraService()
        frame  = camera.get_preview_frame()          # for motion detection
        path   = camera.capture_detection_image()    # after motion confirmed
        saved  = camera.save_annotated_image(path, boxes, labels, scores)
        camera.release()
    """

    def __init__(self):
        os.makedirs(IMAGE_SAVE_DIR, exist_ok=True)

        # ── Quality controls applied to both modes ────────────────────────────
        self._camera_controls = {
            "AeEnable":   True,              # auto-exposure
            "AwbEnable":  True,              # auto-white-balance
            "Brightness": CAMERA_BRIGHTNESS,
            "Contrast":   CAMERA_CONTRAST,
            "Sharpness":  CAMERA_SHARPNESS,
            "Saturation": CAMERA_SATURATION,
        }

        # ── Initialise Picamera2 ──────────────────────────────────────────────
        try:
            self._camera = Picamera2()

            # Preview config — low resolution, continuous stream for OpenCV.
            self._preview_config = self._camera.create_preview_configuration(
                main={"size": (STREAM_WIDTH, STREAM_HEIGHT),
                      "format": "RGB888"},
                controls=self._camera_controls,
                # The camera is mounted upside down — 180° rotation applied.
                transform=Transform(hflip=True, vflip=True),
            )

            # Still config — high resolution, maximum quality for YOLO/storage.
            self._still_config = self._camera.create_still_configuration(
                main={"size": (CAPTURE_WIDTH, CAPTURE_HEIGHT),
                      "format": "RGB888"},
                controls=self._camera_controls,
                # The camera is mounted upside down — 180° rotation applied.
                transform=Transform(hflip=True, vflip=True),
            )

            # Start in preview mode — this is the default operating state.
            self._camera.configure(self._preview_config)
            self._camera.start()

            logger.info(
                f"Pi Camera started in preview mode "
                f"({STREAM_WIDTH}x{STREAM_HEIGHT}). Warming up…"
            )
            time.sleep(CAMERA_WARMUP_SECONDS)
            logger.info("Camera ready.")

            # Try to enable autofocus if the camera module supports it.
            # (Camera Module 3 supports continuous AF; v2 does not.)
            try:
                from libcamera import controls as lc
                self._camera.set_controls(
                    {"AfMode": lc.AfModeEnum.Continuous}
                )
                logger.info("Continuous autofocus enabled.")
            except Exception:
                logger.debug("Autofocus not available on this camera module.")

        except Exception as error:
            logger.error(f"Camera failed to initialise: {error}")
            raise

        self._in_preview_mode = True

    # ── Public API ────────────────────────────────────────────────────────────

    def get_preview_frame(self) -> np.ndarray | None:
        """
        Capture one low-resolution BGR frame for motion detection.

        Returns a numpy array (H x W x 3, BGR) ready for OpenCV processing.
        This is called continuously in the motion detection loop and must
        be as fast as possible.

        Colour space conversion is applied (RGB → BGR) to produce a frame
        compatible with OpenCV.

        Returns:
            numpy array, or None on failure.
        """
        try:
            frame = self._camera.capture_array()

            # Convert RGBA → BGR if needed (Picamera2 can return RGBA).
            if frame.shape[2] == 4:
                frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
            elif frame.shape[2] == 3:
                # Picamera2 returns RGB; OpenCV expects BGR.
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            return frame

        except Exception as error:
            logger.error(f"Preview frame capture failed: {error}")
            return None

    def capture_detection_image(self) -> str | None:
        """
        Switch to high-resolution still mode, capture one image, and
        switch back to preview mode.

        This is called ONLY when motion has been confirmed by MotionService.
        The quality is suitable for YOLO inference, dashboard display,
        and Cloudinary upload.

        The camera is given CAMERA_CAPTURE_SETTLE seconds after switching
        to still mode to allow AEC and AWB to re-stabilise at the new
        resolution. Without this settle time, the first still image is
        often underexposed or blurry.

        Returns:
            Path to the saved JPEG as a string, or None on failure.
        """
        timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_path = os.path.join(IMAGE_SAVE_DIR, f"detection_{timestamp}.jpg")

        try:
            # Switch to high-quality still configuration.
            self._camera.switch_mode(self._still_config)
            self._in_preview_mode = False

            # Allow AEC/AWB to settle at the new resolution.
            time.sleep(CAMERA_CAPTURE_SETTLE)

            # Capture the still image.
            self._camera.capture_file(image_path)
            logger.info(
                f"HQ still captured "
                f"({CAPTURE_WIDTH}x{CAPTURE_HEIGHT}): {image_path}"
            )

        except Exception as error:
            logger.error(f"HQ still capture failed: {error}")
            return None

        finally:
            # Always return to preview mode so motion monitoring continues.
            try:
                self._camera.switch_mode(self._preview_config)
                self._in_preview_mode = True
            except Exception as error:
                logger.warning(f"Failed to return to preview mode: {error}")

        # Prune old images to protect SD card space.
        self._prune_old_images()

        return image_path

    def save_annotated_image(
        self,
        source_path: str,
        boxes: list,
        labels: list,
        scores: list,
    ) -> str | None:
        """
        Draw bounding boxes and labels onto the detection image and save
        an annotated copy.

        The annotated image is what gets uploaded to Cloudinary and
        displayed on the dashboard — it shows exactly what YOLO detected
        with confidence scores, making results much clearer.

        Args:
            source_path: path to the original (unannotated) detection image.
            boxes:       list of [x1, y1, x2, y2] bounding box coordinates.
            labels:      list of class name strings, one per box.
            scores:      list of confidence floats, one per box.

        Returns:
            Path to the annotated image, or source_path if annotation fails.
        """
        try:
            image = cv2.imread(source_path)
            if image is None:
                logger.warning(f"Could not read image for annotation: {source_path}")
                return source_path

            for box, label, score in zip(boxes, labels, scores):
                x1, y1, x2, y2 = [int(v) for v in box]

                # Colour per class: green for person, blue for dog.
                colour = (0, 255, 0) if label == "person" else (255, 100, 0)

                cv2.rectangle(image, (x1, y1), (x2, y2), colour, 2)

                text       = f"{label} {score:.0%}"
                font       = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.7
                thickness  = 2
                (tw, th), _ = cv2.getTextSize(text, font, font_scale, thickness)

                cv2.rectangle(
                    image,
                    (x1, y1 - th - 8),
                    (x1 + tw + 4, y1),
                    colour,
                    -1,
                )

                cv2.putText(
                    image,
                    text,
                    (x1 + 2, y1 - 4),
                    font,
                    font_scale,
                    (255, 255, 255),
                    thickness,
                )

            base, ext      = os.path.splitext(source_path)
            annotated_path = f"{base}_annotated{ext}"
            cv2.imwrite(annotated_path, image)

            logger.info(f"Annotated image saved: {annotated_path}")
            return annotated_path

        except Exception as error:
            logger.error(f"Image annotation failed: {error}")
            return source_path

    def release(self):
        """Stop the camera and release hardware resources."""
        try:
            self._camera.stop()
            logger.info("Camera released.")
        except Exception as error:
            logger.warning(f"Error releasing camera: {error}")

    # ── Private helpers ───────────────────────────────────────────────────────

    def _prune_old_images(self):
        """
        Delete the oldest images when MAX_STORED_IMAGES is exceeded.
        Protects the Pi SD card from filling up over time.
        """
        try:
            pattern = os.path.join(IMAGE_SAVE_DIR, "detection_*.jpg")
            images  = sorted(glob.glob(pattern))

            if len(images) > MAX_STORED_IMAGES:
                to_delete = images[:len(images) - MAX_STORED_IMAGES]
                for path in to_delete:
                    os.remove(path)
                logger.info(
                    f"Pruned {len(to_delete)} old image(s). "
                    f"{MAX_STORED_IMAGES} retained."
                )
        except Exception as error:
            logger.warning(f"Image pruning failed: {error}")