# =============================================================================
# Builds the IoT dashboard container.
#
# The detection loop (main.py) runs natively on the Pi — libcamera cannot
# run inside a Docker container as it requires kernel-level hardware access.
# Run it natively:
#   cd ~/Networks-IOT-Assignment
#   source .venv/bin/activate
#   PYTHONPATH=app python3 app/main.py
#
# The dashboard reads from:
#   - MongoDB Atlas (when MONGO_URI is set in .env)
#   - SQLite via ./data volume mount (local fallback)
# =============================================================================

FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# ── Set project root ──────────────────────────────────────────────────────────
WORKDIR /Networks-IOT-Assignment

# ── Python dependencies ───────────────────────────────────────────────────────
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir https://bit.ly/3C0PMVY || \
    pip install --no-cache-dir BlynkLib

# ── Copy project structure ────────────────────────────────────────────────────
# Copies app/ as a subdirectory so the container mirrors the native layout:
#   /Networks-IOT-Assignment/app/main.py
#   /Networks-IOT-Assignment/app/config.py  etc.
COPY app/ app/

# ── Runtime directories ───────────────────────────────────────────────────────
# data/, logs/, and images/ are created as fallbacks for the container.
# In production they are overridden by the volume mounts in docker-compose.yml.
# models/ must exist so detector_service.py path check doesn't crash
# However, clear instructions that user must create models/ and add yolov8n.onnx
# there before running the container (or locally) are included in the README.
RUN mkdir -p logs images data

# ── Python path ───────────────────────────────────────────────────────────────
# Adds app/ to the module search path so flat imports resolve correctly:
#   from config import ... → /Networks-IOT-Assignment/app/config.py
ENV PYTHONPATH=/Networks-IOT-Assignment/app

# ── PROJECT_ROOT matches WORKDIR ──────────────────────────────────────────────
# config.py uses this to locate data/, logs/, images/, models/
# which all sit directly under the project root.
ENV PROJECT_ROOT=/Networks-IOT-Assignment

# ── Default command ───────────────────────────────────────────────────────────
CMD ["gunicorn", "--workers", "1", "--threads", "4", "--worker-class", "gthread", "--bind", "0.0.0.0:5000", "dashboard:app"]