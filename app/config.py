"""
Purpose:
    Centralises all runtime configuration for the IOT detection system.
    Values are loaded from a .env file so they can be changed without
    modifying source code.

    Every other module imports from here. If a variable name changes,
    it only needs updating in one place.

Coverage:
    - Motion detection (OpenCV absolute difference)
    - Camera (preview stream + HQ still capture)
    - YOLO ONNX detection with NMS
    - Blynk (BlynkLib socket connection)
    - MQTT (HiveMQ)
    - SQLite persistence
    - Cloudinary image hosting
    - Flask dashboard
    - SenseHAT LED feedback colours
    - Event cooldown / spam prevention
    - MongoDB Atlas (cloud mirror)
"""

import os
from dotenv import load_dotenv

# ── Load .env from the project root ──────────────────────────────────────────
# Some of these variables, e.g. camera settings and motion detection thresholds, 
# can be set in the .env file. In cases where a variable is not set, a default value is provided
# in this file's code (e.g. MOTION_MIN_AREA = int(os.getenv("MOTION_MIN_AREA", "3000"))). 
# This allows the system to run with reasonable defaults even if the .env file is missing or incomplete.
# If the user wishes to only use this config.py file without updating the .env file for 
# non-sensitive settings, they can do so — the defaults in this file will be used. 
# If they want to override any of the defaults, they can set environment variables directly in their 
# shell or IDE run configuration, and those will take precedence over the defaults in this file.
load_dotenv()


# ── Motion Detection ──────────────────────────────────────────────────────────
# Absolute difference method — lightweight, deterministic, Pi-friendly.
# These values are tuned for indoor/home environments.

# Minimum contour area (pixels) to count as real motion.
# Smaller values catch subtle movement but increase false positives from
# shadows, flickering lights, and camera noise.
# Increase if too many false triggers; decrease if real movement is missed.
MOTION_MIN_AREA = int(os.getenv("MOTION_MIN_AREA", "3000"))
# Validation to ensure MOTION_MIN_AREA is a positive integer. If zero or negative, set to default of 3000.
if MOTION_MIN_AREA < 1:
    raise ValueError("MOTION_MIN_AREA must be >= 1")


# Pixel difference threshold (0-255). Pixels below this value are considered
# unchanged (background). Higher = less sensitive, lower = more sensitive.
MOTION_THRESHOLD = int(os.getenv("MOTION_THRESHOLD", "25"))
# Validation to ensure MOTION_THRESHOLD is between 0 and 255.
if not 0 <= MOTION_THRESHOLD <= 255:
    raise ValueError("MOTION_THRESHOLD must be between 0 and 255")


# Gaussian blur kernel size for noise reduction before motion detection.
# Must be odd number. Larger = more blur = less noise but less detail.
MOTION_BLUR_SIZE = int(os.getenv("MOTION_BLUR_SIZE", "21"))
# Validation to ensure MOTION_BLUR_SIZE is positive. If zero or negative, set to default of 21.
if MOTION_BLUR_SIZE <= 0:
    raise ValueError("MOTION_BLUR_SIZE must be > 0")
# Validation to ensure MOTION_BLUR_SIZE is odd. If an even number is provided, increment by 1.
if MOTION_BLUR_SIZE % 2 == 0:
    MOTION_BLUR_SIZE += 1


# Number of consecutive frames with motion required before triggering.
# Prevents single-frame noise (shadows, lighting flicker) from triggering.
MOTION_CONFIRMATION_FRAMES = int(os.getenv("MOTION_CONFIRMATION_FRAMES", "2"))
# Validation to ensure MOTION_CONFIRMATION_FRAMES is a positive integer. If zero or negative, set to default of 2.
if MOTION_CONFIRMATION_FRAMES < 1:
    raise ValueError("MOTION_CONFIRMATION_FRAMES must be >= 1")


# Seconds to wait after a confirmed detection before allowing another trigger.
# Prevents one moving dog generating hundreds of events.
MOTION_COOLDOWN_SECONDS = int(os.getenv("MOTION_COOLDOWN_SECONDS", "10"))
# Validation to ensure MOTION_COOLDOWN_SECONDS is a positive integer. If zero or negative, set to default of 10.
if MOTION_COOLDOWN_SECONDS < 1:
    raise ValueError("MOTION_COOLDOWN_SECONDS must be >= 1")

# Seconds between preview frame reads in the motion loop.
# Lower = more responsive but higher CPU. 0.1 = ~10 checks/second.
MOTION_LOOP_DELAY = float(os.getenv("MOTION_LOOP_DELAY", "0.1"))
# Validation to ensure MOTION_LOOP_DELAY is positive. If zero or negative, set to default of 0.1.
if MOTION_LOOP_DELAY <= 0:
    raise ValueError("MOTION_LOOP_DELAY must be > 0")

# ── Camera — Preview Stream (motion detection) ────────────────────────────────
# Low resolution used ONLY for OpenCV motion detection.
# Small and fast — keeps CPU load minimal during idle monitoring.
STREAM_WIDTH  = int(os.getenv("STREAM_WIDTH",  "640"))
STREAM_HEIGHT = int(os.getenv("STREAM_HEIGHT", "480"))
# Validation to ensure stream resolution is positive. If zero or negative, set to default of 640x480.
if STREAM_WIDTH <= 0 or STREAM_HEIGHT <= 0:
    raise ValueError("Stream resolution must be positive")

# ── Camera — HQ Still Capture (YOLO inference + storage) ─────────────────────
# High resolution used ONLY when motion is confirmed.
# This image is what gets sent to YOLO, saved to disk, and uploaded to Cloudinary.
CAPTURE_WIDTH  = int(os.getenv("CAPTURE_WIDTH",  "1920"))
CAPTURE_HEIGHT = int(os.getenv("CAPTURE_HEIGHT", "1080"))
# Validation to ensure capture resolution is positive. If zero or negative, set to default of 1920x1080.
if CAPTURE_WIDTH <= 0 or CAPTURE_HEIGHT <= 0:
    raise ValueError("Capture resolution must be positive")

# Seconds to wait after switching to still config before capturing.
# Allows auto-exposure and auto-white-balance to settle on the new mode.
# Increase if images are still dark or blurry.
CAMERA_CAPTURE_SETTLE = float(os.getenv("CAMERA_CAPTURE_SETTLE", "1.0"))
# Validation to ensure CAMERA_CAPTURE_SETTLE is positive. If zero or negative, set to default of 1.0.
if CAMERA_CAPTURE_SETTLE <= 0:
    raise ValueError("CAMERA_CAPTURE_SETTLE must be > 0")

# Seconds after camera.start() before the first preview frame is read.
# Allows initial AEC/AWB to stabilise.
CAMERA_WARMUP_SECONDS = float(os.getenv("CAMERA_WARMUP_SECONDS", "2.0"))
# Validation to ensure CAMERA_WARMUP_SECONDS is positive. If zero or negative, set to default of 2.0.
if CAMERA_WARMUP_SECONDS <= 0:
    raise ValueError("CAMERA_WARMUP_SECONDS must be > 0")

# ── Camera quality controls ───────────────────────────────────────────────────
# Applied to both stream and still capture via Picamera2 controls.
# Brightness: -1.0 to 1.0 (0.0 is default/neutral). Positive = brighter.
# Contrast:   0.0 to 32.0 (1.0 is default). Higher = more contrast.
# Sharpness:  0.0 to 16.0 (1.0 is default). Higher = sharper edges.
# Saturation: 0.0 to 32.0 (1.0 is default). Higher = more vivid colours.

# Values are read from the .env file as strings, converted to floats, and validated in config.py.
# This ensures that if the user sets invalid values in the .env file, they will be
# caught with a clear error message when the application starts, rather than causing unexpected behaviour later on.
# If a value is missing or invalid in the .env file, a default value is used,
# allowing the system to run with reasonable settings without requiring the user to configure everything.
def _env_float(name: str, default: str) -> float:
    """
    Read a float environment variable with clean error reporting.
    """
    value = os.getenv(name, default)

    try:
        return float(value)
    except ValueError:
        raise ValueError(
            f"{name} must be a valid float (got: {value!r})"
        )


def _clamp(value: float, minimum: float, maximum: float) -> float:
    """
    Clamp a numeric value to a safe range.
    """
    return max(minimum, min(value, maximum))


# Read raw values from environment
CAMERA_BRIGHTNESS = _env_float("CAMERA_BRIGHTNESS", "0.1")
CAMERA_CONTRAST   = _env_float("CAMERA_CONTRAST",   "1.1")
CAMERA_SHARPNESS  = _env_float("CAMERA_SHARPNESS",  "1.2")
CAMERA_SATURATION = _env_float("CAMERA_SATURATION", "1.0")


# Validate and clamp to Picamera2-supported ranges
CAMERA_BRIGHTNESS = _clamp(CAMERA_BRIGHTNESS, -1.0, 1.0)
CAMERA_CONTRAST   = _clamp(CAMERA_CONTRAST,    0.0, 32.0)
CAMERA_SHARPNESS  = _clamp(CAMERA_SHARPNESS,   0.0, 16.0)
CAMERA_SATURATION = _clamp(CAMERA_SATURATION,  0.0, 32.0)


# ── Disk Space Protection ─────────────────────────────────────────────────────
# Maximum number of images to keep in the images/ folder.
# When exceeded, oldest images are deleted automatically.
MAX_STORED_IMAGES = int(os.getenv("MAX_STORED_IMAGES", "500"))
if MAX_STORED_IMAGES <= 0:
    raise ValueError("MAX_STORED_IMAGES must be >= 1")


# ── YOLO ONNX Detection ───────────────────────────────────────────────────────
# Minimum confidence score to accept a detection.
# Detections below this are discarded before NMS.
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.50"))
if CONFIDENCE_THRESHOLD < 0 or CONFIDENCE_THRESHOLD > 1:
    raise ValueError("CONFIDENCE_THRESHOLD must be between 0 and 1")

# IoU (Intersection over Union) threshold for Non-Maximum Suppression.
# Boxes overlapping more than this fraction are considered duplicates.
# Lower = more aggressive suppression (fewer boxes kept).
NMS_THRESHOLD = float(os.getenv("NMS_THRESHOLD", "0.40"))
if NMS_THRESHOLD < 0 or NMS_THRESHOLD > 1:
    raise ValueError("NMS_THRESHOLD must be between 0 and 1")

# YOLO model input size. YOLOv8n expects 640x640.
YOLO_INPUT_SIZE = 640

# COCO classes this project cares about. All other detections are filtered out.
TARGET_CLASSES = {"person", "dog"}

# Whether to draw bounding boxes and labels on saved detection images.
# Strongly recommended — makes the dashboard and Cloudinary images much more useful.
SAVE_ANNOTATED_IMAGES = os.getenv("SAVE_ANNOTATED_IMAGES", "true").lower() == "true"


# ── Blynk ────────────────────────────────────────────────────────────────────
BLYNK_AUTH_TOKEN = os.getenv("BLYNK_AUTH_TOKEN", "")


# ── Event / notification cooldown ────────────────────────────────────────────
# Separate from MOTION_COOLDOWN_SECONDS — this controls how often
# Blynk/MQTT notifications fire, not how often motion is detected.
EVENT_COOLDOWN_SECONDS = int(os.getenv("EVENT_COOLDOWN_SECONDS", "15"))
if EVENT_COOLDOWN_SECONDS < 1:
    raise ValueError("EVENT_COOLDOWN_SECONDS must be >= 1")


# ── MQTT (HiveMQ public broker) ───────────────────────────────────────────────
MQTT_BROKER       = os.getenv("MQTT_BROKER",  "broker.hivemq.com")
MQTT_PORT         = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER_ID      = os.getenv("MQTT_USER_ID", "iot-detector")
MQTT_TOPIC_EVENTS = f"/{MQTT_USER_ID}/events"
MQTT_TOPIC_ENV    = f"/{MQTT_USER_ID}/telemetry/environment"
MQTT_TOPIC_STATUS = f"/{MQTT_USER_ID}/status"


# ── MongoDB Atlas (cloud mirror) ──────────────────────────────────────────────
# MONGO_URI is the full connection string from the Atlas "Connect" dialog.
# Format: mongodb+srv://<user>:<password>@<cluster>.mongodb.net/
#
# Leave MONGO_URI blank to disable MongoDB — the system runs on SQLite only.
# When set, every detection is mirrored to Atlas in addition to SQLite.
# The dashboard reads from MongoDB when available, falling back to SQLite.
MONGO_URI        = os.getenv("MONGO_URI",        "")
MONGO_DB_NAME    = os.getenv("MONGO_DB_NAME",    "iot_detector")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "detections")

# ── Cloudinary image hosting ──────────────────────────────────────────────────
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_API_KEY    = os.getenv("CLOUDINARY_API_KEY",    "")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "")
CLOUDINARY_FOLDER     = os.getenv("CLOUDINARY_FOLDER",     "iot-detector")


# ── SenseHAT LED colours (RGB tuples) ────────────────────────────────────────
LED_GREEN = (0, 255, 0)
LED_RED   = (255, 0, 0)
LED_BLUE  = (0, 0, 255)
LED_WHITE = (255, 255, 255)
LED_OFF   = (0, 0, 0)
LED_DETECTION_HOLD_SECONDS = float(os.getenv("LED_DETECTION_HOLD_SECONDS", "2.0"))
if LED_DETECTION_HOLD_SECONDS <= 0:
    raise ValueError("LED_DETECTION_HOLD_SECONDS must be > 0")


# ── Flask dashboard ───────────────────────────────────────────────────────────
FLASK_HOST  = os.getenv("FLASK_HOST",  "0.0.0.0")
FLASK_PORT  = int(os.getenv("FLASK_PORT", "5000"))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"


# ── File paths and directories ────────────────────────────────────────────────
# PROJECT_ROOT is set to /Networks-IOT-Assignment in the Dockerfile.
# Native: resolved by going two dirname levels up from app/config.py,
#         landing at Networks-IOT-Assignment/ on the Pi filesystem.
# Docker: set explicitly via ENV PROJECT_ROOT=/Networks-IOT-Assignment.
# Both environments resolve data/, logs/, images/, and models/ identically.
BASE_DIR = os.getenv(
    "PROJECT_ROOT",
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

DATA_DIR = os.path.join(BASE_DIR, "data")
LOG_DIR = os.path.join(BASE_DIR, "logs")
IMAGE_DIR = os.path.join(BASE_DIR, "images")
MODEL_DIR = os.path.join(BASE_DIR, "models")

# data/, logs/, and images/ are created automatically on first run.
# models/ is intentionally not created here — yolov8n.onnx must be
# copied manually into models/ before starting the detector.
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)

# SQLite database file path. Used if MONGO_URI is not set.
DB_PATH = os.path.join(DATA_DIR, "detections.db")

IMAGE_SAVE_DIR = IMAGE_DIR

# YOLO ONNX model file path. Must be present for detection to work.
YOLO_MODEL_PATH = os.path.join(MODEL_DIR, "yolov8n.onnx")
if not os.path.exists(YOLO_MODEL_PATH):
    raise FileNotFoundError("YOLO model file not found. Please ensure 'yolov8n.onnx' is present in the models directory.")