# Intelligent IoT Pet & Human Detection System

A modular, event-driven IoT computer vision system running on a Raspberry Pi that detects dogs and humans using a pre-trained YOLOv8 model, then sends notifications and logs events across multiple channels simultaneously.

---

## Technologies

| Technology | Purpose |
|---|---|
| Raspberry Pi 4 | Edge computing device running the full IoT pipeline |
| Raspberry Pi OS (Linux) | Operating system for device services and hardware integration |
| Python 3 | Core application logic and service orchestration |
| OpenCV | Motion detection, image preprocessing, and computer vision utilities |
| YOLOv8 (Ultralytics) | Real-time AI object detection for dogs and humans |
| ONNX Runtime | Efficient local inference engine for YOLOv8 model execution |
| Picamera2 | Raspberry Pi Camera Module image capture (CSI interface) |
| Sense HAT | Environmental sensing (temperature, humidity, pressure) and LED feedback |
| Flask | Web server and dashboard backend |
| Jinja2 | HTML template rendering for Flask dashboard pages |
| Gunicorn | Production WSGI server for Render deployment |
| Chart.js | Real-time analytics and dashboard visualisation |
| chartjs-adapter-date-fns | Time-based formatting support for Chart.js time-series graphs |
| Server-Sent Events (SSE) | Live event streaming from Flask server to browser dashboard |
| SQLite | Local embedded database for persistent detection history |
| MongoDB Atlas | Cloud-hosted database for remote analytics and deployment support |
| MongoDB Aggregation Pipeline | Server-side statistical aggregation and hourly analytics |
| Cloudinary | Cloud image hosting for annotated detection images |
| HiveMQ Cloud | MQTT broker for IoT message transport |
| paho-mqtt | Python MQTT client library |
| BlynkLib | Mobile IoT dashboard and push notification integration |
| Docker | Containerised deployment environment |
| Docker Compose | Multi-service container orchestration |
| python-dotenv | Environment variable and configuration management |
| JSON | Structured API responses and MQTT payload formatting |
| REST API | Dashboard data endpoints for detections, analytics, and environment data |
| HTML5 | Dashboard page structure |
| CSS3 | Dashboard styling and responsive layout |
| JavaScript | Frontend dashboard interactivity and live updates |
| EventSource API | Browser-side SSE client for real-time dashboard streaming |
| Threading (Python threading module) | Background SSE worker and concurrent client handling |
| Queue (Python queue module) | Thread-safe communication between SSE worker and clients |
| datetime / timedelta | Time-window analytics and hourly bucket calculations |
| Z-score statistical analysis | Detection anomaly scoring and behavioural trend analysis |
---

## Architecture

```text
SenseHAT + Pi Camera (CSI)
      │
      ▼
CameraService           ← Picamera2 image capture
      │
      ▼
MotionService           ← OpenCV motion detection (Absolute Difference)
      │
      ▼
DetectorService         ← YOLOv8 ONNX inference (COCO dog/person detection)
      │
      ▼
EventManager            ← Central event router (WAL Mode, Cooldown, Z-score Analytics)
      │
      ├─► LEDService              → SenseHAT LED matrix (Blue idle / Green normal / Red alert)
      ├─► CloudinaryService       → Upload annotated frames, get public URL
      ├─► BlynkService (thread)   → Blynk Cloud dashboard + mobile push notifications
      ├─► MQTTService (thread)    → HiveMQ MQTT topic publish (Events & Telemetry)
      ├─► DBService               → Local SQLite detection log & event logging
      └─► EnvDataService          → SenseHAT environmental telemetry (Temp/Humid/Pres)

Flask Dashboard (dashboard.py)
      │
      ├─► DBService               → Reads local detection history (SQLite)
      └─► SSE (/stream)           → Real-time live push updates to frontend Chart.js

MongoDB Atlas (Cloud Mirror)
      │
      └─► Sync (Mirror)           → Syncs with SQLite for historical analytics & cloud backups
```

---

## Features

- **Motion-gated AI detection pipeline** — motion sensor triggers high-quality image capture before YOLO inference, reducing unnecessary processing and improving efficiency on the Raspberry Pi.
- **Still-image detection** — Pi Camera captures JPEG images for YOLOv8 analysis to detect dogs and humans.
- **Dual object classification** — independently tracks both dog and human detections with separate analytics, counters, and notifications.
- **ONNX-accelerated inference** — YOLOv8 exported to ONNX format for faster and lighter CPU inference on edge hardware.
- **Photo on dog detection** — timestamped annotated JPEG archived whenever a dog is confirmed, optionally uploaded to Cloudinary.
- **Bounding-box image annotation** — detected dogs are highlighted with YOLO confidence overlays before upload and storage.
- **Physical LED feedback** — SenseHAT LED matrix shows system states (startup, idle, detection, shutdown) using patterns adapted from module labs.
- **SenseHAT environmental sensing** — temperature, humidity, and pressure captured alongside detections and included in analytics, MQTT telemetry, and Blynk updates.
- **Real-time Flask dashboard** — live web dashboard showing detections, environmental readings, analytics, and detection history.
- **Server-Sent Events (SSE) live updates** — dashboard updates automatically without page refresh using event-stream push architecture.
- **Real-time Chart.js analytics** — interactive hourly detection graphs and environmental trend visualisations.
- **Rolling-average analytics** — computes 24-hour rolling averages to establish baseline detection behaviour.
- **Anomaly detection (Z-score)** — statistical anomaly scoring identifies unusual spikes in activity relative to historical behaviour.
- **Peak activity analysis** — identifies the busiest hourly detection period over the previous 24 hours.
- **MongoDB aggregation pipeline analytics** — server-side hourly bucketing and statistical aggregation when MongoDB Atlas is enabled.
- **SQLite fallback architecture** — system automatically falls back to local SQLite analytics when MongoDB is unavailable.
- **Cloud database deployment support** — MongoDB Atlas allows the Render-hosted dashboard to access live remote data without direct Pi filesystem access.
- **Blynk Cloud dashboard** — live status updates, detection counters, environmental telemetry, and push notifications using BlynkLib.
- **MQTT event publishing** — structured JSON event payloads published to HiveMQ Cloud for detections and telemetry.
- **MQTT telemetry topics** — environmental readings continuously published as lightweight IoT telemetry streams.
- **LWT (Last Will and Testament)** — MQTT broker automatically publishes offline status on unexpected disconnects.
- **REST API endpoints** — JSON APIs expose detections, counts, analytics, environment readings, and service status.
- **Cloud-hosted image access** — detection images accessible remotely through Cloudinary public URLs.
- **Persistent detection history** — SQLite stores label, confidence, timestamps, image paths, cloud URLs, notification status, and environmental readings.
- **Event cooldown system** — prevents repeated notification spam while a subject remains in frame.
- **Threaded background workers** — separate worker thread handles live SSE event broadcasting without blocking Flask routes.
- **Thread-safe event queues** — queue-based architecture safely distributes live updates to multiple connected dashboard clients.
- **Automatic SSE reconnection** — browser EventSource API reconnects automatically if the live dashboard stream drops.
- **Docker containerisation** — reproducible deployment with isolated detector and dashboard services.
- **Gunicorn production deployment** — Flask dashboard deployable to Render using threaded Gunicorn workers.
- **Environment-based configuration** — all configurable settings managed through `.env` variables.
- **Structured logging** — application events and errors written to both stdout and persistent log files.
- **Graceful cloud fallback behaviour** — system continues operating locally if cloud services (MongoDB, MQTT, Cloudinary) become unavailable.
- **Modular service architecture** — detector, analytics, database, MQTT, dashboard, and notification systems separated into independent services for maintainability.

---

## Knowledge Leveraged from Other Modules

### Programming
- Separation of Concerns / Modular Design
- Object-Oriented Programming (Classes, Methods, Encapsulation)
- Exception Handling (`try` / `except`)
- Conditional Logic and Loops
- Functions and Static Methods
- Dictionaries, Lists, Tuples, and Arrays
- File Handling and JSON Processing
- Logging and Debugging
- External Library Integration

### Web Development
- HTML5
- CSS3
- Responsive Layout Design
- CSS Grid and Flexbox
- JavaScript
- Flask Templating (Jinja2)
- JSON Data Handling

### Databases
- SQL
- CRUD Operations
- Database Queries and Filtering
- NoSQL Data Modelling
- MongoDB
- MongoDB Aggregation Pipelines (`$group`, `$avg`, `$sum`, `$dateTrunc`)
- JSON Document Storage

### Computer Systems and Networks
- MQTT Messaging (HiveMQ + `paho-mqtt`)
- Publish/Subscribe Architecture
- Last Will and Testament (LWT)
- Blynk IoT Integration
- Sensor Telemetry Collection
- Raspberry Pi / SenseHAT Integration
- Edge Computing Concepts
- Cloud Deployment (Render)
- Cloudinary Media Hosting

---

## Demo



---

## Project Structure

```
smart-iot-detector/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example              ← copy to .env and fill in your values
├── README.md
│
├── app/
│   ├── main.py               ← detection loop entry point
│   ├── dashboard.py          ← Flask web dashboard (deployable to Render)
│   ├── config.py             ← centralised config (loads .env)
│   ├── events.py             ← named event constants
│   ├── camera_service.py     ← Picamera2 image capture
│   ├── detector_service.py   ← YOLOv8 inference
│   ├── motion_service.py     ← motion detection
│   ├── event_manager.py      ← central event router
│   ├── blynk_service.py      ← BlynkLib socket connection (background thread)
│   ├── mqtt_service.py       ← HiveMQ MQTT publishing (paho loop_start)
│   ├── db_service.py         ← SQLite detection log
│   ├── mongo_service.py      ← MongoDB service for cloud storage/logging
│   ├── analytics.py          ← data aggregation and trends processor
│   ├── led_service.py        ← SenseHAT LED matrix feedback
│   ├── env_data_service.py   ← SenseHAT environmental sensor readings
│   ├── cloudinary_service.py ← Cloudinary image upload
│   ├── logger_service.py     ← shared structured logger
│   └── templates/
│       └── dashboard.html    ← Jinja2 HTML dashboard template
│
├── models/
│   └── yolov8n.onnx          ← download separately (see Setup)
│
├── images/                   ← detection images (git-ignored)
├── logs/                     ← events.log (git-ignored)
└── detections.db             ← SQLite database (git-ignored)
```
---

## Architecture Diagram

![System Architecture Diagram](projectGraphic.png)


---

## Design Decisions & Reflection

### Why BlynkLib?
BlynkLib uses a persistent socket connection and provides `blynk.run()`, `blynk.virtual_write()`, and `blynk.log_event()`. Running `blynk.run()` in a dedicated background thread prevents it from blocking the camera capture loop. It also has a high quality web app and mobile app that makes it easy to set up and monitor your IOT devices.

### Why HiveMQ + paho-mqtt?
HiveMQ is the broker used because test.mosquitto.org wasn't working when I started this assignment. paho-mqtt is the standard Python MQTT client. MQTT alongside Blynk provides a second communication channel, demonstrating multiple IoT protocols.

### Why SenseHAT environmental data?
The SenseHAT enables us to publish temperature, humidity, and pressure alongside detection events provides a richer data stream and demonstrates combined knowledge across module topics.

### Why SQLite?
Zero configuration, single file, survives restarts when volume-mounted. Sufficient for home IoT event volumes. Also consumed by the Flask dashboard.

### Why Flask + Render?
The week 9 lab builds a Flask API on the Pi, and the smart-doorbell lab deploys Flask to Render. Using the same pattern here provides a publicly accessible dashboard and applies two lab skills together.

### Why Docker?
Docker ensures reproducible deployment regardless of host Python version. It also demonstrates containerisation as a self-learned Release 4 technology.

### Why Cloudinary?
Cloudinary is used to make Pi-captured images accessible from the internet. Detection photos are viewable in the Render dashboard and in MQTT payloads, not just stored locally.



### Limitations

- No custom-trained YOLO model — uses general-purpose COCO pretrained weights.
- No multi-camera support.
- SQLite on Render requires a persistent volume or replacement with a cloud database for multi-instance deployments.
- libcamera must be present on the Docker host (Pi OS) for Picamera2 to work inside the container.
- SenseHAT temperature readings can be elevated by the Pi's CPU heat — a calibration offset could be applied in `env_data_service.py`.

### Future Improvements

- MQTT subscription for remote LED control
- Historical analytics charts in the Flask dashboard.
- Edge TPU acceleration (Coral USB) for faster inference.
- Systemd service for automatic startup
- Behavioural classification beyond label detection (e.g. dog urinating).




---

# Setup Guide

This guide walks you through setting up the external accounts, hardware configuration, system software, project structure, dependencies, testing, deployment, and troubleshooting for the **Networks-IOT-Assignment** project.

---

# 📋 Table of Contents

1. [Part 1: External Accounts Setup](#part-1--external-accounts-setup)
2. [Part 2: Raspberry Pi Hardware](#part-2--raspberry-pi-hardware)
3. [Part 3: Pi Software Setup](#part-3--pi-software-setup)
4. [Part 4: Project Setup on the Pi](#part-4--project-setup-on-the-pi)
5. [Part 5: Individual Component Testing](#part-5--individual-component-testing)
6. [Part 6: Running the Full System](#part-6--running-the-full-system)
7. [Part 7: End-to-End Verification Checklist](#part-7--end-to-end-verification-checklist)
8. [Part 8: Blynk Mobile App Configuration (Android)](#part-8--blynk-mobile-app-configuration-android)
9. [Part 9: GitHub Repository Tracking](#part-9--github-repository-tracking)
10. [Part 10: Run with Docker](#part-10--run-with-docker)
11. [Part 11: Deploy Dashboard to Render](#part-11--deploy-dashboard-to-render)
12. [Part 12: Troubleshooting](#part-12--troubleshooting)

---

# PART 1 — External Accounts Setup

> ⚠️ Complete this section on your computer before configuring the Raspberry Pi.

You will need credentials from several external services.

---

## 1.1 Blynk Setup

1. Create an account at `https://blynk.io`
2. Go to:
   - **Developer Zone**
   - **My Templates**
   - **+ New Template**

Configure:

| Setting | Value |
|---|---|
| Name | `IoT Detector` |
| Hardware | `Raspberry Pi` |
| Connection Type | `WiFi` |

### Create Datastreams

Under **Datastreams** → **+ New Datastream** → **Virtual Pin**

| Virtual Pin | Name | Type | Min | Max |
|---|---|---|---|---|
| `V0` | System Status | String | — | — |
| `V1` | Human Count | Integer | `0` | `1000` |
| `V2` | Dog Count | Integer | `0` | `1000` |
| `V3` | Last Detection | String | — | — |
| `V4` | Temperature | Double | `-20` | `80` |
| `V5` | Humidity | Double | `0` | `100` |

### Configure Events

Under **Events & Notifications** → **+ Create Event**

#### Event 1

| Setting | Value |
|---|---|
| Name | `Dog Detected` |
| Event Code | `dog_detected` |
| Push Notifications | Enabled |
| Limit | Once per minute |

#### Event 2

| Setting | Value |
|---|---|
| Name | `Human Detected` |
| Event Code | `human_detected` |
| Push Notifications | Enabled |

> ⚠️ Event codes are case-sensitive and must match exactly.

### Configure Dashboard

Add these widgets to the Blynk Web Dashboard:

| Widget | Datastream |
|---|---|
| Label | `V0` |
| Gauge | `V1` |
| Gauge | `V2` |
| Label | `V3` |
| Gauge / SuperChart | `V4` |
| Gauge / SuperChart | `V5` |

### Create Device

1. Go to **Devices**
2. Click **+ New Device**
3. Choose **From Template**
4. Select `IoT Detector`

Copy the **Auth Token** from **Developer Tools** (`</>`).

Add it to `.env`:

```env
BLYNK_AUTH_TOKEN=your_token_here
```

---

## 1.2 Cloudinary Setup

1. Register at `https://cloudinary.com`
2. Open the dashboard
3. Copy:

| Cloudinary Value | .env Variable |
|---|---|
| Cloud Name | `CLOUDINARY_CLOUD_NAME` |
| API Key | `CLOUDINARY_API_KEY` |
| API Secret | `CLOUDINARY_API_SECRET` |

No folder setup is required.

---

## 1.3 MongoDB Atlas Setup

MongoDB Atlas acts as a cloud mirror of the local SQLite database.

1. Create a free account at `https://cloud.mongodb.com`
2. Create an `M0 Free` cluster
3. Create a database user
4. Allow network access (`0.0.0.0/0` for development)
5. Copy the Python connection string

Example:

```text
mongodb+srv://username:password@cluster.mongodb.net/
```

Add to `.env`:

```env
MONGO_URI=your_connection_string
```

The database and collection are created automatically.

> ℹ️ Leave `MONGO_URI` blank to disable MongoDB support.

---

## 1.4 HiveMQ Setup

No account is required.

The system uses:

```text
broker.hivemq.com
```

Set a unique MQTT user ID in `.env`:

```env
MQTT_USER_ID=your_unique_id
```

---

## 1.5 GitHub Setup

Ensure `.env` is included in `.gitignore` before pushing code.

---

## 1.6 Render Setup

1. Create an account at `https://render.com`
2. Sign in with GitHub
3. Complete deployment later in Part 11

---

# PART 2 — Raspberry Pi Hardware

## Hardware Assembly

### Pi Camera

- Connect the ribbon cable to the CSI port
- Blue side faces the USB ports
- Lock the connector latch firmly

### SenseHAT

- Align with GPIO pins
- Press down evenly
- Do not force the connection

---

# PART 3 — Pi Software Setup

## 3.1 Update System Packages

```bash
sudo apt update && sudo apt upgrade -y
```

---

## 3.2 Install System Dependencies

```bash
sudo apt install -y \
    python3-picamera2 \
    sense-hat \
    git \
    python3-pip \
    mosquitto-clients \
    libgl1 \
    libglib2.0-0
```

---

## 3.3 Configure Git + SSH

### Set Git Identity

```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

### Generate SSH Key

```bash
ssh-keygen -t ed25519 -C "your.email@example.com"
```

### Copy Public Key

```bash
cat ~/.ssh/id_ed25519.pub
```

Add it to:

- GitHub
- Settings
- SSH and GPG Keys

### Verify

```bash
ssh -T git@github.com
```

---

# PART 4 — Project Setup on the Pi

## 4.1 Clone Repository

```bash
cd ~
git clone git@github.com:YOUR_USERNAME/Networks-IOT-Assignment.git
cd Networks-IOT-Assignment
```

---

## 4.2 Create Directories

```bash
mkdir -p app/templates models images logs
```

---

## 4.3 Configure `.gitignore`

```bash
cat > .gitignore << 'EOF'
.env
.venv/
__pycache__/
*.pyc
*.pyo
logs/
images/
detections.db
models/yolov8n.onnx
models/yolov8n.pt
EOF
```

---

## 4.4 Configure Environment Variables

```bash
cp .env.example .env
nano .env
```

Fill in credentials for:

- Blynk
- MQTT
- Cloudinary
- MongoDB Atlas

---

## 4.5 Export YOLOv8 ONNX Model

Run on your laptop:

```bash
pip install ultralytics
```

```bash
python -c "
from ultralytics import YOLO
model = YOLO('yolov8n.pt')
model.export(format='onnx')
"
```

Copy to Pi:

```bash
scp yolov8n.onnx pi@YOUR_PI_IP:~/Networks-IOT-Assignment/models/
```

Verify:

```bash
ls -lh models/
```

---

## 4.6 Create Virtual Environment

```bash
python -m venv .venv --system-site-packages
source .venv/bin/activate
```

---

## 4.7 Install Python Dependencies

```bash
pip install -r requirements.txt
```

Install Blynk separately:

```bash
pip install https://bit.ly/3C0PMVY
```

Clear cache:

```bash
pip cache purge
```

### Verify Installations

```bash
python -c "import onnxruntime"
python -c "import cv2"
python -c "import flask"
python -c "import cloudinary"
python -c "import pymongo"
python -c "import BlynkLib"
```

---

# PART 5 — Individual Component Testing

> ⚠️ Always run from the repository root with the virtual environment active.

```bash
cd ~/Networks-IOT-Assignment
source .venv/bin/activate
```

## 5.1 Test Pi Camera

```bash
python -c "
from picamera2 import Picamera2
import time
cam = Picamera2()
cam.configure(cam.create_still_configuration())
cam.start()
time.sleep(2)
cam.capture_file('test_capture.jpg')
cam.stop()
print('Camera OK')
"
```

## 5.2 Test SenseHAT

```bash
python -c "
from sense_hat import SenseHat
sense = SenseHat()
print(sense.get_temperature())
print(sense.get_humidity())
print(sense.get_pressure())
"
```

## 5.3 Test Environmental Data Service

```bash
PYTHONPATH=. python app/env_data_service.py
```

## 5.4 Test YOLO Detection

```bash
PYTHONPATH=. python -c "
from app.detector_service import DetectorService
d = DetectorService()
print(d.detect('test_capture.jpg'))
"
```

## 5.5 Test MQTT

### Terminal 1

```bash
mosquitto_sub -h broker.hivemq.com -t "/YOUR_MQTT_USER_ID/#" -v
```

### Terminal 2

```bash
mosquitto_pub -h broker.hivemq.com \
  -t "/YOUR_MQTT_USER_ID/events" \
  -m '{"event":"test"}'
```

## 5.6 Test Blynk

```bash
PYTHONPATH=. python -c "
from dotenv import load_dotenv
load_dotenv()
import os, BlynkLib, time
blynk = BlynkLib.Blynk(os.getenv('BLYNK_AUTH_TOKEN'))
for i in range(30):
    blynk.run()
    time.sleep(0.1)
blynk.virtual_write(0, 'TEST OK')
"
```

## 5.7 Test Cloudinary

```bash
PYTHONPATH=. python -c "
from dotenv import load_dotenv
load_dotenv()
from app.cloudinary_service import CloudinaryService
cloud = CloudinaryService()
print(cloud.upload('test_capture.jpg'))
"
```

## 5.8 Test MongoDB Atlas

```bash
PYTHONPATH=. python -c "
from dotenv import load_dotenv
load_dotenv()
from app.mongo_service import MongoService
mongo = MongoService()
print(mongo.is_enabled())
"
```

## 5.9 Test Flask Dashboard

```bash
PYTHONPATH=. python app/dashboard.py
```

Open:

```text
http://YOUR_PI_IP:5000
```

---

# PART 6 — Running the Full System

## 6.1 Start Detection Loop

```bash
PYTHONPATH=. python app/main.py
```

Expected:

```text
[INFO] IoT Pet & Human Detection System — starting up
[INFO] MQTT connected
[INFO] Cloudinary enabled
[INFO] Monitoring for motion...
```

SenseHAT LEDs:

- Blue → Startup
- Green → Monitoring
- Red → Detection

---

## 6.2 Start Dashboard

```bash
PYTHONPATH=. python app/dashboard.py
```

Open:

```text
http://YOUR_PI_IP:5000
```

---

# PART 7 — End-to-End Verification Checklist

## Verify:

### SenseHAT

- Blue on startup
- Green when idle
- Red on detection

### Blynk

- Counters increment
- Status updates
- Push notifications arrive

### MQTT

- `/events` receives JSON
- `/telemetry/environment` receives sensor data

### SQLite

- Detection rows appear

### MongoDB Atlas

- Cloud detections appear

### Cloudinary

- Annotated dog images upload successfully

### Dashboard

- Detection history visible
- API endpoints return valid JSON

---

# PART 8 — Blynk Mobile App Configuration (Android)

Install:

- **Blynk IoT** from Google Play Store

Add widgets:

| Widget | Datastream |
|---|---|
| Labeled Value | `V0` |
| Labeled Value | `V1` |
| Labeled Value | `V2` |
| Labeled Value | `V3` |
| Gauge | `V4` |
| Gauge | `V5` |

Enable push notifications in:

- Android settings
- Blynk app settings

---

# PART 9 — GitHub Repository Tracking

Verify `.env` is ignored:

```bash
git status
```

Commit:

```bash
git add .
git commit -m "Initial project"
git push
```

---

# PART 10 — Run with Docker

> ⚠️ Complete manual setup/testing before using Docker.

## 10.1 Configure Database Path

Update `.env`:

```env
DB_PATH=/app/data/detections.db
```

Create volume directory:

```bash
mkdir -p data
```

## 10.2 Build + Start

```bash
docker compose build
docker compose up
```

Background mode:

```bash
docker compose up -d
```

## 10.3 Useful Commands

```bash
docker compose logs -f
docker compose down
docker compose restart
```

---

# PART 11 — Deploy Dashboard to Render

> ⚠️ MongoDB Atlas must be configured before deployment.

## 11.1 Create Web Service

Go to:

```text
https://render.com
```

Create a new Web Service connected to GitHub.

## 11.2 Render Settings

| Setting | Value |
|---|---|
| Name | `iot-detector-dashboard` |
| Runtime | Python |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn --workers 1 --threads 4 --bind 0.0.0.0:5000 app.dashboard:app` |

## 11.3 Environment Variables

```env
MONGO_URI=
MQTT_USER_ID=
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=
```

## 11.4 Deploy

Click:

```text
Deploy Web Service
```

Render provides a public dashboard URL.

---

# PART 12 — Troubleshooting

## Camera Not Detected

```bash
libcamera-hello --list-cameras
```

Check:

- Ribbon cable orientation
- Camera enabled in `raspi-config`

## SenseHAT Import Error

```bash
python -c "from sense_hat import SenseHat"
```

Recreate virtual environment with:

```bash
python -m venv .venv --system-site-packages
```

## ONNX Model Missing

```bash
ls -lh models/yolov8n.onnx
```

Re-copy from laptop if missing.

## Blynk Connection Failure

```bash
grep BLYNK_AUTH_TOKEN .env
```

Ensure token is correct.

## MongoDB Connection Failure

Check:

- `MONGO_URI`
- Atlas network access rules
- Internet connectivity

## MQTT Messages Missing

```bash
ping broker.hivemq.com
```

Verify topic subscriptions match `MQTT_USER_ID`.

## Render Dashboard Empty

Confirm:

- `main.py` is running on the Pi
- MongoDB Atlas contains detections
- Render environment variables are correct

---

## Supporting Resources

### Documentation & Guides

#### Computer Vision & Object Detection
* [Ultralytics COCO Dataset Guide](https://docs.ultralytics.com/datasets/detect/coco)
* [Ultralytics Dataset Configuration (YAML)](https://github.com/ultralytics/ultralytics/blob/main/ultralytics/cfg/datasets/coco.yaml)
* [Ultralytics Model Export Formats](https://docs.ultralytics.com/modes/export#export-formats)
* [Ultralytics ONNX Integration](https://docs.ultralytics.com/integrations/onnx)
* [OpenCV Main Documentation (v3.4)](https://docs.opencv.org/3.4/pages.html)
* [OpenCV Python Tutorials](https://docs.opencv.org/3.4/d6/d00/tutorial_py_root.html)
* [OpenCV Deep Neural Network (DNN) readNet](https://docs.opencv.org/4.x/d6/d0f/group__dnn.html#ga9d118d70a1659af729d01b10233213ee)
* [Motion Detection using OpenCV on Raspberry Pi 4](https://automaticaddison.com/motion-detection-using-opencv-on-raspberry-pi-4/)
* [Raspberry Pi Picamera2 Official Manual](https://pip-assets.raspberrypi.com/categories/652-raspberry-pi-camera-module-2/documents/RP-008156-DS-2-picamera2-manual.pdf?disposition=inline)

#### ONNX Runtime
* [ONNX Runtime Execution Providers](https://onnxruntime.ai/docs/execution-providers/)
* [ONNX Runtime Python API Summary](https://onnxruntime.ai/docs/api/python/api_summary.html)

#### Databases & Cloud Integration
* [SQLite3 Python Library Documentation](https://docs.python.org/3/library/sqlite3.html)
* [SQLite Write-Ahead Logging (WAL) Mode](https://sqlite.org/wal.html)
* [PyMongo MongoClient Reference](https://pymongo.readthedocs.io/en/stable/api/pymongo/mongo_client.html#pymongo.mongo_client.MongoClient)

#### Networking & Messaging
* [Eclipse Paho MQTT Python Client Documentation](https://eclipse.dev/paho/files/paho.mqtt.python/html/client.html)

#### Containerization
* [Docker Dockerfile Reference](https://docs.docker.com/reference/dockerfile/)
* [Docker Compose File Reference](https://docs.docker.com/reference/compose-file/)

#### Frontend Development & Chart.js
* [Chart.js Getting Started](https://www.chartjs.org/docs/latest/getting-started/)
* [Chart.js Line Charts](https://www.chartjs.org/docs/latest/charts/line.html)
* [Chart.js Bar Charts](https://www.chartjs.org/docs/latest/charts/bar.html)
* [Chart.js Cartesian Time Axes](https://www.chartjs.org/docs/latest/axes/cartesian/time.html)
* [Chart.js Data Updates](https://www.chartjs.org/docs/latest/developers/updates.html)
* [Chart.js Library CDN (v4.4.1)](https://cdnjs.com/libraries/Chart.js/4.4.1)
* [Chart.js date-fns Adapter (NPM)](https://www.npmjs.com/package/chartjs-adapter-date-fns)

#### Web APIs, Security & Backend Streaming
* [MDN Web Docs: Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
* [MDN Web Docs: Using Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events)
* [MDN Web Docs: EventSource API](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)
* [MDN Web Docs: Document Object Model (DOM)](https://developer.mozilla.org/en-US/docs/Web/API/Document_Object_Model)
* [MDN Web Docs: getElementById Method](https://developer.mozilla.org/en-US/docs/Web/API/Document/getElementById)
* [MDN Web Docs: createElement Method](https://developer.mozilla.org/en-US/docs/Web/API/Document/createElement)
* [MDN Web Docs: insertAdjacentHTML Method](https://developer.mozilla.org/en-US/docs/Web/API/Element/insertAdjacentHTML)
* [MDN Web Docs: outerHTML Property](https://developer.mozilla.org/en-US/docs/Web/API/Element/outerHTML)
* [MDN Web Docs: textContent Property vs innerHTML](https://developer.mozilla.org/en-US/docs/Web/API/Node/textContent#differences_from_innerhtml)
* [MDN Web Docs: rel="noopener" Attribute](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Attributes/rel/noopener)
* [MDN Web Docs: beforeunload Window Event](https://developer.mozilla.org/en-US/docs/Web/API/Window/beforeunload_event)
* [WHATWG Living Standard: Server-Sent Events](https://html.spec.whatwg.org/multipage/server-sent-events.html)
* [Flask Documentation: Streaming Patterns](https://flask.palletsprojects.com/en/stable/patterns/streaming/)
* [Flask-CORS Extension Documentation](https://flask-cors.readthedocs.io/en/latest/)
* [Gunicorn Architecture: Thread Configuration Guide](https://gunicorn.org/design/#how-many-threads)
* [Dev.to: Why Python Web Apps Need WSGI and Gunicorn](https://dev.to/techwithhari/why-do-we-need-wsgi-for-python-web-apps-and-why-flask-uses-gunicorn-dm0)
* [OWASP Foundation: Cross-Site Scripting (XSS) Mitigation](https://owasp.org/www-community/attacks/xss/)

#### Python Core & Analytics
* [W3Schools: Python Lambda Keyword](https://www.w3schools.com/python/ref_keyword_lambda.asp)
* [MDN Web Docs: JavaScript Nullish Coalescing Operator (??)](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Nullish_coalescing)
* [Python Standard Library: queue.Queue](https://docs.python.org/3/library/queue.html#queue.Queue)
* [Python Standard Library: collections.defaultdict](https://docs.python.org/3/library/collections.html#collections.defaultdict)
* [Python Standard Library: statistics.stdev](https://docs.python.org/3/library/statistics.html#statistics.stdev)
* [Statistics How To: Z-Score Definition and Calculations](https://www.statisticshowto.com/probability-and-statistics/z-score/)

### Video Tutorials
* [YouTube: OpenCV Tutorial](https://www.youtube.com/watch?v=P4Z8_qe2Cu0)
* [YouTube: Docker Overview](https://www.youtube.com/watch?v=kTp5xUtcalw)
* [YouTube: Docker Full Stack Implementation](https://www.youtube.com/watch?v=lEcULR30-GM)
* [YouTube: Flask Server-Sent Events (SSE) Deep Dive](https://www.youtube.com/watch?v=X_DdIXrmWOo)
* [YouTube: MongoDB Atlas Setup & Python Integration](https://www.youtube.com/watch?v=A_Z1lgZLSNc)
* [YouTube: JavaScript SSE Client Implementation](https://www.youtube.com/watch?v=6zmI_BU18xk)


---

## AI Assistants & LLMs

Large Language Models (LLMs) were utilized during the development of this project. The majority of the code was first written personally based on the Computer Systems & Networks Module lectures and labs, in addition to the knowledge from other modules (Programming, Web Development, Databases), before being tweaked.

The `analytics_service.py` file was largely generated with Claude to help integrating both MongoDB Atlas and the SQLite local database with the Flask web dashboard. New topics like TimeSeries, Z-scores, anomaly scoring, rolling averages, and Server-Sent Events for the real-time monitoring of the web dashboard are mainly focused in that file, though other files also have sections relating to these concepts, such as `dashboard.html`. Resources relating to these topics have been included in the resources section.

### Tools Used
* **Claude** (Anthropic)
* **ChatGPT** (OpenAI)
* **Gemini** (Google)

### Scope of Use
* **Code Analysis**: Various LLMs were used to identify bugs and syntax errors.
* **System Design**: Various LLMs were used to align modular components to ensure functional, end-to-end integration.
* **Documentation**: Gemini was used for structuring and formatting the project `README.md`.
* **Architecture Diagrams**: ChatGPT was used to generate the Architecture Diagram
* **Code Explanation**: Various LLMs were occasionally used to add context and clarify complex logic blocks

*Note: The majority of comments in the source code were written manually or auto-filled via VSCode extensions.*
