# =============================================================================
# Builds the IoT Pet & Human Detection System container.
#
# Architecture:
#   This project uses a motion-gated detection pipeline:
#     Picamera2 preview stream → OpenCV motion detection → HQ still capture
#     → → YOLOv8 ONNX inference → EventManager → Blynk/MQTT/SQLite/MongoDB/Cloudinary
#
#   Two services (defined in docker-compose.yml):
#     smart-detector  — main detection loop (requires Pi hardware)
#     dashboard       — Flask web dashboard (no hardware needed)
#
#   Both services share this single image with different startup commands.
#
# No PyTorch:
#   torch (~426MB) is too large for the Raspberry Pi SD card.
#   detector_service.py uses onnxruntime directly with a pre-exported
#   yolov8n.onnx model (12MB). Export on a laptop, copy to models/.
#
# Pi Camera / SenseHAT in Docker:
#   libcamera (used by Picamera2) requires kernel-level access to the
#   Pi's CSI camera. The container mounts /dev from the host and runs
#   in privileged mode so libcamera can find the camera device.
#
# MongoDB:
#   MongoService connects outbound to Atlas over TCP 27017.
#   No inbound ports or additional Docker networking config is required --
#   Atlas is a hosted service and the container connects to it like any
#   other external HTTPS/TCP service.
# =============================================================================

FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# ── Copy requirements from project root first (Docker layer cache) ────────────
WORKDIR /app
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir https://bit.ly/3C0PMVY || \
    pip install --no-cache-dir BlynkLib

# ── Copy only the app/ subfolder contents into /app ───────────────────────────
# "COPY app/ ." copies everything inside app/ directly into WORKDIR (/app),
# so /app/main.py, /app/config.py etc — no app/app nesting.
COPY app/ .

# ── Copy project-level files needed at runtime ────────────────────────────────
# requirements.txt is already there; these are the other root-level files
# the container needs (Dockerfile itself is not needed inside).
COPY .env_example .

# ── Runtime directories ───────────────────────────────────────────────────────
# data/, logs/, images/ sit one level up at the project root on the host
# but are mounted into /app/data etc inside the container (see compose).
# models/ must exist so detector_service.py path check doesn't crash.
RUN mkdir -p logs images data models

# ── PYTHONPATH ────────────────────────────────────────────────────────────────
# WORKDIR is /app and all source files are directly in /app,
# so flat imports (from config import ...) resolve without any extra path.
ENV PYTHONPATH=/app
ENV PROJECT_ROOT=/app

# ── Default command ───────────────────────────────────────────────────────────
CMD ["python", "main.py"]