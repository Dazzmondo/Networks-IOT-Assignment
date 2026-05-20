"""
Purpose:
    Flask web dashboard displaying detection history and live SenseHAT data.

Endpoints:
    GET /                → HTML dashboard (detections + counts + env)
    GET /api/detections  → JSON recent detections
    GET /api/counts      → JSON detection counts per label
    GET /api/environment → JSON latest SenseHAT reading

Deployment:
    Local (Pi):   python app/dashboard.py
    Render:       gunicorn app.dashboard:app

Note on SenseHAT:
    EnvDataService uses a lazy import so this file does not crash on Render
    (where sense-hat is not installed). It returns zero values gracefully.
"""

import os
import sys

from flask import Flask, jsonify, render_template
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db_service       import DBService
from env_data_service import EnvDataService
from config           import FLASK_HOST, FLASK_PORT, FLASK_DEBUG
from logger_service   import logger

app = Flask(__name__, template_folder="templates")
CORS(app)

db  = DBService()
env = EnvDataService()


@app.route("/")
def index():
    recent = db.get_recent(limit=20)
    counts = db.get_counts()
    env_data = env.read()
    return render_template(
        "dashboard.html",
        detections  = recent,
        dog_count   = counts.get("dog",    0),
        human_count = counts.get("person", 0),
        env         = env_data,
    )


@app.route("/api/detections")
def api_detections():
    return jsonify(db.get_recent(limit=20))


@app.route("/api/counts")
def api_counts():
    return jsonify(db.get_counts())


@app.route("/api/environment")
def api_environment():
    reading = env.read()
    reading["deviceID"] = os.getenv("MQTT_USER_ID", "iot-detector")
    return jsonify(reading)


if __name__ == "__main__":
    logger.info(f"Dashboard starting on {FLASK_HOST}:{FLASK_PORT}")
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)