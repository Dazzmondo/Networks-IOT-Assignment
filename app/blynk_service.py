"""
Purpose:
    Manages the Blynk connection and exposes virtual pin writes and
    event logging to the rest of the application.

Why BlynkLib (not the HTTP API)?
    BlynkLib uses a persistent socket connection to Blynk Cloud.

Virtual pin mapping (configure matching datastreams in Blynk console):
    V0  →  System / detection status text     (Label widget)
    V1  →  Human detection counter            (Gauge)
    V2  →  Dog detection counter              (Gauge)
    V3  →  Last detected label                (Label widget)
    V4  →  Temperature °C                     (Gauge / Chart)
    V5  →  Humidity %                         (Gauge / Chart)

Blynk Events (must match event codes in Blynk console exactly):
    dog_detected
    human_detected
"""

import threading
import time

import BlynkLib

from app.config import BLYNK_AUTH_TOKEN
from app.logger_service import logger


class BlynkService:
    """
    Wraps BlynkLib and runs blynk.run() in a background daemon thread.

    All public methods (virtual_write, log_event, etc.) are safe to call
    from any thread because BlynkLib's internal socket operations are
    protected by its own locking.

    Virtual pin mapping:
        V0  System / detection status text
        V1  Human detection counter
        V2  Dog detection counter
        V3  Last detected label
        V4  Temperature (°C)
        V5  Humidity (%)
 
    Blynk event codes (must match Blynk console exactly):
        dog_detected
        human_detected

    Usage:
        blynk_svc = BlynkService()
        blynk_svc.update_status("SYSTEM ONLINE")
        blynk_svc.log_event("dog_detected", "Dog detected")
        blynk_svc.write_env_data(temp=22.5, humidity=48.2)
        blynk_svc.stop()
    """

    def __init__(self):
        # -- Create BlynkLib instance -------------------------------------------
        self._blynk = BlynkLib.Blynk(BLYNK_AUTH_TOKEN)

        # In-memory counters (reset on restart; SQLite is the persistent store).
        self._human_count = 0
        self._dog_count   = 0

        # -- Run blynk.run() in a background daemon thread -----------------------
        # A daemon thread is automatically killed when the main program exits,
        # so no explicit join() is needed on shutdown.
        self._running = True
        self._thread  = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Blynk background thread started.")

    # -- Background loop (private) ----------------------------------------------

    def _run_loop(self):
        """
        Calls blynk.run() in a tight loop to maintain the connection and process events:
            while True:
                blynk.run()
                sleep(...)

        Includes exponential back-off on exceptions so transient network
        errors do not spin the CPU.
        """
        retry_delay = 2
        while self._running:
            try:
                self._blynk.run()
                retry_delay = 2    # reset back-off on success
                time.sleep(0.05)   # short yield to avoid 100% CPU
            except Exception as error:
                logger.error(f"Blynk run() error: {error}. "
                             f"Retrying in {retry_delay}s…")
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 30)

    # -- Public API ---------------------------------------------------------------

    def virtual_write(self, pin: int, value) -> None:
        """
        Write a value to a Blynk virtual pin.
        Mirrors blynk.virtual_write(pin, value) from the labs.
        """
        try:
            self._blynk.virtual_write(pin, value)
            logger.debug(f"Blynk V{pin} ← {value}")
        except Exception as error:
            logger.error(f"Blynk virtual_write V{pin} failed: {error}")

    def log_event(self, event_code: str, description: str = "") -> None:
        """
        Log a named Blynk event (triggers push notifications / automations).
        The event_code MUST match the event code in the Blynk console exactly (case-sensitive).
        """
        try:
            self._blynk.log_event(event_code, description)
            logger.info(f"Blynk event logged: {event_code}")
        except Exception as error:
            logger.error(f"Blynk log_event '{event_code}' failed: {error}")

    # -- Convenience wrappers (thin layer over virtual_write) ---------------------

    def update_status(self, status_text: str) -> None:
        """Update the system status label (V0)."""
        self.virtual_write(0, status_text)

    def increment_human_count(self) -> int:
        """Increment human counter and push to V1."""
        self._human_count += 1
        self.virtual_write(1, self._human_count)
        return self._human_count

    def increment_dog_count(self) -> int:
        """Increment dog counter and push to V2."""
        self._dog_count += 1
        self.virtual_write(2, self._dog_count)
        return self._dog_count

    def send_detection_label(self, label: str) -> None:
        """Push the last detected label to V3."""
        self.virtual_write(3, label)

    def write_env_data(self, temp: float, humidity: float) -> None:
        """
        Push SenseHAT environmental data to V4 (temp) and V5 (humidity).
        This allows the Blynk dashboard to display live environmental readings
        alongside detection counters.
        """
        self.virtual_write(4, temp)
        self.virtual_write(5, humidity)

    def stop(self) -> None:
        """Signal the background loop to exit cleanly."""
        self._running = False
        logger.info("Blynk service stopped.")
