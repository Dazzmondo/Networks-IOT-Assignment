"""
Purpose:
    Flask web dashboard displaying detection history and live SenseHAT data.

Endpoints:
    GET /                → HTML dashboard (detections + counts + env + analytics)
    GET /api/detections  → JSON recent detections
    GET /api/counts      → JSON detection counts per label
    GET /api/environment → JSON latest SenseHAT reading
    GET /api/analytics   → JSON rolling averages, anomaly score, hourly buckets
    GET /api/status      → JSON service connection status
    GET /stream          → Server-Sent Events (SSE) live push stream

Server-Sent Events (SSE) architecture:
    /stream holds an open HTTP connection per browser tab.
    The server pushes named events (detection, environment, analytics,
    counts, timeseries) whenever new data is available.  The browser
    EventSource API reconnects automatically if the connection drops —
    no client-side retry logic needed.

    A background thread (_sse_worker) polls the database and environment
    sensor on a short interval and pushes updates to all connected clients
    via a thread-safe queue.  This keeps Flask route handlers simple
    and avoids blocking the WSGI worker.

Data source selection:
    When MongoService is connected and enabled, the dashboard reads recent
    detections and analytics from MongoDB Atlas.  This allows the Render-
    deployed instance to serve live data without access to the local SQLite
    file on the Pi.

    When MongoDB is not configured, all reads fall back to SQLite.
    The same dashboard.py runs both locally (Pi) and on Render — the
    active backend is determined at startup by whether MONGO_URI is set.

Deployment:
    Local (Pi):   PYTHONPATH=. python app/dashboard.py
    Render:       gunicorn --workers 1 --threads 4 --bind 0.0.0.0:5000 app.dashboard:app

    Note on gunicorn workers: must be 1 (or use the gevent worker class).
    SSE requires a persistent connection per client; multiple worker
    processes do not share the in-process queue used here.

Note on SenseHAT:
    EnvDataService uses a lazy import so this file does not crash on Render
    (where sense-hat is not installed). It returns zero values gracefully.
"""

import json
import os
import queue
import threading
import time

from flask import Flask, Response, jsonify, render_template, stream_with_context
from flask_cors import CORS

# Removed sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# because gunicorn as app.dashboard:app sets the working directory to the app/ folder
# so imports work as expected without modification. 
# Insert not needed and causes issues when running locally.

from analytics_service import AnalyticsService
from config            import FLASK_DEBUG, FLASK_HOST, FLASK_PORT, MONGO_URI
from db_service        import DBService
from env_data_service  import EnvDataService
from logger_service    import logger
from mongo_service     import MongoService

app = Flask(__name__, template_folder="templates")
CORS(app)

# -- Initialise MongoDB if configured -----------------------------------------
# MongoService gracefully disables itself when MONGO_URI is blank, so
# this is always safe to construct regardless of environment.
mongo = MongoService()

# -- Initialise core services -------------------------------------------------
# DBService receives the mongo instance so it can mirror writes.
# On Render, analytics and recent detections are served from MongoDB.
db        = DBService(mongo_service=mongo)
env       = EnvDataService()
analytics = AnalyticsService(db_service=db, mongo_service=mongo)


# ── SSE client registry ───────────────────────────────────────────────────────
# Each connected browser tab gets its own Queue.
# The _sse_worker thread pushes formatted SSE strings into every queue.
_sse_clients: list[queue.Queue] = []
_sse_lock = threading.Lock()


def _register_client() -> queue.Queue:
    """Add a new SSE client queue and return it."""
    q = queue.Queue(maxsize=50)
    with _sse_lock:
        _sse_clients.append(q)
    return q


def _unregister_client(q: queue.Queue) -> None:
    """Remove a client queue when its connection closes."""
    with _sse_lock:
        try:
            _sse_clients.remove(q)
        except ValueError:
            pass


def _broadcast(event: str, data: dict) -> None:
    """
    Format and push one SSE message to every connected client.

    SSE wire format (per spec):
        event: <name>\\n
        data: <json>\\n
        \\n

    Dead queues (full = client too slow) are silently dropped to avoid
    blocking the worker thread.
    """
    message = f"event: {event}\ndata: {json.dumps(data)}\n\n"
    with _sse_lock:
        for q in list(_sse_clients):
            try:
                q.put_nowait(message)
            except queue.Full:
                pass


# ── SSE background worker ─────────────────────────────────────────────────────

def _sse_worker():
    """
    Background daemon thread that polls for new data and broadcasts SSE events.

    Poll interval is intentionally short (2 s) so the dashboard feels live.
    The worker tracks the last seen detection ID so it only pushes new rows,
    not a full table dump on every tick.

    Events pushed:
        detection   — one per new DB row (newest detections only)
        environment — SenseHAT reading on every tick
        analytics   — rolling avg / anomaly score (recomputed each tick)
        counts      — total label counts (triggers bar chart update)
        timeseries  — full 24 h bucket data (triggers line chart update)
    """
    last_id = 0

    # Initialise last_id to the current newest row so we do not replay
    # the entire history on first startup.
    try:
        recent = db.get_recent(limit=1)
        if recent:
            last_id = recent[0]["id"]
    except Exception:
        pass

    while True:
        try:
            # -- New detections -----------------------------------------------
            # get_since_id() returns only rows newer than last_id, so the
            # SSE broadcast never replays rows already sent to clients.
            new_rows = db.get_since_id(last_id)
            for row in new_rows:
                _broadcast("detection", row)
                last_id = max(last_id, row["id"])

            # -- Environment --------------------------------------------------
            env_data = env.read()
            _broadcast("environment", env_data)

            # -- Analytics (rolling avg, anomaly score) -----------------------
            # analytics.compute() selects MongoDB or SQLite automatically.
            stats = analytics.compute()
            _broadcast("analytics", stats)

            # -- Counts -------------------------------------------------------
            _broadcast("counts", db.get_counts())

            # -- Time-series chart data --------------------------------------
            # Only recompute and push when new rows arrived to reduce load.
            if new_rows:
                _broadcast("timeseries", analytics.chart_data())

        except Exception as error:
            logger.error(f"SSE worker error: {error}")

        time.sleep(2)


# Start the SSE worker as a daemon so it exits when the main process exits.
_worker_thread = threading.Thread(target=_sse_worker, daemon=True)
_worker_thread.start()
logger.info("SSE background worker started.")


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """
    Render the HTML dashboard.

    Recent detections are read from MongoDB when available (Render deployment)
    or from SQLite when running locally on the Pi.

    chart_data is injected as a Jinja variable so Chart.js bootstraps all
    charts immediately on page load. The SSE stream keeps them live after.
    """
    # Select data source based on MongoDB availability
    # On Render, mongo.is_enabled() is True and SQLite is not present,
    # so recent detections come from Atlas.
    # On the Pi, both are available; SQLite is used as the primary source
    # since it is always up to date and does not require a network call.
    if mongo.is_enabled():
        recent = mongo.get_recent(limit=20)
        counts = mongo.get_counts()
    else:
        recent = db.get_recent(limit=20)
        counts = db.get_counts()

    env_data = env.read()
    stats    = analytics.compute()
    c_data   = analytics.chart_data()

    return render_template(
        "dashboard.html",
        detections       = recent,
        dog_count        = counts.get("dog",    0),
        human_count      = counts.get("person", 0),
        env              = env_data,
        analytics        = stats,
        chart_data       = c_data,
        analytics_source = stats.get("source", "sqlite"),
        mongo_enabled    = mongo.is_enabled(),
    )


@app.route("/api/detections")
def api_detections():
    """Return recent detections as JSON. Reads from MongoDB when available."""
    if mongo.is_enabled():
        return jsonify(mongo.get_recent(limit=20))
    return jsonify(db.get_recent(limit=20))


@app.route("/api/counts")
def api_counts():
    """Return total detection counts per label as JSON."""
    if mongo.is_enabled():
        return jsonify(mongo.get_counts())
    return jsonify(db.get_counts())


@app.route("/api/environment")
def api_environment():
    """Return current SenseHAT environmental readings as JSON."""
    reading = env.read()
    reading["deviceID"] = os.getenv("MQTT_USER_ID", "iot-detector")
    return jsonify(reading)


@app.route("/api/analytics")
def api_analytics():
    """
    Return rolling averages, anomaly score, and hourly bucket data as JSON.

    Response shape:
    {
        "rolling_avg":   float,
        "current_hour":  int,
        "peak_hour":     str,
        "anomaly_score": float,
        "anomaly_label": str,
        "anomaly_class": str,
        "source":        str,
        "timeseries":    { ... },
        "hourly":        { ... },
        "counts":        { ... },
    }
    """
    stats  = analytics.compute()
    c_data = analytics.chart_data()
    return jsonify({**stats, **c_data})


@app.route("/api/status")
def api_status():
    """Return current service connection status as JSON."""
    return jsonify({
        "mongodb_connected": mongo.is_enabled(),
        "analytics_source":  analytics.compute().get("source", "sqlite"),
        "mqtt_user_id":      os.getenv("MQTT_USER_ID", "iot-detector"),
    })


@app.route("/stream")
def stream():
    """
    Server-Sent Events endpoint.

    Each GET /stream request:
        1. Registers a new client queue.
        2. Returns a streaming response that yields from that queue.
        3. Unregisters the queue when the client disconnects.

    The initial comment ping keeps the connection alive through proxies
    that close idle connections before the first real event arrives.
    """
    q = _register_client()

    @stream_with_context
    def _generate():
        # SSE comment lines (starting with ':') are ignored by clients
        # but prevent proxy timeouts on connection establishment.
        yield ": connected\n\n"
        try:
            while True:
                try:
                    # Block for up to 25 s; yield keepalive comment if idle.
                    # 25 s is below the typical 30 s proxy timeout.
                    msg = q.get(timeout=25)
                    yield msg
                except queue.Empty:
                    # Keepalive comment — prevents proxy/load-balancer timeout.
                    yield ": keepalive\n\n"
        except GeneratorExit:
            pass
        finally:
            _unregister_client(q)

    return Response(
        _generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no", # disables Nginx response buffering
        },
    )


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logger.info(f"Dashboard starting on {FLASK_HOST}:{FLASK_PORT}")
    logger.info(f"MongoDB: {'enabled' if mongo.is_enabled() else 'disabled (SQLite only)'}")
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG, threaded=True)