# Intelligent IoT Pet & Human Detection System

A modular, event-driven IoT computer vision system running on a Raspberry Pi that detects dogs and humans using a pre-trained YOLOv8 model, then sends notifications and logs events across multiple channels simultaneously.

---

## Technologies

| Technology | Purpose |
|---|---|
| Raspberry Pi | Edge device |
| Picamera2 | Pi Camera Module still-image capture (CSI port) |
| YOLOv8 (Ultralytics) | AI object detection |
| SenseHAT | LED physical feedback + environmental sensors |
| Docker / Docker Compose | Containerised, reproducible deployment |
| BlynkLib | IoT dashboard and push notifications (socket connection) |
| HiveMQ (MQTT / paho-mqtt) | Lightweight event messaging |
| SQLite | Persistent detection history |
| Flask + Gunicorn | Web dashboard, deployable to Render |
| Cloudinary | Remote image hosting for detection photos |
| Python | Application logic |
| python-dotenv | Environment-based configuration |

---

## Architecture

```
Pi Camera (CSI)
      │
      ▼
CameraService          ← Picamera2 still-image capture
      │
      ▼
DetectorService        ← YOLOv8 inference on image file
      │
      ▼
EventManager           ← Central event router
      │
      ├─► LEDService              → SenseHAT LED matrix (green idle / red detection)
      ├─► CameraService           → save_detection_image() on dog detections
      ├─► CloudinaryService       → upload detection image, get public URL
      ├─► BlynkService (thread)   → Blynk Cloud dashboard + push notifications
      ├─► MQTTService (thread)    → HiveMQ MQTT topic publish
      ├─► DBService               → SQLite detection log
      └─► EnvDataService          → SenseHAT temperature / humidity / pressure

Flask Dashboard (dashboard.py)
      │
      └─► DBService               → reads detection history from SQLite
                                    serves /api/environment (week 9 lab pattern)
```

---

## Features

- **Still-image detection** — Pi Camera captures a JPEG every 2 seconds; YOLOv8 analyses it for dogs and humans.
- **Photo on dog detection** — a timestamped JPEG is archived every time a dog is confirmed, and optionally uploaded to Cloudinary.
- **Physical LED feedback** — SenseHAT LED matrix shows blue (starting), green (idle), red (detection), off (shutdown). Follows the exact pattern from the module labs.
- **SenseHAT environmental data** — temperature, humidity, and pressure are read alongside detections and published to Blynk (V4/V5) and MQTT telemetry topic.
- **Blynk Cloud dashboard** — live status, detection counters (V0–V5), and push notifications via BlynkLib (socket connection, background thread).
- **MQTT event publishing** — JSON payloads published to HiveMQ on detection events and environmental telemetry, following the topic naming from the MQTT lab.
- **LWT (Last Will and Testament)** — broker publishes `offline` automatically if the device disconnects unexpectedly (MQTT lab pattern).
- **SQLite persistence** — every detection (label, confidence, image path, Cloudinary URL, SenseHAT readings, timestamp) is logged to `detections.db`.
- **Flask web dashboard** — HTML dashboard with recent detections, counts, and Cloudinary images; API endpoints; deployable to Render.
- **Event cooldown** — prevents notification spam when a subject stays in frame.
- **Docker containerisation** — reproducible deployment; detector and dashboard run as separate services.
- **Structured logging** — all events written to `logs/events.log` and stdout.
- **Environment-based configuration** — all tuneable values in `.env`.

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

- MQTT subscription for remote LED control (matching the week 9 lab exercise).
- Historical analytics charts in the Flask dashboard.
- Edge TPU acceleration (Coral USB) for faster inference.
- Systemd service for automatic startup (matching the week 9 lab systemd section).
- Behavioural classification beyond label detection.




--

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

### System Interface Authorization
Open a terminal shell session on your target Raspberry Pi and execute the interface parameters control tool:

```bash
sudo raspi-config
```

1. Navigate using key prompts: **Interface Options** \(\rightarrow\) **Camera** \(\rightarrow\) **Enable** \(\rightarrow\) **Yes**.
2. Select **Finish** and trigger a full hardware power cycle reboot:

```bash
sudo reboot
```

3. Post-initialization, run a physical interface sweep to confirm detection status:

```bash
libcamera-hello --list-cameras
```
*Verification standard: The output logging array must return and identify at least one active imaging sensor unit.*

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
Verify that your target workspace accurately reflects the required system module tree distribution template structural map details below:

```text
~/Networks-IOT-Assignment/
│
├── .env                          # Local Private Credentials Config Block
├── .env.example                  # Environment Variables Distribution Template
├── .gitignore                    # Local Track Filter Exclusion Table
├── requirements.txt              # Primary Application Dependencies Manifest
├── README.md                     # Project Technical Documentation Module
│
├── app/
│   ├── main.py                   # Master Application Thread Executive Core
│   ├── dashboard.py              # Interface Framework Host Engine
│   ├── config.py                 # Core Properties Component Mapping Module
│   ├── events.py                 # Alert Management Logic Tree
│   ├── logger_service.py         # Diagnostic Tracking Matrix Provider
│   ├── camera_service.py         # Capture Subsystem Logic Wrapper
│   ├── detector_service.py       # Inference Acceleration Handler
│   ├── motion_service.py         # Delta Imaging Evaluation Vector Core
│   ├── led_service.py            # Hardware Array Render Module
│   ├── event_manager.py          # Centralized State Dispatch Controller
│   ├── blynk_service.py          # Cloud Telemetry Interface Connector
│   ├── mqtt_service.py           # Message Transport Layer Dispatcher
│   ├── db_service.py             # Relational Database Workspace Pipeline
│   ├── env_data_service.py       # Environmental Telemetry Collector
│   ├── cloudinary_service.py     # Image Asset Cloud Storage Service
│   └── templates/
│       └── dashboard.html        # Engine Target View Presentation Markup
│
├── models/
│   └── yolov8n.onnx              # Compiled Network Optimization Graph Array
│
├── images/                       # Temporary System Runtime Output Matrix 
└── logs/                         # File Output Logging Matrix Destination
```

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

Paste your local configurations into the file editor interface context:
```ini
BLYNK_AUTH_TOKEN=your_token
CONFIDENCE_THRESHOLD=0.60
CAMERA_WARMUP_SECONDS=2.0
LOOP_INTERVAL_SECONDS=2.0
IMAGE_SAVE_DIR=images
LED_DETECTION_HOLD_SECONDS=2.0
EVENT_COOLDOWN_SECONDS=15
MQTT_BROKER=broker.hivemq.com
MQTT_PORT=1883
MQTT_USER_ID=userid
DB_PATH=detections.db
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
CLOUDINARY_FOLDER=iot-detector
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=false
```
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

## Supporting Resources:
https://docs.ultralytics.com/datasets/detect/coco
https://automaticaddison.com/motion-detection-using-opencv-on-raspberry-pi-4/
https://docs.opencv.org/3.4/pages.html
https://docs.opencv.org/3.4/d6/d00/tutorial_py_root.html
https://www.youtube.com/watch?v=P4Z8_qe2Cu0 (OpenCV)
https://www.youtube.com/watch?v=kTp5xUtcalw (Docker)
https://www.youtube.com/watch?v=lEcULR30-GM (Docker)
https://docs.docker.com/reference/dockerfile/
https://docs.docker.com/reference/compose-file/
https://onnxruntime.ai/docs/execution-providers/
https://docs.ultralytics.com/integrations/onnx
https://onnxruntime.ai/docs/api/python/api_summary.html
https://www.w3schools.com/python/ref_keyword_lambda.asp

AI LLMs used:
Claude
ChatGPT
Gemini

LLMs primarilly used to analyse code for errors, help with consistent system design (connecting modules in a functional way), README formatting, and for diagram generation of architecture.
Most comments in src code were either written personally or autofilled by VSCode, but occasionally
LLMs may have been used to help explain specific code.