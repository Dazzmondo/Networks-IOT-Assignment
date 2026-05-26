"""
Purpose:
    Wraps the SenseHAT LED matrix to provide physical feedback on the device.

Why LED feedback?
    Every SenseHAT lab in the module uses the LED matrix to show device
    state visually — green for idle/online, red for an event/detection.

    Adding LED feedback to this project:
      - Demonstrates the physical IoT layer (sensor/device output).
      - Makes it easy to see what the system is doing without a monitor.

Colour convention (matches labs throughout the module):
    GREEN  → system idle, online, running normally
    RED    → detection event (dog or human detected)
    BLUE   → system starting up / initialising
    OFF    → system offline / shut down

Usage:
    from led_service import LEDService
    leds = LEDService()
    leds.set_idle()
    leds.set_detection("dog")
    leds.set_offline()
"""
import threading

from app.config import (
    LED_GREEN,
    LED_RED,
    LED_BLUE,
    LED_OFF,
    LED_DETECTION_HOLD_SECONDS,
)
from app.logger_service import logger


class LEDService:
    """
    Controls the SenseHAT LED matrix to reflect system state.

    A background timer automatically returns the LEDs to idle green
    after a detection colour has been shown for LED_DETECTION_HOLD_SECONDS.
    """

    def __init__(self):
        try:
            # The SenseHAT library is only imported when this service is instantiated.
            # If sense_hat is not installed (e.g. on Render or in the dashboard
            # container), the except block sets self._sense
            # to None and all LED calls become silent no-ops.
            from sense_hat import SenseHat
            self._sense = SenseHat()
            self._sense.clear(LED_BLUE)   # blue = starting up
            logger.info("SenseHAT LED matrix initialised (blue = starting up).")
        except Exception as error:
            # SenseHAT may not be available in some test/CI environments.
            # Log the error but do not crash the application.
            logger.warning(f"SenseHAT LED matrix unavailable: {error}")
            self._sense = None

        self._timer: threading.Timer | None = None

    # -- Public API ---------------------------------------------------------------

    def set_idle(self):
        """
        Set LEDs to idle green.
        Called on system startup.
        """
        self._cancel_timer()
        self._set_colour(LED_GREEN)
        logger.debug("LEDs → green (idle)")

    def set_detection(self, label: str):
        """
        Flash the LEDs red to indicate a detection event, then return
        to green after LED_DETECTION_HOLD_SECONDS.

        Args:
            label: detection class, e.g. "dog" or "person".

        Matches the pattern from shakey.py:
            sense.clear(RED)
            time.sleep(1)
            sense.clear(GREEN)
        The difference is this uses a non-blocking Timer instead of sleep
        so the main detection loop is not stalled.
        """
        self._cancel_timer()
        self._set_colour(LED_RED)
        logger.debug(f"LEDs → red ({label} detected)")

        # Schedule automatic return to idle green without blocking.
        self._timer = threading.Timer(
            LED_DETECTION_HOLD_SECONDS,
            self.set_idle,
        )
        self._timer.daemon = True
        self._timer.start()

    def set_offline(self):
        """Turn LEDs off — used during shutdown."""
        self._cancel_timer()
        self._set_colour(LED_OFF)
        logger.debug("LEDs → off (offline)")

    # -- Private helpers ----------------------------------------------------------

    def _set_colour(self, colour: tuple):
        """Set the entire LED matrix to a single colour."""
        if self._sense:
            try:
                self._sense.clear(colour)
            except Exception as error:
                logger.warning(f"LED colour set failed: {error}")

    def _cancel_timer(self):
        """Cancel any pending return-to-idle timer."""
        if self._timer and self._timer.is_alive():
            self._timer.cancel()
            self._timer = None
