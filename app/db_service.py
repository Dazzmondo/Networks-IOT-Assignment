"""
Purpose:
    Persistent storage for detection events using SQLite.

Why SQLite?
    - Zero configuration: no separate server process needed.
    - Single file (detections.db) — easy to inspect, copy, or back up.
    - Sufficient for the event volume a home IoT system generates.
    - Historical data handling with queries, which is also used by the Flask dashboard.

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
from datetime import datetime

from config import DB_PATH
from logger_service import logger


class DBService:
    """
    Manages the SQLite detection log.

    A fresh connection is opened for every operation to avoid locking
    issues across threads.  The schema is created automatically on first use.
    """

    def __init__(self):
        self._db_path = DB_PATH
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
                logger.info(
                    f"DB logged → id={cursor.lastrowid} "
                    f"label={label} confidence={confidence:.2f} "
                    f"blynk={blynk_notified} mqtt={mqtt_published}"
                )
                return cursor.lastrowid
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
