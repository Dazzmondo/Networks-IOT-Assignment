"""
Purpose:
    Configures a single shared logger for the entire application.
    Every other module imports `logger` from here, ensuring a consistent
    format and that all output goes to the same file and console stream.

Why structured logging matters:
    - Provides a timestamped audit trail of detections and errors.
    - Makes debugging easier — grep the log file for specific events.
    - The system records what happened even if you are not watching the terminal.
"""

import logging
import os

from config import LOG_DIR

# Ensure the logs directory exists before configuring the file handler.
os.makedirs(LOG_DIR, exist_ok=True)

# Named logger doesn't depend on root logger config
logger = logging.getLogger("IoTDetector")
logger.setLevel(logging.INFO)

# Only add handlers if none exist yet (prevents duplicate lines on reimport).
if not logger.handlers:
    _formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
 
    # File handler — persistent log
    _file_handler = logging.FileHandler(os.path.join(LOG_DIR, "events.log"))
    _file_handler.setFormatter(_formatter)

    # Stream handler — stdout / Docker logs
    _stream_handler = logging.StreamHandler()
    _stream_handler.setFormatter(_formatter)

    logger.addHandler(_file_handler)
    logger.addHandler(_stream_handler)

# Prevent log records from propagating to the root logger
# (avoids duplicate output if another library configures the root).
logger.propagate = False
