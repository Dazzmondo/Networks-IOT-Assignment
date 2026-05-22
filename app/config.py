"""
Purpose:
    Centralises ALL runtime configuration for the IoT detection system.
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
load_dotenv()


# ── Motion Detection ──────────────────────────────────────────────────────────
# Absolute difference method — lightweight, deterministic, Pi-friendly.
# These values are tuned for indoor/home environments.

# Minimum contour area (pixels) to count as real motion.
# Smaller values catch subtle movement but increase false positives from
# shadows, flickering lights, and camera noise.
# Increase if too many false triggers; decrease if real movement is missed.
MOTION_MIN_AREA = int(os.getenv("MOTION_MIN_AREA", "3000"))

# Pixel difference threshold (0-255). Pixels below this value are considered
# unchanged (background). Higher = less sensitive, lower = more sensitive.
MOTION_THRESHOLD = int(os.getenv("MOTION_THRESHOLD", "25"))

# Gaussian blur kernel size for noise reduction before motion detection.
# Must be odd number. Larger = more blur = less noise but less detail.
MOTION_BLUR_SIZE = int(os.getenv("MOTION_BLUR_SIZE", "21"))

# Number of consecutive frames with motion required before triggering.
# Prevents single-frame noise (shadows, lighting flicker) from triggering.
MOTION_CONFIRMATION_FRAMES = int(os.getenv("MOTION_CONFIRMATION_FRAMES", "2"))

# Seconds to wait after a confirmed detection before allowing another trigger.
# Prevents one moving dog generating hundreds of events.
MOTION_COOLDOWN_SECONDS = int(os.getenv("MOTION_COOLDOWN_SECONDS", "10"))

# Seconds between preview frame reads in the motion loop.
# Lower = more responsive but higher CPU. 0.1 = ~10 checks/second.
MOTION_LOOP_DELAY = float(os.getenv("MOTION_LOOP_DELAY", "0.1"))


# ── Camera — Preview Stream (motion detection) ────────────────────────────────
# Low resolution used ONLY for OpenCV motion detection.
# Small and fast — keeps CPU load minimal during idle monitoring.
STREAM_WIDTH  = int(os.getenv("STREAM_WIDTH",  "640"))
STREAM_HEIGHT = int(os.getenv("STREAM_HEIGHT", "480"))

# ── Camera — HQ Still Capture (YOLO inference + storage) ─────────────────────
# High resolution used ONLY when motion is confirmed.
# This image is what gets sent to YOLO, saved to disk, and uploaded to Cloudinary.
CAPTURE_WIDTH  = int(os.getenv("CAPTURE_WIDTH",  "1920"))
CAPTURE_HEIGHT = int(os.getenv("CAPTURE_HEIGHT", "1080"))

# Seconds to wait after switching to still config before capturing.
# Allows auto-exposure and auto-white-balance to settle on the new mode.
# Increase if images are still dark or blurry.
CAMERA_CAPTURE_SETTLE = float(os.getenv("CAMERA_CAPTURE_SETTLE", "1.0"))

# Seconds after camera.start() before the first preview frame is read.
# Allows initial AEC/AWB to stabilise.
CAMERA_WARMUP_SECONDS = float(os.getenv("CAMERA_WARMUP_SECONDS", "2.0"))

# ── Camera quality controls ───────────────────────────────────────────────────
# Applied to both stream and still capture via Picamera2 controls.
# Brightness: -1.0 to 1.0 (0.0 is default/neutral). Positive = brighter.
# Contrast:   0.0 to 32.0 (1.0 is default). Higher = more contrast.
# Sharpness:  0.0 to 16.0 (1.0 is default). Higher = sharper edges.
# Saturation: 0.0 to 32.0 (1.0 is default). Higher = more vivid colours.
CAMERA_BRIGHTNESS  = float(os.getenv("CAMERA_BRIGHTNESS",  "0.1"))
CAMERA_CONTRAST    = float(os.getenv("CAMERA_CONTRAST",    "1.1"))
CAMERA_SHARPNESS   = float(os.getenv("CAMERA_SHARPNESS",   "1.2"))
CAMERA_SATURATION  = float(os.getenv("CAMERA_SATURATION",  "1.0"))

# Directory where captured images are saved.
IMAGE_SAVE_DIR = os.getenv(
    "IMAGE_SAVE_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "images"),
)

# ── Disk Space Protection ─────────────────────────────────────────────────────
# Maximum number of images to keep in the images/ folder.
# When exceeded, oldest images are deleted automatically.
MAX_STORED_IMAGES = int(os.getenv("MAX_STORED_IMAGES", "500"))


# ── YOLO ONNX Detection ───────────────────────────────────────────────────────
# Minimum confidence score to accept a detection.
# Detections below this are discarded before NMS.
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.50"))

# IoU (Intersection over Union) threshold for Non-Maximum Suppression.
# Boxes overlapping more than this fraction are considered duplicates.
# Lower = more aggressive suppression (fewer boxes kept).
NMS_THRESHOLD = float(os.getenv("NMS_THRESHOLD", "0.40"))

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


# ── MQTT (HiveMQ public broker) ───────────────────────────────────────────────
MQTT_BROKER       = os.getenv("MQTT_BROKER",  "broker.hivemq.com")
MQTT_PORT         = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER_ID      = os.getenv("MQTT_USER_ID", "iot-detector")
MQTT_TOPIC_EVENTS = f"/{MQTT_USER_ID}/events"
MQTT_TOPIC_ENV    = f"/{MQTT_USER_ID}/telemetry/environment"
MQTT_TOPIC_STATUS = f"/{MQTT_USER_ID}/status"


# ── SQLite persistence ────────────────────────────────────────────────────────
DB_PATH = os.getenv(
    "DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "detections.db"),
)

# ── MongoDB Atlas (cloud mirror) ──────────────────────────────────────────────
# MONGO_URI is the full connection string from the Atlas "Connect" dialog.
# Format: mongodb+srv://<user>:<password>@<cluster>.mongodb.net/
#
# Leave MONGO_URI blank to disable MongoDB — the system runs on SQLite only.
# When set, every detection is mirrored to Atlas in addition to SQLite.
# The Render-deployed dashboard reads from MongoDB when MONGO_URI is set,
# falling back to SQLite API responses otherwise.
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


# ── Flask dashboard ───────────────────────────────────────────────────────────
FLASK_HOST  = os.getenv("FLASK_HOST",  "0.0.0.0")
FLASK_PORT  = int(os.getenv("FLASK_PORT", "5000"))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"