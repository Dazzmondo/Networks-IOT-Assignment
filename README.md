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

## Setup Guide

This guide walks you through setting up the external accounts, hardware configuration, system software, project structure, dependencies, testing, end-to-end running, and troubleshooting for the **Networks-IOT-Assignment** project.

---

## 📋 Table of Contents
1. [Part 1: External Accounts Setup](#part-1--external-accounts-setup)
2. [Part 2: Raspberry Pi Hardware](#part-2--raspberry-pi-hardware)
3. [Part 3: Pi Software Setup](#part-3--pi-software-setup)
4. [Part 4: Project Setup on the Pi](#part-4--project-setup-on-the-pi)
5. [Part 5: Individual Component Testing](#part-5--test-each-component-individually)
6. [Part 6: Running the Full System](#part-6--running-the-full-system)
7. [Part 7: End-to-End Verification Checklist](#part-7--end-to-end-verification-checklist)
8. [Part 8: Blynk Mobile App Configuration (Android)](#part-8--blynk-mobile-app-configuration-android)
9. [Part 9: GitHub Repository Tracking](#part-9--github-repository-tracking)
10. [Part 10: Deploy Dashboard to Render](#part-10--deploy-dashboard-to-render)
11. [Part 11: Troubleshooting Technical Matrix](#part-11--troubleshooting-technical-matrix)

---

## PART 1 — External Accounts Setup
> ⚠️ **Important:** Complete this section on your computer before configuring the Raspberry Pi. You will need API credentials from four services.

### 1.1 Blynk Setup
1. **Account Creation:** Sign up for a free account at [blynk.io](https://blynk.io).
2. **Create Template:** Navigate to **Developer Zone** → **My Templates** → **+ New Template**.
   * **Name:** `IoT Detector`
   * **Hardware:** `Raspberry Pi`
   * **Connection Type:** `WiFi`
3. **Configure Datastreams:** Under the **Datastreams** tab, click **+ New Datastream** → **Virtual Pin** for each entry below:


| Virtual Pin | Name | Data Type | Min | Max |
| :--- | :--- | :--- | :--- | :--- |
| `V0` | System Status | String | — | — |
| `V1` | Human Count | Integer | `0` | `1000` |
| `V2` | Dog Count | Integer | `0` | `1000` |
| `V3` | Last Detection | String | — | — |
| `V4` | Temperature | Double | `-20` | `80` |
| `V5` | Humidity | Double | `0` | `100` |

4. **Configure Events:** Under the **Events & Notifications** tab, click **Edit** → **+ Create Event**:
   * **Event 1:**
     * **Type:** Custom Event
     * **Name:** `Dog Detected`
     * **Event Code:** `dog_detected` *(Must be exactly lowercase with underscore)*
     * **Notifications Tab:** Enable push notifications. Set limit to **once per minute**.
   * **Event 2:**
     * **Type:** Custom Event
     * **Name:** `Human Detected`
     * **Event Code:** `human_detected` *(Must be exactly lowercase with underscore)*
     * **Notifications Tab:** Enable push notifications.
5. **Create Automation:**
   * Go to **Automations** → **+ New Automation**.
   * **Trigger:** Event → Select `dog_detected`.
   * **Action:** Send email → Enter your email address.
   * Repeat the process for `human_detected` if desired.
6. **Design Web Dashboard:** Go to the **Web Dashboard** tab → **Edit** and add the following widgets:


| Widget Type | Datastream | Purpose |
| :--- | :--- | :--- |
| **Label** | `V0` | System Status |
| **Gauge** | `V1` | Human Count |
| **Gauge** | `V2` | Dog Count |
| **Label** | `V3` | Last Detected |
| **Gauge / SuperChart** | `V4` | Temperature |
| **Gauge / SuperChart** | `V5` | Humidity |

7. **Deploy Device:** Go to **Devices** → **+ New Device** → **From Template** → Select `IoT Detector` → Click **Create**.
8. **Extract Auth Token:** On your new device page, click the **Developer Tools** icon (`</>`) and copy the **Auth Token**. This string will be assigned to `BLYNK_AUTH_TOKEN` inside your `.env` file.

### 1.2 Cloudinary Setup
1. Register for a free account at [cloudinary.com](https://cloudinary.com).
2. Log in and navigate to your **Dashboard**.
3. Under **Account Details**, copy the following environment strings:
   * **Cloud Name** \(\rightarrow\) `CLOUDINARY_CLOUD_NAME`
   * **API Key** \(\rightarrow\) `CLOUDINARY_API_KEY`
   * **API Secret** \(\rightarrow\) `CLOUDINARY_API_SECRET` *(Click to reveal)*
4. *Note: No backend folder setup is required. The `iot-detector` directory is initialized automatically during the first asset payload transfer.*

### 1.3 HiveMQ Setup
No account registration is required. The system leverages the open-access public endpoint `broker.hivemq.com`. Your data strings remain sandboxed via your unique identifier configuration (`MQTT_USER_ID={USERID}`) mapped inside the local `.env` profile.

### 1.4 GitHub Setup
Ensure your active repository profile contains a robust system filter rule to ensure production credential blocks are never cached or exposed upstream. Ensure `.env` is listed inside your local `.gitignore` rule table before executing upstream commits.

### 1.5 Render Setup
1. Create a platform profile at [render.com](https://render.com) using your active GitHub OAuth profile authorization.
2. *Note: Defer deployment build configurations until application execution has been fully verified locally on the hardware target.*

---

## PART 2 — Raspberry Pi Hardware

### Hardware Interconnect Assembly
1. **Pi Camera:** Insert the structural ribbon data cable directly into the CSI port assembly interface. **Orientation:** The blue insulated strip must face directly toward the USB terminal block array.
2. **Sense HAT:** Align and securely mate the hardware HAT onto the 40-pin GPIO array header block. Press downward firmly and uniformly to avoid bending connection pins.

---

## PART 3 — Pi Software Setup

### 3.1 Update System Repositories
Ensure system base packages are upgraded to runtime parity levels:
```bash
sudo apt update && sudo apt upgrade -y
```

### 3.2 Install Core Native Dependencies
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
*Note: Installing `mosquitto-clients` exposes target endpoints `mosquitto_sub` and `mosquitto_pub` directly to your interactive shell for pipeline tracing operations.*

### 3.3 Set Up Git and SSH Key Authentication
Configure your global environment identification properties:
```bash
git config --global user.name "{USERNAME}"
git config --global user.email "your.email@example.com"
```

Generate a secure ed25519 identity key signature pair:
```bash
ssh-keygen -t ed25519 -C "your.email@example.com"
# Press [Enter] to bypass passphrase security prompts
```

Output the newly generated public authentication token configuration block to screen:
```bash
cat ~/.ssh/id_ed25519.pub
```

* **Action Item:** Copy the terminal output profile chunk, navigate to **GitHub** \(\rightarrow\) **Settings** \(\rightarrow\) **SSH and GPG Keys** \(\rightarrow\) **New SSH Key**, and paste the key.

Verify target transport path access layer clearance to upstream hosts:
```bash
ssh -T git@github.com
# Success output string: "Hi {USERNAME}! You've successfully authenticated..."
```

---

## PART 4 — Project Setup on the Pi

### 4.1 Clone Application Workspace
```bash
cd ~
git clone git@github.com:{USERNAME}/{REPO}.git
cd Networks-IOT-Assignment
```

If the tracking repository context maps to an empty layout tree node structure, build the architecture framework locally manually:
```bash
cd ~
mkdir Networks-IOT-Assignment && cd Networks-IOT-Assignment
git init
git branch -M main
git remote add origin git@github.com:{USERNAME}/{REPO}.git
```

### 4.2 Initialize System Workspace Trees
```bash
mkdir -p app/templates models images logs
```

### 4.3 Workspace Directory Tree Standard
Verify that your target workspace accurately reflects the project structure shown earlier in the README.


### 4.4 Set Up Version Control Exclusions
Generate a configuration workspace exclusion track manifest file using your shell terminal:
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

### 4.5 Set Up Local Environment Configurations
```bash
nano .env
```

Paste your local configurations into the file editor.

*To exit Nano: Press `Ctrl+O` $\rightarrow$ `Enter` to commit, then `Ctrl+X` to close the editor.*

### 4.6 Compile and Deploy ONNX Object Inference Graph
To optimize computational footprints on resource-constrained Pi architectures, compile your network weights model target arrays on your laptop workspace environment host:

```bash
# Execute these commands locally on your laptop workspace machine terminal
pip install ultralytics
python -c "
from ultralytics import YOLO
model = YOLO('yolov8n.pt')
model.export(format='onnx')
print('Done — yolov8n.onnx created')
"
```

Deploy the compiled network asset model tracking module directly over the local network interface structure to the Raspberry Pi:
```bash
# Execute on your laptop terminal (modify identifier targets to map your network)
scp yolov8n.onnx pi@YOUR_PI_IP:~/Networks-IOT-Assignment/models/
```

Confirm that the model file reached the target destination directory safely:
```bash
ls -lh ~/Networks-IOT-Assignment/models/
```

### 4.7 Initialize Virtual Environment Sandbox Context
```bash
cd ~/Networks-IOT-Assignment
python -m venv .venv --system-site-packages
source .venv/bin/activate
```
*Verification standard: The active shell prompt sequence must now clearly display an active `(.venv)` indicator prefix.*

### 4.8 Install Python Package Dependencies
Install packages sequentially to prevent deep-dependency conflicts with core system modules:

```bash
# Step 1: Install core package dependencies
pip install -r requirements.txt 

# Step 2: Install targeted Blynk networking engine components
pip install https://bit.ly/3C0PMVY

# Step 3: Clear transient storage cache spaces to free disk drive overhead
pip cache purge
```

Execute an environment verification sweep across core framework runtime packages:
```bash
python -c "import onnxruntime; print('ONNX OK')"
python -c "import cv2; print('OpenCV OK')"
python -c "import BlynkLib; print('Blynk OK')"
python -c "import paho.mqtt.client; print('MQTT OK')"
python -c "import flask; print('Flask OK')"
python -c "import cloudinary; print('Cloudinary OK')"
python -c "from picamera2 import Picamera2; print('Camera OK')"
python -c "from sense_hat import SenseHat; print('SenseHAT OK')"
```

---

## PART 5 — Test Each Component Individually
> ⚠️ **Prerequisite Execution Rule:** Always ensure that any unit level diagnostics or executable targets run strictly from the repository workspace core directory with the virtual environment layer active.

```bash
cd ~/Networks-IOT-Assignment
source .venv/bin/activate
```
### 5.1 Test the Pi Camera
Verify that the camera hardware initializes correctly and can capture a still frame to disk:
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
print('Camera OK — test_capture.jpg created')
"
ls -lh test_capture.jpg
```

### 5.2 Test the Sense HAT
Verify communication with the Sense HAT sensors and confirm the RGB LED matrix illuminates:
```bash
python -c "
from sense_hat import SenseHat
import time
sense = SenseHat()
print('Temp:', round(sense.get_temperature(), 2))
print('Humidity:', round(sense.get_humidity(), 2))
print('Pressure:', round(sense.get_pressure(), 2))
sense.clear(0, 255, 0)
time.sleep(2)
sense.clear()
print('SenseHAT OK — LEDs should have flashed green')
"
```

### 5.3 Test env_data_service Standalone
Isolate and verify temperature, humidity, and atmospheric pressure:
```bash
python app/env_data_service.py
```
*Verification standard: The terminal must return real-time looping temperature, humidity, and atmospheric pressure data logs.*

### 5.4 Test ONNX Detection
Verify that `onnxruntime` can parse the local compiled graph structure and complete a model inference evaluation pass:
```bash
python -c "
import sys
sys.path.insert(0, 'app')
from detector_service import DetectorService
d = DetectorService()
results = d.detect('test_capture.jpg')
print('Detection OK — results:', results)
"
```

### 5.5 Test MQTT Architecture
Validate real-time pub/sub message transit capabilities by spawning two separate concurrent shell sessions:

* **Terminal 1 (Listener Client):**
  ```bash
  mosquitto_sub -h broker.hivemq.com -t "/userid/#" -v
  ```
* **Terminal 2 (Publisher Client):**
  ```bash
  mosquitto_pub -h broker.hivemq.com \
    -t "/userid/events" \
    -m '{"event":"test","label":"dog","confidence":0.9}'
  ```

*Verification standard: The JSON string submitted in Terminal 2 must instantaneously mirror inside the listener feed array of Terminal 1.*

### 5.6 Test Blynk Cloud Telemetry
Verify network route connectivity to the Blynk SaaS ingestion endpoints by updating virtual pin properties manually:
```bash
python -c "
import sys
sys.path.insert(0, 'app')
import os
os.chdir('$(pwd)')
from dotenv import load_dotenv
load_dotenv()
import BlynkLib, time
token = os.getenv('BLYNK_AUTH_TOKEN')
blynk = BlynkLib.Blynk(token)
print('Connecting to Blynk...')
for i in range(30):
    blynk.run()
    time.sleep(0.1)
blynk.virtual_write(0, 'TEST OK')
for i in range(10):
    blynk.run()
    time.sleep(0.1)
print('Done — check V0 on your Blynk dashboard')
"
```
*Verification standard: Open your Remote Cloud Web Panel. The System Status indicator box mapped to `V0` must now read `TEST OK`.*

### 5.7 Test Cloudinary API Asset Engine
Verify authenticated payload uploads to your cloud-hosted object storage workspace:
```bash
python -c "
import sys
sys.path.insert(0, 'app')
from dotenv import load_dotenv
load_dotenv()
from cloudinary_service import CloudinaryService
cloud = CloudinaryService()
url = cloud.upload('test_capture.jpg')
print('Cloudinary OK — URL:', url)
"
```
*Verification standard: Copy the resulting URL string output and load it inside any external browser interface to check the image delivery.*

### 5.8 Test Flask Dashboard Engine
Test localized web layout compilation threads and operational endpoints:
```bash
python app/dashboard.py &
sleep 2
curl http://localhost:5000/api/counts
curl http://localhost:5000/api/environment
```
Open a browser page on your local home network targeting `http://YOUR_PI_IP:5000`. Once validated, terminate the background test process:
```bash
kill %1
```

---

## PART 6 — Running the Full System

> ⚠️ **Prerequisite Execution Rule:** Always confirm your virtual environment layers are activated before spinning up application execution cycles.

```bash
cd ~/Networks-IOT-Assignment
source .venv/bin/activate
```

### 6.1 Run the Core System Loop
Execute the main engine initialization thread from your primary workspace console window:
```bash
python app/main.py
```
```text
[INFO] IoT Pet & Human Detection System — starting up
[INFO] SenseHAT LED matrix initialised (blue = starting up)
[INFO] Pi Camera started, warming up…
[INFO] Camera ready.
[INFO] Database ready: detections.db
[INFO] Blynk background thread started.
[INFO] MQTT connected to broker.hivemq.com:1883
[INFO] Cloudinary image upload enabled.
[INFO] Loading ONNX model from: .../models/yolov8n.onnx
[INFO] ONNX model loaded.
[INFO] All services ready. Entering detection loop.
```
*Note: The hardware Sense HAT matrix elements will transition through a brief blue startup indication state before locking hard into steady green standby mode.*

### 6.2 Spin Up the Web Dashboard
Execute the interface server app concurrently inside an independent shell terminal window:
```bash
python app/dashboard.py
```
Target browser system view: `http://YOUR_PI_IP:5000`

---

## PART 7 — End-to-End Verification Checklist

Ensure that the following interactions occur seamlessly while `main.py` runs actively:

* **Physical LED Matrix Behavior:**
  * Displays Solid Blue during internal sub-system boots.
  * Transitions to Solid Green when entering standard scanning cycles.
  * Pulses High-Intensity Red for approximately 2 seconds when targeting a valid target class configuration match, then cycles back to Green.
* **Blynk Workspace Matrix Tracking:**
  * Virtual element `V0` displays status flag text reading `SYSTEM ONLINE`.
  * Virtual elements `V4` & `V5` register ambient environment tracking sweeps.
  * Passing in front of the lens triggers a step increase inside counter `V1`, changes the last detection state string on `V3` to `Human`, and updates system tracking label `V0` to display `HUMAN DETECTED`.
* **MQTT Channel Verification Sweep:**
  ```bash
  mosquitto_sub -h broker.hivemq.com -t "/{YOUR_MQTT_USER_ID}/#" -v
  ```
  * Confirm `/{user}/status` maintains an online ping.
  * Confirm `/{user}/events` pushes structured JSON on event triggers.
  * Confirm `/{user}/telemetry/environment` delivers telemetry feeds continuously.
* **SQLite Relational Verification:**
  ```bash
  sqlite3 detections.db "SELECT id, timestamp, label, confidence, blynk_notified, mqtt_published FROM detections ORDER BY id DESC LIMIT 5;"
  ```
* **Cloud Storage File Ingestion:** 
  Review your media library on [cloudinary.com](https://cloudinary.com) inside the target directory path container `/iot-detector` to verify that real-time capture images are matching local detections.
* **Web Dashboard Integrity Checks:** Run localized environment structural parsing validation sweeps via terminal tool parameters:
  ```bash
  curl http://localhost:5000/api/environment
  curl http://localhost:5000/api/counts
  ```

---

## PART 8 — Blynk Mobile App Configuration (Android)

1. Download and install the official **Blynk IoT** package tool through the Google Play Store environment.
2. Sign in with your developer profile account settings.
3. Open your automatically linked `IoT Detector` tile node, select the configuration tool layout view (wrench element icon), and structure your panel layout elements with the matching mapping parameter matrix settings below:


| Mobile Widget Type | Linked Datastream Pin | Custom Target Label |
| :--- | :--- | :--- |
| **Labeled Value** | `V0` | Status |
| **Labeled Value** | `V1` | Humans |
| **Labeled Value** | `V2` | Dogs |
| **Labeled Value** | `V3` | Last Detected |
| **Gauge** | `V4` | Temperature |
| **Gauge** | `V5` | Humidity |

4. Exit out of the design view mode layer parameters interface.
5. **Enable Push Notifications:** Ensure both Android OS app permissions and internal Blynk workspace profile notifications toggle paths are active.
6. **Live Verification:** Run an interaction cycle by presenting a target image profile to the device camera lens array to trigger a push alert delivery payload on the mobile handset.

---

## PART 9 — GitHub Repository Tracking

Before committing any project changes to your upstream workspace, verify your version control block exclusion rule logic:
```bash
cd ~/Networks-IOT-Assignment
source .venv/bin/activate

cat .gitignore | grep .env
# Required output response echo verification string match: .env
```

```bash
git add .
git status
# ⚠️ CAUTION VERIFICATION STEP: Confirm '.env' isn't present within your staged changes list.

git commit -m "Initial project — IoT pet and human detection system"
git push -u origin main
```

For general maintenance code drops moving forward across downstream production revisions, run:
```bash
git add .
git commit -m "Provide a brief description of the structural changes implemented"
git push
```

---

## PART 10 — Deploy Dashboard to Render

1. Open your management panel interface on [render.com](https://render.com) and authenticate through your GitHub profile handle link.
2. Choose **+ New** $\rightarrow$ **Web Service**, then authorize and link your `Networks-IOT-Assignment` tracking repository path.
3. Apply the system runtime configurations precisely as detailed below:


| Configuration Property Block | Designated Value Settings Target |
| :--- | :--- |
| **Name** | `iot-detector-dashboard` |
| **Language** | `Python 3` |
| **Branch** | `main` |
| **Root Directory** | *(Leave entirely blank)* |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn app.dashboard:app` |
| **Region** | `Frankfurt (EU Central)` |
| **Plan** | `Free` |

4. Transcribe your local environment parameter attributes from your private `.env` setup blocks into the Render configuration settings:
   * `MQTT_USER_ID`
   * `CLOUDINARY_CLOUD_NAME`
   * `CLOUDINARY_API_KEY`
   * `CLOUDINARY_API_SECRET`
   * `FLASK_DEBUG` = `false`
   * `DB_PATH` = `detections.db`
5. Click **Deploy Web Service**. The platform will return your public URL stream endpoint string pattern upon building successfully (e.g., `https://iot-detector-dashboard.onrender.com`).

> ℹ️ **Technical Constraint Architecture Warning:** Render's base tier leverages non-persistent ephemeral storage layers. The local database file instance (`detections.db`) is completely initialized back to zero states during platform recycle loops. The cloud layout correctly prints operational data elements during local execution sequences tracking from the target hardware, but remains empty on the web mirror unless bound directly to an external managed cloud database engine. *This limitation is fully documented and satisfies assignment scope criteria.*

---

## PART 11 — Troubleshooting Technical Matrix

* **Camera Hardware Ingestion Failures (`No cameras available`):**
  ```bash
  libcamera-hello --list-cameras
  ```
  *Solution:* Power down your system, verify the ribbon cable alignment inside the CSI slot latch, boot back up, and confirm the interface options setup using the configuration parameters utility (`sudo raspi-config`).
* **Sense HAT Python Namespace Import Errors:**
  ```bash
  python -c "from sense_hat import SenseHat; print('OK')"
  ```
  *Solution:* Confirm your virtual environment setup includes full access rights to system level shared dependencies (`--system-site-packages`). If issues continue to manifest across standard tracks, run `sudo apt install sense-hat`, remove your corrupted directory sandbox container entirely, and run a fresh installation process from scratch.
* **ONNX Engine Runtime Graph Load Failures:**
  ```bash
  ls -lh models/yolov8n.onnx
  ```
  *Solution:* Confirm your object model compilation file sizing registers close to ~12MB. If missing or corrupt, re-export the ONNX matrix elements through your local laptop setup environment using python commands and re-run your terminal network file copy transmission parameters (`scp`).
* **BlynkLib Networking Connection Routing Faults:**
  ```bash
  grep BLYNK_AUTH_TOKEN .env
  ```
  *Solution:* Verify that the alphanumeric string configuration record matches exactly, contains no trailing character space elements, and is assigned without any literal formatting quote structures inside your workspace profile document.
* **Execution Module Resolution Paths Failure Errors (`ModuleNotFoundError`):**
  ```bash
  cd ~/Networks-IOT-Assignment
  source .venv/bin/activate
  python app/main.py
  ```
  *Solution:* Never call tracking scripts directly inside nested script folders (e.g., executing `python main.py` within `/app`). Always run commands targeting the core execution scripts from the workspace main layer directory paths.
* **MQTT Remote Telemetry Message Loss Errors:**
  Verify structural transport layer connectivity using basic ping diagnostic routines:
  ```bash
  ping broker.hivemq.com
  ```
  Keep an open terminal running active target trace listeners (`mosquitto_sub`) to capture and match message payload outputs in real-time while `main.py` processes active execution loops.
* **Missing Blynk Cloud Application Push Alert Dispatches:**
  * Confirm that custom system tracking code properties exactly match `dog_detected` and `human_detected` strings down to all casing and punctuation rules inside the remote administration desk.
  * Verify notification rules logic configurations are set to active mode paths within the remote dashboard parameters console layout.
  * Review system app configuration profiles on your mobile phone to verify your operating system permissions aren't blocking alert delivery channels. Confirm that your developers account traffic does not exceed free-tier capacity limitations.


## PART 12 —  Run with Docker

```bash
docker compose build
docker compose up
# Detection loop + dashboard start together.
# Dashboard available at http://YOUR_PI_IP:5000
```

---

## Supporting Resources

### Documentation & Guides

#### Computer Vision & Object Detection
* [Ultralytics COCO Dataset Guide](https://docs.ultralytics.com/datasets/detect/coco)
* [Ultralytics ONNX Integration](https://docs.ultralytics.com/integrations/onnx)
* [OpenCV Main Documentation (v3.4)](https://docs.opencv.org/3.4/pages.html)
* [OpenCV Python Tutorials](https://docs.opencv.org/3.4/d6/d00/tutorial_py_root.html)
* [Motion Detection using OpenCV on Raspberry Pi 4](https://automaticaddison.com/motion-detection-using-opencv-on-raspberry-pi-4/)

#### ONNX Runtime
* [ONNX Runtime Execution Providers](https://onnxruntime.ai/docs/execution-providers/)
* [ONNX Runtime Python API Summary](https://onnxruntime.ai/docs/api/python/api_summary.html)

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

#### Web APIs & Backend Streaming
* [MDN Web Docs: Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
* [MDN Web Docs: EventSource API](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)
* [MDN Web Docs: Document Object Model (DOM)](https://developer.mozilla.org/en-US/docs/Web/API/Document_Object_Model)
* [MDN Web Docs: insertAdjacentHTML Method](https://developer.mozilla.org/en-US/docs/Web/API/Element/insertAdjacentHTML)
* [WHATWG Living Standard: Server-Sent Events](https://html.spec.whatwg.org/multipage/server-sent-events.html)
* [Flask Documentation: Streaming Patterns](https://flask.palletsprojects.com/en/stable/patterns/streaming/)

#### Python Core
* [W3Schools: Python Lambda Keyword](https://www.w3schools.com/python/ref_keyword_lambda.asp)

### Video Tutorials
* [YouTube: OpenCV Tutorial](https://www.youtube.com/watch?v=P4Z8_qe2Cu0)
* [YouTube: Docker Overview](https://www.youtube.com/watch?v=kTp5xUtcalw)
* [YouTube: Docker Full Stack Implementation](https://www.youtube.com/watch?v=lEcULR30-GM)


https://sqlite.org/wal.html

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
