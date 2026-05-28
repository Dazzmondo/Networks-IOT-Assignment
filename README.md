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
| Gunicorn | Production WSGI server originally designed for Render deployment (later abandoned) |
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
- **Cloud database deployment support** — MongoDB Atlas allows the dashboard to access live remote data without direct Pi filesystem access.
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
- **Gunicorn production deployment** — Flask dashboard deployable using threaded Gunicorn workers.
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
- Cloudinary Media Hosting

---

## Demo

[![Watch the video](https://www.youtube.com/watch?v=AvDrT0WeD7k)](https://www.youtube.com/watch?v=AvDrT0WeD7k)

NOTE: RENDER IS NO LONGER BEING USED IN THIS ASSIGNMENT

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

NOTE: RENDER IS NO LONGER BEING USED IN THIS ASSIGNMENT

---

## Design Decisions & Reflection

### Why BlynkLib over the Blynk HTTP API?
BlynkLib uses a persistent socket connection rather than individual HTTP requests. This means the connection stays open continuously in a background thread, and `blynk.virtual_write()` pushes data to the dashboard instantly rather than waiting for a polling cycle. Running `blynk.run()` in a dedicated daemon thread (using Python's `threading.Thread`) prevents it from blocking the main motion detection loop — the camera never pauses waiting for a network call. The Blynk platform also provides a polished web dashboard and mobile app that make it straightforward to monitor the system remotely without building a custom frontend from scratch.

### Why HiveMQ + paho-mqtt?
HiveMQ's public broker (`broker.hivemq.com`) was chosen because `test.mosquitto.org` wasn't working when I started the assignment. paho-mqtt is the standard Python MQTT client and was used directly in the module labs. MQTT adds a second independent communication channel alongside Blynk, demonstrating multiple IoT protocols running concurrently. The implementation includes a Last Will and Testament (LWT) message so the broker automatically publishes `offline` to the status topic if the Pi disconnects unexpectedly. Topics are namespaced under a unique `MQTT_USER_ID` to avoid collisions on the shared public broker. QoS 1 (at least once) is used for detection events (guaranteed delivery) and QoS 0 (at most once) for environmental telemetry (best effort, acceptable to lose occasional readings).

### Why motion-gated detection?
Running YOLO inference on every camera frame would push the Pi's CPU to 100% continuously, causing thermal throttling and degraded performance across all services. The motion gate means YOLO only runs when something has actually moved. OpenCV's absolute difference method was chosen over MOG2 background subtraction because MOG2 continuously adapts its background model, which requires more compute power and increases the chances of the CPU overheating. MOG2' continuous learning can also cause it to gradually "learn" a slow-moving pet as part of the background and stop detecting it. Absolute difference against a fixed reference frame is deterministic, lightweight, and easier to tune for indoor conditions.

### Why two camera configurations (preview + still)?
A single camera configuration optimised for speed produces poor quality still images — video frames sacrifice resolution and exposure quality for throughput. A 640×480 grayscale stream is sufficient for OpenCV contour analysis (motion detection does not need colour or high resolution), but the image sent to YOLO for inference, saved to disk, and uploaded to Cloudinary should be the best quality the camera can produce. Picamera2's `switch_mode()` allows runtime switching between a low-resolution preview configuration and a high-resolution still configuration. The still mode is only used for the fraction of a second needed to capture the detection image, then the camera returns to preview mode.

### Why ONNX Runtime over running PyTorch directly?
PyTorch and the full Ultralytics package require approximately 426 MB of disk space, which is too large for the Raspberry Pi SD card alongside the operating system, other dependencies, and project files. The YOLOv8n model exported to ONNX format is approximately 12 MB. ONNX Runtime (`onnxruntime`) is a lightweight inference engine that runs the exported model directly without PyTorch installed. The model is exported once on a laptop and copied to the Pi. This is a standard edge deployment pattern where model training and inference happen on different hardware.

### Why NMS post-processing in code rather than baked into the model export?
Exporting YOLOv8 to ONNX without the built-in Non-Maximum Suppression (NMS) layer (the default export behaviour) gives full control over confidence thresholds at runtime via environment variables. This means thresholds can be tuned without re-exporting the model. Per-class NMS is applied separately for dog and person detections so a high-confidence person box cannot suppress a nearby dog box — which would happen if NMS were applied globally across all classes.

### Why SenseHAT environmental data?
The SenseHAT is physically attached to the Raspberry Pi used in this project, making it a natural additional data source. Publishing temperature, humidity, and pressure alongside detection events produces a richer data stream — environmental context is logged with every detection and displayed in the Flask dashboard. It also demonstrates the physical IoT layer (sensor input) beyond just the camera, and allows the system to correlate detection activity with environmental conditions over time through the analytics charts. NOTE: SenseHAT data is not available when deploying through Docker.

### Why SQLite with WAL mode?
SQLite requires zero configuration, produces a single portable file, and persists across restarts when volume-mounted in Docker. It is sufficient for the event volume a home IoT system generates. WAL (Write-Ahead Logging) mode is enabled via `PRAGMA journal_mode=WAL` so the Flask dashboard can read from the database at the same time as the detection loop writes to it, without locking conflicts. This is important because the dashboard and main detection loop run as separate processes that both access the same file.

### Why MongoDB Atlas alongside SQLite?
SQLite lives on the Pi's SD card and is not accessible remotely. MongoDB Atlas provides a free-tier cloud database that the Render-deployed dashboard can query directly. The dual-write pattern — SQLite first, then MongoDB as a mirror — means the Pi retains full offline resilience (SQLite always written first, MongoDB failure does not affect the pipeline) while also maintaining remote persistence. MongoDB's aggregation pipeline (`$dateTrunc`, `$group`, `$avg`) enables server-side analytics computation — rolling averages and hourly bucketing are computed in the database rather than by pulling raw rows into Python.

### Why Flask + Server-Sent Events over WebSockets page refresh?
The module labs build Flask APIs on the Pi and deploy them to Render, so Flask is a natural fit. Server-Sent Events (SSE) replace the original `<meta http-equiv="refresh" content="10">` pattern. SSE holds a single persistent HTTP connection per browser tab and the server pushes named events (`detection`, `environment`, `analytics`, `counts`, `timeseries`) whenever new data is available. This means the dashboard updates in under 2 seconds after a detection without reloading the page. This is a better user experience and avoids the visual flicker of a full reload. SSE was chosen over WebSockets because it is simpler (one-way server-to-client push is all that is needed) and works natively with Flask's streaming response support.

### Why Docker?
Docker ensures the system can be deployed on the Pi without manually managing Python versions, virtual environments, or conflicting system packages. It also demonstrates containerisation as a self-learned technology beyond the module content. I used to sell Google Kubernetes Engine (GKE) as part of the Google Cloud Platform, and noticed from interactions with CIOs and CTOs that Docker containers and serverless represented trends business were moving towards. Thus, I wanted to learn Docker/containerisation technology. The implementation covers multi-service `docker-compose.yml` configuration, volume mounts for persistent data. NOTE: Hardware access and SenseHAT data are not accessible through Docker deployment. For SenseHAT data please run local deployment.

### Why Cloudinary?
The Pi captures detection images to its local SD card, but those images are only accessible from the local network. Cloudinary uploads annotated dog detection images (with YOLO bounding boxes drawn) to a Continuous Delivery Network (CDN) and returns a public HTTPS URL. This URL is stored in SQLite, mirrored to MongoDB, included in the MQTT event payload, and displayed as a clickable thumbnail in the Flask dashboard — making captured images accessible from anywhere.

### Why per-class event cooldowns?
Without cooldowns, a single dog walking past the camera could generate dozens of Blynk notifications and MQTT messages within a few seconds as it triggers multiple motion detection cycles. Two separate cooldown systems are used: `MOTION_COOLDOWN_SECONDS` (in `motion_service.py`) controls how often the camera captures a new still image, and `EVENT_COOLDOWN_SECONDS` (in `event_manager.py`) controls how often Blynk and MQTT notifications fire. Separating them means detections are still logged to SQLite and MongoDB on every valid motion event, but push notifications are rate-limited independently.

### Why Z-score anomaly detection?
A fixed threshold ("alert if more than 5 detections in an hour") is fragile because the right number depends on the normal activity level of the specific environment. A Z-score measures how many standard deviations the current hour's detection count is above the 24-hour mean, so the anomaly detector self-calibrates to each deployment. A quiet house where one detection per hour is normal would flag 5 detections as anomalous, while a busy house where 10 per hour is normal would not — using the same threshold logic.

---

### Limitations

- The YOLO model uses general-purpose COCO pretrained weights rather than a custom-trained model. Detection accuracy for edge cases (partially visible animals, unusual angles) would improve significantly with a fine-tuned dataset.
- SenseHAT temperature readings are elevated by the Pi's CPU heat. The raw values are useful for relative comparisons and trend analysis but do not reflect true ambient temperature. A calibration offset could be applied in `env_data_service.py`.
- The motion background frame is fixed at initialisation. Gradual lighting changes (lights switching on and off) cause the fixed background to drift from the current scene, increasing false positive detections over time. `reset_background()` exists to address this but must currently be called manually.
- libcamera must be present on the Docker host (Raspberry Pi OS) for Picamera2 to work inside the container. The Docker image cannot run the detection loop on non-Pi hardware without camera simulation.
- The SSE live update system uses an in-process queue, which means the Flask dashboard must run with a single gunicorn worker. This limits concurrent SSE clients to the number of threads configured.
- BlynkLib's in-memory counters (V1 human count, V2 dog count) reset to zero on every restart. SQLite and MongoDB hold the persistent counts, but the Blynk gauges do not reflect the true lifetime total after a restart.
- The PiCamera 2 caused many problems throughout testing. The quality of the images proved to be blurry and unreliable. The initial Raspberry Pi 4 used for the assignment needed to be replaced due to the CSI Connector becoming damaged (likely due to overheating, measured at nearly 100°C at one point during testing). This poor image quality persisted across 2 separate cameras, 2 separate Raspberry Pis, and through attempts to improve the images with OpenCV. Normal camera tests in the terminal produced similarly poor quality images. In a more practical, production-ready system, better quality cameras would definitely be used.
- When deployed through Docker, SenseHAT real-time data can't be seen through the dashboard. This is because the hardware configuration could not be implemented in Docker. This was also a factor in the choice to not use Render. 
- It was ultimately decided to abandon Render because the system could not be effectively deployed in a functional state. It progressed to the point where the website said it deployed, but it returned a 502 error when you tried to load the url. The code was failing to deploy correctly and it was getting too close to the deadline to debug in time.


---

### Future Improvements

- Behavioural classification beyond label detection (e.g. dog urinating). The original motivation for this project was detecting a specific dog behaviour. The system currently identifies that a dog is present but not what it is doing. A pose estimation model (such as YOLOv8-pose) combined with multi-frame analysis of position and movement patterns could classify behaviours like circling, leg lifting, and prolonged stationary hovering — the sequence that usually precedes urination. This would allow targeted alerts rather than alerting on every detection.
- Custom-trained YOLO model fine-tuned on a dataset of the specific dog and home environment, improving accuracy for the exact use case.
- MQTT subscription for remote LED colour control. Currently LEDs only reflect local system state.
- Edge TPU acceleration (Coral USB) to reduce YOLO inference time on the Pi.
- Systemd service for automatic startup on Pi boot without manual `python app/main.py`.
- Multi-camera support — a second camera covering another room would extend the detection area.
- Configurable thresholds via the Flask dashboard UI. Currently requires editing `.env` and restarting.
- Automatic background frame reset on a timer in `motion_service.py` to handle gradual lighting changes without manual intervention.
- Extra security/authentication features could be added. As this is a personal academic project, I wasn't worried about somebody unauthorised getting access to my dashboard or data. However, on a production-ready system of a similar design, it likely would be important to keep this data anonymised.
- Editable UI settings to change thresholds like detection confidence level or camera settings could be added to improve the user experience.
- As mentioned in my Limitations section, the PiCamera 2 was not of good enough quality for this project, and caused a lot of problems throughout. The issues with hue, colour, and brightness made the process much more difficult. In a production-ready system I would ensure to use cameras of a far higher standard.


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

⚠️ **Important**: Complete your manual setup and hardware testing (Parts 1–9) before executing this section. Your environment must function locally first.

---

### 10.1 — Pre-create Host Directories and Fix Volume Permissions
Docker processes create mapped volume directories with `root` privileges. Pre-creating them as your standard local user account avoids runtime `PermissionError` traps when your native detection scripts or the containerized dashboard try to write data.

Run these setup commands in your terminal:
```bash
cd ~/Networks-IOT-Assignment

# Pre-create tracking directories
mkdir -p data logs images models

# Force file ownership back to your user profile
sudo chown -R $USER:$USER data logs images models
chmod 755 data logs images models
```

Ensure your ONNX detection weights file is correctly positioned inside the models path:
```bash
ls models/yolov8n.onnx   # Verify the model exists
```

---

### 10.2 — Verify Your Centralized Dynamic Paths
Thanks to the absolute anchor configuration inside `app/config.py` (`BASE_DIR = os.path.abspath(...)`), the storage directories are dynamically mapped based on whether code runs on the metal or inside a container. 

Open your `.env` configuration file and ensure there are no overriding local path flags:
```bash
grep DB_PATH .env   # This should return nothing
```
*Note: If a relative `DB_PATH` property exists in your environment file, remove that line completely. The system automatically computes your optimal target bounds natively.*

---

### 10.3 — Build the Application Container Image
Compile the isolated web layout image by running:
```bash
docker compose build --no-cache
```

💡 **Docker Permission Troubleshooting**: If your user account returns a permission denied exception when attempting to interface with the Docker engine:
```bash
sudo usermod -aG docker $USER
newgrp docker
# Then retry compilation:
docker compose build --no-cache
```

---

### 10.4 — Execute the Hybrid Pipeline Environment
To maximize video stream throughput and maintain hardware accessibility, launch your software packages using this dual operational framework:

#### 1. Spin Up the Web Dashboard Container (Background)
Deploy the multi-threaded Gunicorn web interface detached from your terminal:
```bash
docker compose up -d --remove-orphans
```

#### 2. Launch the Hardware Detection Loop (Natively on your Pi)
Open a brand-new, separate terminal window, navigate to your root project workspace folder, and trigger the physical core pipeline with the terminal environment path mapper active:
```bash
PYTHONPATH=app python3 -m app.main
```

---

### 10.5 — Verify System Synchronization
Monitor initialization operations and verify data pathways by checking terminal outputs.

#### Native Detection Loop Target Output:
```text
IoT Pet & Human Detection System — starting up
MQTT connected to broker.hivemq.com:1883
Pi Camera started in preview mode (640x480). Warming up…
Camera ready.
Continuous autofocus enabled.
MongoDB Atlas connected — db=iot_detector collection=detections
All services ready. Monitoring for motion...
```

#### Docker Web Dashboard Container Target Output:
To view the status of your isolated web services, run:
```bash
docker compose logs -f dashboard
```
```text
[INFO] Starting gunicorn
[INFO] Listening at: http://0.0.0.0:5000
[INFO] Using worker: gthread
[INFO] MongoDB Atlas connected — db=iot_detector collection=detections
[INFO] Database ready: /app/data/detections.db
[INFO] SSE background worker started.
```

Once verified, open your browser and navigate to: `http://<YOUR_PI_IP_ADDRESS>:5000` to review live dashboard views.

---

### 10.6 — Useful Management Commands
```bash
docker compose logs -f dashboard        # Stream web interface dashboard tracking logs only
docker compose down                     # Stop and safely tear down container stacks
docker compose restart                  # Trigger rapid restart cycle on active web blocks
docker compose up -d --build            # Force full image re-compilation after manual updates
```

---

### 10.7 — Production Troubleshooting Ledger


| Symptom | Likely Cause | Fix |
| :--- | :--- | :--- |
| `ModuleNotFoundError: No module named 'analytics_service'` | Gunicorn missing environment search context paths. | Ensure your `docker-compose.yml` environment variable block contains `- PYTHONPATH=/app/app`. |
| `PermissionError: [Errno 13] Permission denied` | Shared volume directories (`data/`, `logs/`) are locked by `root`. | Run `sudo chown -R $USER:$USER logs data images` on the host Pi terminal. |
| `failed to bind host port 0.0.0.0:5000: address already in use` | A lingering application process or container is locking port 5000. | Force close background instances by running `docker compose down` followed by `pkill -f gunicorn`. |
| `ModuleNotFoundError: No module named 'libcamera'` | Attempting to execute the hardware loop inside an isolated container. | Stop container-level tracking. Run your core engine natively via `PYTHONPATH=app python3 -m app.main`. |
| `cannot connect to Docker daemon` | Active local profile lacks administrative execution privileges. | Run `sudo usermod -aG docker $USER && newgrp docker` to update permissions. |


---

# PART 11 — Troubleshooting

## Camera Not Detected

```bash
rpicam-hello --list-cameras
```

Check:

- Ribbon cable orientation
- Camera enabled in `raspi-config`(not necessary in most modern Raspberry Pis)

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


---

## Testing Logs & Project Journal

### 📅 Monday, 25 May 2026

*   **14:11** — 🟡 **Partial Success**
    *   Multiple motion alerts triggered. 
    *   Successfully identified **1 human**. 
    *   Failed to recognize the target dog in the frame.
*   **14:18** — ⚙️ **Hardware Setup Adjustments**
    *   Positioned the physical camera upside down for easier mounting. 
    *   Motion detection ran successfully.
*   **14:27** — 🟢 **Detection Success**
    *   Successfully identified **1 human** with **73% confidence**.
*   **14:30** — 🚀 **System Optimization**
    *   **Code Update**: Modified `camera_service.py` to handle the inverted hardware orientation.
    *   **Results**: Immediate improvement. Detected **3 humans** and **2 dogs**.
    *   **Integration**: Verified end-to-end telemetry. The Blynk mobile application successfully received real-time updates (**Dog confidence: 79%**, **Person confidence: 79%**).
*   **16:19** — 🟢 **Detection Success**
    *   Successfully detected **1 human** and **1 dog**.
*   **17:00** — 🟢 **Detection Success**
    *   Successfully detected **2 dogs**.

---

### 📅 Tuesday, 26 May 2026

*   **18:33** — 🟢 **Detection Success**
    *   Successfully detected **1 dog**.
*   **19:56** — 🔴 **Detection Failure**
    *   YOLOv8 failed to detect the dog. 
    *   *Root cause analysis:* Extreme colour distortion and the top of the dog's head being cut off by the frame boundary.
*   **20:07** — ⚠️ **Hardware Critical Fault**
    *   The camera feed began displaying a persistent bright white and purple hue covering the entire image capture field. 
    *   No software configuration settings were altered prior to this change. Root cause of the sensor distortion remains unknown. Further automation loops are blocked by this baseline imagery fault.
*   **20:10** — 🔴 **Detection Failure**
    *   The dog crossed directly in front of the lens. 
    *   The system triggered motion, but the purple hardware color distortion was too severe for YOLOv8 to extract features.
*   **21:03** — 🔧 **Troubleshooting Phase**
    *   Adjusted the raw camera configurations manually, but the purple tint persisted. 
    *   Executed a standalone test script directly via the Raspberry Pi terminal to bypass the main software loop. The raw images confirmed persistent blurring and colour issues, indicating a structural hardware or connection fault rather than a software regression.
*   **21:53** — 📝 **Daily Summary**
    *   Ceased physical testing for the evening. 
    *   *Conclusion:* The afternoon run was highly successful. The modular python program and the Flask web dashboard executed smoothly without memory leaks. While image clarity was sub-optimal, objects were consistently classified, and remote notifications triggered correctly. The evening hardware degradation ultimately prevented full real-time validation.

Note: These do not represent the full testing logs, but they represent the most important events once the program was functional. For example, attempted tests on 27/05/2026 failed at the beginning of the process due to issues relating to the installation dependencies preventing the program from being run.


## Sample Images


| Dog Detection 1 | Dog Detection 2 | Dog Detecton 3 |
|:---:|:---:|:---:|
| <img src="https://res.cloudinary.com/di5ce2hyw/image/upload/v1779724847/iot-detector/longaimsmqyqxwoflq4j.jpg" width="300" alt="Dog detection 1"> | <img src="https://res.cloudinary.com/di5ce2hyw/image/upload/v1779724857/iot-detector/xmcuaz3biamdvn7xsgql.jpg" width="300" alt="Dog detection 2"> | <img src="https://res.cloudinary.com/di5ce2hyw/image/upload/v1779816825/iot-detector/rvymwz53t80xfuh72sfw.jpg" width="300" alt="Dog detection 3"> |

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

Large Language Models (LLMs) were utilized during the development of this project. The majority of the code was first written personally based on the Computer Systems & Networks module lectures and labs, in addition to the knowledge from other modules (Programming, Web Development, Databases), before being tweaked.


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
