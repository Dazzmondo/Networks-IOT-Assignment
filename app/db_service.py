"""
Purpose:
    Persistent storage for detection events using SQLite.

Why SQLite?
    - Zero configuration: no separate server process needed.
    - Single file (detections.db) — easy to inspect, copy, or back up.
    - Sufficient for the event volume a home IoT system generates.
    - Historical data handling with queries, which is also used by the Flask dashboard.

Dual-write pattern:
    DBService accepts an optional MongoService instance at construction.
    When provided, every successful SQLite write is immediately mirrored
    to MongoDB Atlas.  The mirror write is fire-and-forget — a MongoDB
    failure does not roll back the SQLite write or affect the pipeline.
 
    This keeps all persistence logic in one place (DBService) rather than
    scattering mongo.insert_detection() calls across event_manager.py.

Schema:
    Table: detections
    ┌─────────────────┬──────────┬───────────────────────────────────────┐
    │ id              │ INTEGER  │ Auto-increment primary key            │
    │ timestamp       │ TEXT     │ ISO-8601 datetime string              │
    │ label           │ TEXT     │ "dog" or "person"                     │
    │ confidence      │ REAL     │ YOLO confidence score (0.0 – 1.0)     │
    │ image_path      │ TEXT     │ Local path to archived image / NULL   │
    │ image_url       │ TEXT     │ Cloudinary public URL / NULL          │
    │ blynk_notified  │ INTEGER  │ 1 if Blynk event was logged, else 0   │
    │ mqtt_published  │ INTEGER  │ 1 if MQTT was published, else 0       │
    │ temp            │ REAL     │ SenseHAT temperature at detection     │
    │ humidity        │ REAL     │ SenseHAT humidity at detection        │
    │ pressure        │ REAL     │ SenseHAT pressure at detection        │
    └─────────────────┴──────────┴───────────────────────────────────────┘
"""

import os
import sqlite3
from datetime import datetime, timedelta

from config import DB_PATH
from logger_service import logger


class DBService:
    """
    Manages the SQLite detection log.

    A fresh connection is opened for every operation to avoid locking
    issues across threads.  The schema is created automatically on first use.
    
    Args:
        mongo_service: optional MongoService instance. When provided, every
                       successful SQLite write is mirrored to MongoDB Atlas.
                       Pass None (default) to disable cloud mirroring.
    """

    def __init__(self, mongo_service=None):
        self._db_path = DB_PATH

        # -- Store the optional MongoDB mirror reference ----------------------
        # _mongo is None when MongoDB is not configured or unavailable.
        # All mirror calls are guarded with `if self._mongo:` so this
        # class behaves identically whether or not MongoDB is present.
        self._mongo = mongo_service

        # Ensure parent directory exists before SQLite tries to open the file.
        parent_dir = os.path.dirname(os.path.abspath(self._db_path))
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        # Waits up to 10 seconds on a locked DB before raising.
        conn = sqlite3.connect(self._db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Create the detections table if it does not already exist."""
        try:
            with self._connect() as conn:

                # Enable Write-Ahead Logging (WAL) mode to allow concurrent readers while writing.
                # This is important because the Flask dashboard reads from the
                # same file that the detection loop writes to.
                conn.execute("PRAGMA journal_mode=WAL;")

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS detections (
                        id              INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp       TEXT    NOT NULL,
                        label           TEXT    NOT NULL,
                        confidence      REAL    NOT NULL,
                        image_path      TEXT,
                        image_url       TEXT,
                        blynk_notified  INTEGER NOT NULL DEFAULT 0,
                        mqtt_published  INTEGER NOT NULL DEFAULT 0,
                        temp            REAL,
                        humidity        REAL,
                        pressure        REAL
                    )
                """)
                conn.commit()
            logger.info(f"Database ready: {self._db_path}")
        except Exception as error:
            logger.error(f"Database initialisation failed: {error}")
            raise

    # -- Public API ---------------------------------------------------------------

    def log_detection(
        self,
        label: str,
        confidence: float,
        image_path: str | None     = None,
        image_url: str | None      = None,
        blynk_notified: bool       = False,
        mqtt_published: bool       = False,
        temp: float | None         = None,
        humidity: float | None     = None,
        pressure: float | None     = None,
    ) -> int | None:
        """
        Insert a new detection record.

        SQLite is always written first. The MongoDB mirror is attempted
        after a successful SQLite insert, using the new row's id as the
        sqlite_id field for deduplication in Atlas.

        Returns the new row ID, or None on failure.
        """
        try:
            with self._connect() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO detections
                        (timestamp, label, confidence, image_path, image_url,
                         blynk_notified, mqtt_published, temp, humidity, pressure)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        datetime.now().isoformat(timespec="seconds"),
                        label,
                        confidence,
                        image_path,
                        image_url,
                        int(blynk_notified),
                        int(mqtt_published),
                        temp,
                        humidity,
                        pressure,
                    ),
                )
                conn.commit()
                row_id = cursor.lastrowid

                logger.info(
                    f"DB logged → id={row_id} "
                    f"label={label} confidence={confidence:.2f} "
                    f"blynk={blynk_notified} mqtt={mqtt_published}"
                )

                # -- Mirror to MongoDB Atlas ----------------------------------
                
                # Fetch the full row so the document shape matches what
                # get_recent() returns — keeps the mirror consistent.
                # The mirror is attempted after commit so SQLite is safe
                # even if MongoDB raises an exception.
                if self._mongo:
                    row = conn.execute(
                        "SELECT * FROM detections WHERE id = ?", (row_id,)
                    ).fetchone()
                    if row:
                        self._mongo.insert_detection(dict(row))

                return row_id
        except Exception as error:
            logger.error(f"Failed to log detection: {error}")
            return None

    def get_recent(self, limit: int = 20) -> list[dict]:
        """Return the most recent detections, newest first."""
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT * FROM detections ORDER BY id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
                return [dict(row) for row in rows]
        except Exception as error:
            logger.error(f"DB query failed: {error}")
            return []

    def get_counts(self) -> dict:
        """Return total detection counts per label, e.g. {"dog": 5, "person": 12}."""
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT label, COUNT(*) as count FROM detections GROUP BY label"
                ).fetchall()
                return {row["label"]: row["count"] for row in rows}
        except Exception as error:
            logger.error(f"DB count query failed: {error}")
            return {}

    def get_since_id(self, last_id: int) -> list[dict]:
        """
        Return all detections with id > last_id, oldest first.
 
        Used by the Server-Sent Events (SSE) worker to fetch only new rows on each 
        poll tick rather than re-reading the full table.  The caller tracks last_id
        and increments it as rows are processed.
 
        Args:
            last_id: the highest row id already seen by the caller.
 
        Returns:
            List of detection dicts, ordered by id ascending (oldest first).
        """
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT * FROM detections WHERE id > ? ORDER BY id ASC",
                    (last_id,),
                ).fetchall()
                return [dict(row) for row in rows]
        except Exception as error:
            logger.error(f"DB get_since_id failed: {error}")
            return []
 
 
    def get_last_24h(self) -> list[dict]:
        """
        Return all detections from the last 24 hours, oldest first.
 
        Used by AnalyticsService to compute rolling averages and build
        Chart.js time-series buckets.  The 24-hour window means the
        analytics stay relevant as the system runs over multiple days.
 
        Returns:
            List of detection dicts ordered by timestamp ascending.
        """
        try:
            cutoff = (datetime.now() - timedelta(hours=24)).isoformat(
                timespec="seconds"
            )
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT * FROM detections
                    WHERE timestamp >= ?
                    ORDER BY timestamp ASC
                    """,
                    (cutoff,),
                ).fetchall()
                return [dict(row) for row in rows]
        except Exception as error:
            logger.error(f"DB get_last_24h failed: {error}")
            return []