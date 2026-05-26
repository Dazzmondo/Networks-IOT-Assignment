"""
Purpose:
    Application entry point.

Pipeline (motion-gated):
    1. Continuously read low-resolution preview frames.
    2. MotionService analyses each frame for motion (OpenCV absolute diff).
    3. If no motion: sleep briefly and continue — YOLO never runs.
    4. If motion confirmed: capture one high-quality still image.
    5. Run YOLO ONNX inference on the still image.
    6. Filter detections to target classes (dog, person).
    7. If valid detections: route each through EventManager.

Benefits of this system design:
    - YOLO only runs when something actually moved saving CPU resources
    - HQ still images used for inference (not low-res video frames)
    - Immediate response to movement
    - Prevents Pi overheating from continuous full-load inference
    - Mirrors how real surveillance systems and wildlife cameras work

Services started:
    - LEDService         (SenseHAT LED matrix — blue startup, green idle)
    - CameraService      (Picamera2 preview + HQ still)
    - MotionService      (OpenCV absolute difference motion detection)
    - DetectorService    (ONNX YOLOv8 with NMS)
    - MongoService       (MongoDB Atlas cloud mirror — optional, non-fatal)
    - DBService          (SQLite + optional MongoDB mirror via dual-write)
    - EnvDataService     (SenseHAT temperature/humidity/pressure)
    - BlynkService       (BlynkLib background thread)
    - MQTTService        (paho-mqtt background thread)
    - CloudinaryService  (image upload)
    - EventManager       (routes detections to all services)
"""

import sys
import time

from blynk_service      import BlynkService
from camera_service     import CameraService
from cloudinary_service import CloudinaryService
from config             import MOTION_LOOP_DELAY, TARGET_CLASSES
from db_service         import DBService
from detector_service   import DetectorService
from env_data_service   import EnvDataService
from event_manager      import EventManager
from led_service        import LEDService
from logger_service     import logger
from mongo_service      import MongoService
from motion_service     import MotionService
from mqtt_service       import MQTTService


def main():
    logger.info("=" * 60)
    logger.info("IoT Pet & Human Detection System — starting up")
    logger.info("=" * 60)

    # ── Initialise services ───────────────────────────────────────────────────
    # LEDs go blue (starting up) immediately.
    led_service = LEDService()

    # Camera is critical — exit if unavailable.
    try:
        camera_service = CameraService()
    except Exception as error:
        logger.error(f"Cannot start — camera unavailable: {error}")
        led_service.set_offline()
        sys.exit(1)

    # -- MongoDB Atlas (cloud mirror) ----------------------------------------
    # MongoService is non-fatal — if Atlas is unreachable or unconfigured
    # the system continues with SQLite only.
    mongo_service = MongoService()

    # SQLite is critical — exit if unavailable.
    # DBService receives mongo_service so every successful SQLite write is
    # automatically mirrored to Atlas when MongoDB is connected.
    try:
        db_service = DBService(mongo_service=mongo_service)
    except Exception as error:
        logger.error(f"Cannot start — database unavailable: {error}")
        led_service.set_offline()
        camera_service.release()
        sys.exit(1)

    # Motion detection (pure Python/OpenCV — always available).
    motion_service = MotionService()

    # YOLO (ONNX — requires models/yolov8n.onnx).
    try:
        detector_service = DetectorService()
    except FileNotFoundError as error:
        logger.error(f"Cannot start — {error}")
        led_service.set_offline()
        camera_service.release()
        sys.exit(1)

    # Environmental data — non-fatal if SenseHAT unavailable.
    env_service = EnvDataService()

    # Blynk — starts background thread on construction.
    blynk_service = BlynkService()

    # MQTT — non-fatal if broker unreachable.
    try:
        mqtt_service = MQTTService()
    except Exception as error:
        logger.warning(f"MQTT unavailable: {error}. Continuing without MQTT.")
        mqtt_service = None

    # Cloudinary — gracefully disabled if credentials absent.
    cloudinary_service = CloudinaryService()

    event_manager = EventManager(
        camera_service     = camera_service,
        blynk_service      = blynk_service,
        mqtt_service       = mqtt_service,
        db_service         = db_service,
        led_service        = led_service,
        cloudinary_service = cloudinary_service,
        env_service        = env_service,
    )

    # ── System ready ──────────────────────────────────────────────────────────
    led_service.set_idle()
    blynk_service.update_status("SYSTEM ONLINE")
    logger.info(
        "All services ready. "
        f"Monitoring for motion (target: {', '.join(TARGET_CLASSES)})."
    )
    logger.info(
        f"MongoDB mirror: "
        f"{'enabled' if mongo_service.is_enabled() else 'disabled (SQLite only)'}"
    )

    # ── Main motion-gated detection loop ──────────────────────────────────────
    try:
        while True:

            # Step 1: Read low-resolution preview frame.
            # This is fast and cheap. YOLO only runs when motion is detected.
            preview_frame = camera_service.get_preview_frame()

            if preview_frame is None:
                logger.warning("Preview frame unavailable — skipping cycle.")
                time.sleep(MOTION_LOOP_DELAY)
                continue

            # Step 2: Check for motion
            # OpenCV absolute difference — no YOLO, no disk write, very fast.
            # Returns False most of the time (nothing moving).
            motion_detected = motion_service.detect_motion(preview_frame)

            if not motion_detected:
                time.sleep(MOTION_LOOP_DELAY)
                continue

            # Motion confirmed — YOLO will now run.
            logger.info("Motion confirmed. Capturing detection image…")

            # Step 3: Capture high-quality still image.
            # Switches camera to full-resolution still mode, captures,
            # then returns to preview mode.
            image_path = camera_service.capture_detection_image()

            if image_path is None:
                logger.warning("HQ capture failed — skipping YOLO for this event.")
                continue

            # Step 4: Run YOLO inference with NMS.
            # Only runs on this one image, not every frame.
            detections = detector_service.detect(image_path)

            # Step 5: Filter to target classes.
            # DetectorService already filters internally, but this guard
            # makes the intent explicit and handles any edge cases.
            valid_detections = [
                d for d in detections
                if d["label"] in TARGET_CLASSES
            ]

            if not valid_detections:
                logger.info(
                    "Motion detected but no dog or human found by YOLO — "
                    "continuing monitoring."
                )
                continue

            logger.info(
                f"Target detected: "
                f"{[{k: v for k, v in d.items() if k != 'box'} for d in valid_detections]}"
            )

            # Step 6: Route each detection through EventManager.
            # This triggers Blynk, MQTT, SQLite, Cloudinary, LEDs.
            for detection in valid_detections:
                event_manager.handle_detection(
                    detection          = detection,
                    current_image_path = image_path,
                )

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt — shutting down.")

    except Exception as error:
        logger.error(f"Unhandled exception in main loop: {error}", exc_info=True)

    finally:
        # Graceful shutdown.
        logger.info("Releasing resources…")
        blynk_service.update_status("SYSTEM OFFLINE")
        blynk_service.stop()
        if mqtt_service:
            mqtt_service.disconnect()
        led_service.set_offline()
        camera_service.release()
        logger.info("Shutdown complete.")


if __name__ == "__main__":
    main()