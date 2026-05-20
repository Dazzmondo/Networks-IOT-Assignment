"""
Purpose:
    Reads temperature, humidity, and pressure from the SenseHAT and
    returns them as a structured dictionary.

Why add SenseHAT environmental data?
    The SenseHAT is physically attached to the Raspberry Pi used in this
    project. It provides a built-in source of real sensor data that can
    provide additional real data sources alongside the camera.

Module structure:
    This module uses a single function that returns a dictionary.  The
    if __name__ == "__main__": block allows standalone testing.

    The SenseHAT object is created once at module level and reused, which
    is more efficient than creating a new instance on every call.

Usage:
    from env_data_service import EnvDataService
    env = EnvDataService()
    data = env.read()
    # data → {"temp": 22.5, "humidity": 48.2, "pressure": 1013.4}
"""

from logger_service import logger


class EnvDataService:
    """
    Reads environmental sensor data from the SenseHAT.

    Separating this into its own service means it can be used by both
    the main detection loop (to publish telemetry alongside detections)
    and any Flask dashboard endpoint.
    """

    def __init__(self):
        try:
            # The SenseHAT library is only imported when this service is instantiated.
            # If sense_hat is not installed (e.g. on Render or in the dashboard
            # container), the ImportError is caught and the service degrades
            # gracefully instead of crashing the application.
            from sense_hat import SenseHat
            self._sense = SenseHat()
            logger.info("SenseHAT environmental sensors initialised.")
        except Exception as error:
            logger.warning(f"SenseHAT environmental sensors unavailable: {error}")
            self._sense = None

    def read(self) -> dict:
        """
        Read current temperature, humidity, and pressure.

        Returns:
            dict with keys: "temp" (°C), "humidity" (%), "pressure" (hPa).
            Returns zeros if the SenseHAT is unavailable.
        """
        if self._sense is None:
            return {"temp": 0.0, "humidity": 0.0, "pressure": 0.0}

        try:
            temp     = round(self._sense.get_temperature(), 2)
            humidity = round(self._sense.get_humidity(),    2)
            pressure = round(self._sense.get_pressure(),    2)

            data = {
                "temp":     temp,
                "humidity": humidity,
                "pressure": pressure,
            }
            logger.debug(f"Environmental reading: {data}")
            return data

        except Exception as error:
            logger.error(f"Failed to read environmental data: {error}")
            return {"temp": 0.0, "humidity": 0.0, "pressure": 0.0}


# -- Standalone test -----------------------------
if __name__ == "__main__":
    service = EnvDataService()
    reading = service.read()
    print(f"Temp: {reading['temp']} C  "
          f"Humidity: {reading['humidity']}%  "
          f"Pressure: {reading['pressure']} hPa")
