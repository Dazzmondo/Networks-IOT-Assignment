"""
Purpose:
    The central event router for the IoT detection system.
    Receives confirmed detections from DetectorService and orchestrates:
      - Cooldown enforcement (no notification spam)
      - SenseHAT LED physical feedback
      - Blynk dashboard updates and push notifications (BlynkLib)
      - MQTT event publishing (HiveMQ)
      - Cloudinary image upload (dog detections — annotated image)
      - SQLite logging of every detection
      - SenseHAT environmental data published alongside detections

    This module only activates AFTER:
        motion detected → HQ image captured → YOLO confirmed dog/person.

    Everything BEFORE this (motion detection, camera, YOLO) is handled
    upstream. EventManager only handles what happens after a valid detection.

Detection dict format (from DetectorService):
    {
        "label":      "dog" | "person",
        "confidence": 0.87,
        "box":        [x1, y1, x2, y2]   ← pixel coords in original image
    }

Dog detection image flow:
    1. camera_service.save_annotated_image() draws bounding box on image.
    2. cloudinary_service.upload() sends annotated image to Cloudinary.
    3. Public URL stored in SQLite and included in MQTT payload.

mqtt_service may be None (broker unreachable at startup).
All calls to self._mqtt are guarded with `if self._mqtt:`.
"""

import time

from logger_service     import logger
from config             import EVENT_COOLDOWN_SECONDS
from events             import DOG_DETECTED_EVENT, HUMAN_DETECTED_EVENT

from blynk_service      import BlynkService
from mqtt_service       import MQTTService
from db_service         import DBService
from led_service        import LEDService
from cloudinary_service import CloudinaryService
from env_data_service   import EnvDataService


class EventManager:
    """
    Routes detection events to all downstream services.

    All dependencies are injected through the constructor.
    mqtt_service may be None.
    """

    def __init__(
        self,
        camera_service,
        blynk_service:      BlynkService,
        mqtt_service,
        db_service:         DBService,
        led_service:        LEDService,
        cloudinary_service: CloudinaryService,
        env_service:        EnvDataService,
    ):
        self._camera    = camera_service
        self._blynk     = blynk_service
        self._mqtt      = mqtt_service
        self._db        = db_service
        self._leds      = led_service
        self._cloud     = cloudinary_service
        self._env       = env_service

        self._last_event_times: dict = {}

    # ── Cooldown ──────────────────────────────────────────────────────────────

    def _cooldown_expired(self, event_name: str) -> bool:
        """Return True if cooldown has elapsed for this event type."""
        now       = time.time()
        last_time = self._last_event_times.get(event_name, 0)

        if now - last_time >= EVENT_COOLDOWN_SECONDS:
            self._last_event_times[event_name] = now
            return True

        remaining = int(EVENT_COOLDOWN_SECONDS - (now - last_time))
        logger.debug(f"Cooldown active for '{event_name}' — {remaining}s remaining.")
        return False

    # ── Main entry point ──────────────────────────────────────────────────────

    def handle_detection(self, detection: dict, current_image_path):
        """
        Route a single YOLO detection to the appropriate handler.

        Args:
            detection:          {"label": str, "confidence": float, "box": list}
            current_image_path: path to the HQ still image that was analysed
        """
        label      = detection["label"]
        confidence = detection["confidence"]
        box        = detection.get("box")    # [x1, y1, x2, y2] or None

        if label == "person":
            self._handle_human_detected(confidence, box, current_image_path)
        elif label == "dog":
            self._handle_dog_detected(confidence, box, current_image_path)

    # ── Per-event handlers ────────────────────────────────────────────────────

    def _handle_human_detected(
        self,
        confidence: float,
        box,
        image_path,
    ):
        """Handle a confirmed human detection."""
        logger.info("Human detected.")

        self._leds.set_detection("person")

        env = self._env.read()

        cooldown_ok = self._cooldown_expired(HUMAN_DETECTED_EVENT)

        blynk_ok = False
        mqtt_ok  = False

        if cooldown_ok:
            # ── Blynk ─────────────────────────────────────────────────────────
            self._blynk.update_status("HUMAN DETECTED")
            self._blynk.increment_human_count()
            self._blynk.send_detection_label("Human")
            self._blynk.write_env_data(env["temp"], env["humidity"])
            self._blynk.log_event(
                HUMAN_DETECTED_EVENT,
                f"Human detected (confidence {confidence:.0%})"
            )
            blynk_ok = True

            # ── MQTT ──────────────────────────────────────────────────────────
            if self._mqtt:
                mqtt_ok = self._mqtt.publish_detection(
                    event_name = HUMAN_DETECTED_EVENT,
                    label      = "person",
                    confidence = confidence,
                    image_path = image_path,
                )
                self._mqtt.publish_environment(
                    temp     = env["temp"],
                    humidity = env["humidity"],
                    pressure = env["pressure"],
                )
            else:
                logger.debug("MQTT not available — skipping human detection publish.")

        # ── SQLite — always log ────────────────────────────────────────────────
        self._db.log_detection(
            label          = "person",
            confidence     = confidence,
            image_path     = image_path,
            blynk_notified = blynk_ok,
            mqtt_published = mqtt_ok,
            temp           = env.get("temp"),
            humidity       = env.get("humidity"),
            pressure       = env.get("pressure"),
        )

    def _handle_dog_detected(
        self,
        confidence: float,
        box,
        image_path,
    ):
        """
        Handle a confirmed dog detection.

        Annotates the detection image with bounding box before uploading
        to Cloudinary and storing the URL in the database.
        """
        logger.info("Dog detected.")

        self._leds.set_detection("dog")

        # ── Annotate the detection image with bounding box ────────────────────
        # Drawing the box on the image makes Cloudinary/dashboard images
        # much more useful — you can see exactly what YOLO identified.
        annotated_path = None
        image_url      = None

        if image_path and self._camera and box:
            annotated_path = self._camera.save_annotated_image(
                source_path = image_path,
                boxes       = [box],
                labels      = ["dog"],
                scores      = [confidence],
            )

        # Upload annotated image to Cloudinary.
        upload_path = annotated_path or image_path
        if upload_path:
            image_url = self._cloud.upload(upload_path)

        env = self._env.read()

        cooldown_ok = self._cooldown_expired(DOG_DETECTED_EVENT)

        blynk_ok = False
        mqtt_ok  = False

        if cooldown_ok:
            # ── Blynk ─────────────────────────────────────────────────────────
            self._blynk.update_status("DOG DETECTED")
            self._blynk.increment_dog_count()
            self._blynk.send_detection_label("Dog")
            self._blynk.write_env_data(env["temp"], env["humidity"])
            self._blynk.log_event(
                DOG_DETECTED_EVENT,
                f"Dog detected (confidence {confidence:.0%})"
            )
            blynk_ok = True

            # ── MQTT ──────────────────────────────────────────────────────────
            if self._mqtt:
                mqtt_ok = self._mqtt.publish_detection(
                    event_name = DOG_DETECTED_EVENT,
                    label      = "dog",
                    confidence = confidence,
                    image_path = annotated_path or image_path,
                    image_url  = image_url,
                )
                self._mqtt.publish_environment(
                    temp     = env["temp"],
                    humidity = env["humidity"],
                    pressure = env["pressure"],
                )
            else:
                logger.debug("MQTT not available — skipping dog detection publish.")

        # ── SQLite — always log ────────────────────────────────────────────────
        self._db.log_detection(
            label          = "dog",
            confidence     = confidence,
            image_path     = annotated_path or image_path,
            image_url      = image_url,
            blynk_notified = blynk_ok,
            mqtt_published = mqtt_ok,
            temp           = env.get("temp"),
            humidity       = env.get("humidity"),
            pressure       = env.get("pressure"),
        )