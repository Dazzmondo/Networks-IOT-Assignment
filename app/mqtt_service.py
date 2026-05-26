"""
Purpose:
    Publishes detection events and environmental telemetry to HiveMQ's
    public MQTT broker using paho-mqtt.

    Last Will and Testament pattern is implemented. 
    The broker publishes "offline" automatically if the device disconnects unexpectedly.

    All topics are configured in config.py via MQTT_USER_ID so they are
    unique to deployment.

Background thread:
    paho's loop_start() runs the network loop in a daemon thread.
    This means the main detection loop never blocks waiting for network I/O.
"""

import json
import time
from datetime import datetime

import paho.mqtt.client as mqtt

from app.config import (
    MQTT_BROKER,
    MQTT_PORT,
    MQTT_TOPIC_EVENTS,
    MQTT_TOPIC_ENV,
    MQTT_TOPIC_STATUS,
    MQTT_USER_ID,
)
from app.logger_service import logger


class MQTTService:
    """
    Manages the MQTT connection and provides publish methods.
    """

    def __init__(self):
        self._client = mqtt.Client(client_id=f"{MQTT_USER_ID}-detector")

        # -- Last Will and Testament (LWT) -----------------------------------------------
        # If the device disconnects unexpectedly, the broker publishes "offline"
        # to the status topic automatically.
        self._client.will_set(
            MQTT_TOPIC_STATUS,
            payload="offline",
            qos=1,
            retain=True,
        )

        self._client.on_connect    = self._on_connect
        self._client.on_disconnect = self._on_disconnect

        # -- Connect with retry ------------------------------------------------------------
        self._connect_with_retry()

        # -- Start background network loop (non-blocking) ----------------------------------
        # loop_start() spawns a daemon thread to handle MQTT network I/O in the background.
        self._client.loop_start()

    # -- Private callbacks -----------------------------------------------------------------

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info(f"MQTT connected to {MQTT_BROKER}:{MQTT_PORT}")
            # Publish "online" retained status on successful connection
            client.publish(MQTT_TOPIC_STATUS, "online", qos=1, retain=True)
        else:
            logger.error(f"MQTT connection refused — rc={rc}")

    def _on_disconnect(self, client, userdata, rc):
        if rc != 0:
            logger.warning(f"MQTT unexpected disconnect (rc={rc}). "
                           "Paho will attempt reconnection automatically.")

    def _connect_with_retry(self, max_attempts: int = 5):
        """Connect with exponential back-off on failure."""
        delay = 2
        for attempt in range(1, max_attempts + 1):
            try:
                self._client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
                return
            except Exception as error:
                logger.warning(
                    f"MQTT connect attempt {attempt}/{max_attempts} "
                    f"failed: {error}. Retrying in {delay}s…"
                )
                time.sleep(delay)
                delay = min(delay * 2, 30)
        raise RuntimeError(
            f"Could not connect to MQTT broker {MQTT_BROKER} "
            f"after {max_attempts} attempts."
        )

    # -- Public API ------------------------------------------------------------------------

    def publish_detection(
        self,
        event_name: str,
        label: str,
        confidence: float,
        image_path: str | None = None,
        image_url: str | None  = None,
    ) -> bool:
        """
        Publish a detection event to /<MQTT_USER_ID>/events.
        """
        payload = {
            "event":      event_name,
            "label":      label,
            "confidence": round(confidence, 3),
            "timestamp":  datetime.now().isoformat(timespec="seconds"),
            "image_path": image_path,
            "image_url":  image_url,
        }
        return self._publish(MQTT_TOPIC_EVENTS, payload, qos=1, retain=False)

    def publish_environment(
        self,
        temp: float,
        humidity: float,
        pressure: float,
    ) -> bool:
        """
        Publish SenseHAT environmental telemetry to /<MQTT_USER_ID>/telemetry/environment.
        """
        payload = {
            "userID":   MQTT_USER_ID,
            "temp":     temp,
            "humidity": humidity,
            "pressure": pressure,
            "ts":       int(datetime.now().timestamp()),
        }
        return self._publish(MQTT_TOPIC_ENV, payload, qos=0, retain=True)

    def disconnect(self) -> None:
        """Publish "offline" and disconnect cleanly."""
        try:
            self._client.publish(MQTT_TOPIC_STATUS, "offline", qos=1, retain=True)
            self._client.loop_stop()
            self._client.disconnect()
            logger.info("MQTT disconnected.")
        except Exception as error:
            logger.warning(f"MQTT disconnect error: {error}")

    # -- Private helper --------------------------------------------------------------------

    def _publish(self, topic: str, payload: dict, qos: int, retain: bool) -> bool:
        try:
            result = self._client.publish(
                topic, json.dumps(payload), qos=qos, retain=retain
            )
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"MQTT published → {topic}")
                return True
            else:
                logger.error(f"MQTT publish failed — rc={result.rc} topic={topic}")
                return False
        except Exception as error:
            logger.error(f"MQTT publish exception: {error}")
            return False
