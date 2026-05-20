# =============================================================================
# Builds the IoT Pet & Human Detection System container.
#
# Architecture:
#   This project uses a motion-gated detection pipeline:
#     Picamera2 preview stream → OpenCV motion detection → HQ still capture
#     → YOLOv8 ONNX inference → EventManager → Blynk/MQTT/SQLite/Cloudinary
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
# =============================================================================

FROM python:3.11-slim

# ── System dependencies ───────────────────────────────────────────────────────
# libgl1, libglib2.0-0 — required by opencv-python-headless
# libatlas-base-dev    — required by numpy on ARM (Pi)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libatlas-base-dev \
    && rm -rf /var/lib/apt/lists/*

# ── Project root ──────────────────────────────────────────────────────────────
WORKDIR /app

# ── Python dependencies ───────────────────────────────────────────────────────
# Copy requirements first — Docker caches this layer separately.
# Only rebuilds on requirements.txt change, not on source code change.
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir https://bit.ly/3C0PMVY || \
    pip install --no-cache-dir BlynkLib

# ── Copy project source ───────────────────────────────────────────────────────
# .dockerignore prevents .env, logs/, images/, detections.db, models/,
# and .venv/ from being included — keeps image lean and secrets safe.
COPY . .

# ── Runtime directories ───────────────────────────────────────────────────────
RUN mkdir -p logs images

# ── Default: run the main detection loop ─────────────────────────────────────
# Override with 'command:' in docker-compose.yml for the dashboard service.
CMD ["python", "app/main.py"]