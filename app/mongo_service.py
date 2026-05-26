"""
mongo_service.py
================
Purpose:
    Mirrors every detection event to MongoDB Atlas in real time, providing
    cloud-based remote persistence alongside the local SQLite database.

Architecture — dual-write pattern:
    Every detection is written to BOTH SQLite (local) and MongoDB Atlas (cloud).
    SQLite is the primary store — it is always written first and is the source
    of truth for the local dashboard and all local queries.
    MongoDB is the secondary store — written immediately after SQLite succeeds.
    If MongoDB is unavailable, the write failure is logged but does NOT affect
    the detection pipeline. The system degrades gracefully.

    SQLite  →  local dashboard, analytics_service, offline resilience
    MongoDB →  Render dashboard, MongoDB aggregation analytics, remote access

    This mirrors the pattern used in real IoT deployments where an edge device
    maintains local storage for resilience and syncs to the cloud when available.

Why MongoDB Atlas alongside SQLite?
    SQLite is excellent for local structured queries but cannot be accessed
    remotely — the database file lives on the Pi's SD card.  MongoDB Atlas
    provides a free-tier cloud database that the Render-deployed dashboard
    can query directly, making detection history accessible from anywhere.

    MongoDB's aggregation pipeline also enables richer server-side analytics
    (hourly bucketing, rolling averages, peak detection) that would require
    multiple SQLite queries and Python post-processing to replicate.

MongoDB aggregation pipeline:
    Rather than fetching raw rows and computing averages in Python
    (as analytics_service.py does for SQLite), this service uses MongoDB's
    $group, $avg, $sum, and $bucket stages to push computation to the database.
    This is more efficient at scale and demonstrates the aggregation pipeline
    from the Databases module.

Collection schema (mirrors SQLite detections table):
    {
        "_id":            ObjectId (auto),
        "sqlite_id":      int       (SQLite row id for deduplication),
        "timestamp":      datetime  (Python datetime, stored as BSON date),
        "label":          str       ("dog" | "person"),
        "confidence":     float,
        "image_path":     str | None,
        "image_url":      str | None,
        "blynk_notified": bool,
        "mqtt_published": bool,
        "temp":           float | None,
        "humidity":       float | None,
        "pressure":       float | None,
    }

Graceful degradation:
    If MONGO_URI is not set in .env, MongoService is disabled and all
    methods return None/empty results silently.  The rest of the system
    continues to work using SQLite only.

Dependencies:
    pip install pymongo dnspython
    (dnspython is required for MongoDB Atlas SRV DNS resolution)
"""


from datetime import datetime, timedelta, timezone

from app.logger_service import logger
from app.config import (
    MONGO_URI,
    MONGO_DB_NAME,
    MONGO_COLLECTION,
)


class MongoService:
    """
    Wraps PyMongo to provide cloud mirror writes and aggregation queries.

    All public methods are safe to call when MongoDB is disabled —
    they return None or empty results rather than raising exceptions.

    Usage:
        mongo = MongoService()
        mongo.insert_detection(detection_dict)
        counts  = mongo.get_counts()
        hourly  = mongo.get_hourly_buckets(hours=24)
        rolling = mongo.get_rolling_average(hours=24)
        anomaly = mongo.get_anomaly_score()
    """

    def __init__(self):
        # -- Attempt connection only if credentials are configured --------------
        # If MONGO_URI is blank (default), the service disables itself and
        # every method becomes a silent no-op.  This means the system runs
        # identically with or without MongoDB configured.
        self._enabled    = False
        self._collection = None

        if not MONGO_URI:
            logger.info(
                "MongoDB URI not set — cloud mirror disabled. "
                "Detections will be stored in SQLite only."
            )
            return

        try:
            # Import pymongo here rather than at module level so the rest of
            # the application does not crash if pymongo is not installed.
            from pymongo import MongoClient, ASCENDING, DESCENDING
            from pymongo.errors import ServerSelectionTimeoutError

            # serverSelectionTimeoutMS prevents the constructor from blocking
            # for 30 s if Atlas is unreachable — fails fast instead.
            self._client = MongoClient(
                MONGO_URI,
                serverSelectionTimeoutMS=5000,
            )

            # Ping the deployment to verify the connection is live.
            # This raises ServerSelectionTimeoutError if Atlas is unreachable.
            self._client.admin.command("ping")

            self._db         = self._client[MONGO_DB_NAME]
            self._collection = self._db[MONGO_COLLECTION]

            # -- Indexes -------------------------------------------------------
            # sqlite_id: unique index prevents duplicate documents if the
            #   same detection is inserted twice (e.g. after a restart).
            # timestamp: descending index speeds up time-range queries and
            #   the aggregation pipeline's $match stage.
            self._collection.create_index(
                [("sqlite_id", ASCENDING)], unique=True, background=True
            )
            self._collection.create_index(
                [("timestamp", DESCENDING)], background=True
            )

            self._enabled = True
            logger.info(
                f"MongoDB Atlas connected — "
                f"db={MONGO_DB_NAME} collection={MONGO_COLLECTION}"
            )

        except Exception as error:
            logger.warning(
                f"MongoDB Atlas connection failed: {error}. "
                "Continuing with SQLite only."
            )


    # ── Public API ────────────────────────────────────────────────────────────


    def insert_detection(self, detection: dict) -> bool:
        """
        Mirror a detection record to MongoDB Atlas.

        Called immediately after the SQLite insert in db_service.py so
        both stores are updated in the same detection event.

        The document shape mirrors the SQLite schema so the Render dashboard
        can read from MongoDB without any data transformation.

        Args:
            detection: dict matching the SQLite detections row, including
                       the 'id' field (used as sqlite_id for deduplication).

        Returns:
            True if inserted successfully, False otherwise.
        """
        if not self._enabled:
            return False

        try:
            # Convert ISO string timestamp to a Python datetime so MongoDB
            # stores it as a proper BSON date — enables date operators in
            # the aggregation pipeline ($dateToString, $dateTrunc, etc.)
            ts_raw = detection.get("timestamp", "")
            try:
                ts = datetime.fromisoformat(ts_raw)
            except (ValueError, TypeError):
                ts = datetime.now(timezone.utc)

            doc = {
                "sqlite_id":      detection.get("id"),
                "timestamp":      ts,
                "label":          detection.get("label"),
                "confidence":     detection.get("confidence"),
                "image_path":     detection.get("image_path"),
                "image_url":      detection.get("image_url"),
                "blynk_notified": bool(detection.get("blynk_notified")),
                "mqtt_published": bool(detection.get("mqtt_published")),
                "temp":           detection.get("temp"),
                "humidity":       detection.get("humidity"),
                "pressure":       detection.get("pressure"),
            }

            # update_one with upsert=True: inserts if sqlite_id not present,
            # updates if it already exists (idempotent on retry).
            self._collection.update_one(
                {"sqlite_id": doc["sqlite_id"]},
                {"$set": doc},
                upsert=True,
            )
            logger.debug(f"MongoDB mirror → sqlite_id={doc['sqlite_id']} label={doc['label']}")
            return True

        except Exception as error:
            logger.error(f"MongoDB insert_detection failed: {error}")
            return False


    def get_counts(self) -> dict:
        """
        Return total detection counts per label using the aggregation pipeline.

        Pipeline:
            $group by label → $sum 1 per document

        Equivalent SQL:
            SELECT label, COUNT(*) FROM detections GROUP BY label

        Returns:
            {"dog": int, "person": int}
        """
        if not self._enabled:
            return {}

        try:
            pipeline = [
                # Group all documents by their label field.
                # 'count' accumulates 1 for each document in the group.
                {"$group": {"_id": "$label", "count": {"$sum": 1}}},
            ]
            result = self._collection.aggregate(pipeline)
            return {doc["_id"]: doc["count"] for doc in result}

        except Exception as error:
            logger.error(f"MongoDB get_counts failed: {error}")
            return {}


    def get_hourly_buckets(self, hours: int = 24) -> list[dict]:
        """
        Return per-hour detection counts for the last `hours` hours,
        broken down by label (dog / person).

        Uses MongoDB's $dateTrunc aggregation operator to truncate timestamps
        to the hour boundary, then groups and counts within each bucket.

        Pipeline stages:
            $match   → filter to time window (last 24 h)
            $group   → group by {hour_bucket, label}, count documents
            $sort    → ascending by hour for Chart.js consumption

        Returns:
            [
                {
                    "hour":   "2025-01-15T14:00:00",  ← ISO string
                    "label":  "dog",
                    "count":  3,
                },
                ...
            ]
        """
        if not self._enabled:
            return []

        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

            pipeline = [
                # Stage 1: limit to the requested time window.
                # Using an indexed field (timestamp) here lets MongoDB use
                # the index rather than scanning the full collection.
                {"$match": {"timestamp": {"$gte": cutoff}}},

                # Stage 2: group by truncated hour + label.
                # $dateTrunc rounds the timestamp down to the nearest hour.
                # The compound _id gives us one bucket per (hour, label) pair.
                {"$group": {
                    "_id": {
                        "hour": {
                            "$dateTrunc": {
                                "date": "$timestamp",
                                "unit": "hour",
                            }
                        },
                        "label": "$label",
                    },
                    "count": {"$sum": 1},
                }},

                # Stage 3: sort chronologically so callers can iterate in order.
                {"$sort": {"_id.hour": 1}},
            ]

            result = self._collection.aggregate(pipeline)

            return [
                {
                    # Format as ISO string for consistent handling across
                    # Python and JavaScript (Chart.js time scale).
                    "hour":  doc["_id"]["hour"].strftime("%Y-%m-%dT%H:00:00"),
                    "label": doc["_id"]["label"],
                    "count": doc["count"],
                }
                for doc in result
            ]

        except Exception as error:
            logger.error(f"MongoDB get_hourly_buckets failed: {error}")
            return []


    def get_rolling_average(self, hours: int = 24) -> float:
        """
        Compute the mean detections per hour over the last `hours` hours
        using the aggregation pipeline.

        Pipeline stages:
            $match   → time window
            $group   → count per hour bucket
            $group   → average of per-hour counts

        Two $group stages are required because MongoDB cannot average
        across groups in a single stage — the first groups into hourly
        buckets, the second averages those bucket counts.

        Returns:
            Rolling average as a float, rounded to 1 decimal place.
        """
        if not self._enabled:
            return 0.0

        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

            pipeline = [
                {"$match": {"timestamp": {"$gte": cutoff}}},

                # First $group: count detections per hour bucket.
                {"$group": {
                    "_id": {
                        "$dateTrunc": {"date": "$timestamp", "unit": "hour"}
                    },
                    "count": {"$sum": 1},
                }},

                # Second $group: average the per-hour counts.
                # _id: null collapses all bucket documents into a single result.
                {"$group": {
                    "_id":     None,
                    "avg":     {"$avg": "$count"},
                    "buckets": {"$sum": 1},
                }},
            ]

            result = list(self._collection.aggregate(pipeline))
            if not result:
                return 0.0

            return round(result[0].get("avg", 0.0), 1)

        except Exception as error:
            logger.error(f"MongoDB get_rolling_average failed: {error}")
            return 0.0


    def get_recent(self, limit: int = 20) -> list[dict]:
        """
        Return the most recent detections from MongoDB, newest first.

        Used by the Render dashboard so it reads from Atlas rather than
        the local SQLite file (which is not accessible from Render).

        Returns:
            List of detection dicts with string timestamps (ISO format).
        """
        if not self._enabled:
            return []

        try:
            docs = self._collection.find(
                {},
                {"_id": 0},   # exclude the MongoDB ObjectId from results
            ).sort("timestamp", -1).limit(limit)

            results = []
            for doc in docs:
                # Convert BSON datetime back to ISO string for consistency
                # with the SQLite-based dashboard response format.
                if isinstance(doc.get("timestamp"), datetime):
                    doc["timestamp"] = doc["timestamp"].strftime(
                        "%Y-%m-%dT%H:%M:%S"
                    )
                results.append(doc)
            return results

        except Exception as error:
            logger.error(f"MongoDB get_recent failed: {error}")
            return []


    def get_environment_trend(self, hours: int = 24) -> list[dict]:
        """
        Return hourly average temperature and humidity readings over the
        last `hours` hours using the aggregation pipeline.

        Pipeline stages:
            $match   → time window, exclude null temp readings
            $group   → average temp and humidity per hour bucket
            $sort    → ascending by hour

        This powers the temperature trend chart on the dashboard with
        server-side averaging rather than raw-point plotting.

        Returns:
            [{"hour": ISO_str, "avg_temp": float, "avg_humidity": float}, ...]
        """
        if not self._enabled:
            return []

        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

            pipeline = [
                # Only include documents that have sensor readings.
                {"$match": {
                    "timestamp": {"$gte": cutoff},
                    "temp":      {"$ne": None},
                }},

                # Group by hour, averaging temp and humidity within each bucket.
                {"$group": {
                    "_id": {
                        "$dateTrunc": {"date": "$timestamp", "unit": "hour"}
                    },
                    "avg_temp":     {"$avg": "$temp"},
                    "avg_humidity": {"$avg": "$humidity"},
                }},

                {"$sort": {"_id": 1}},
            ]

            result = self._collection.aggregate(pipeline)

            return [
                {
                    "hour":         doc["_id"].strftime("%Y-%m-%dT%H:00:00"),
                    "avg_temp":     round(doc["avg_temp"], 2),
                    "avg_humidity": round(doc["avg_humidity"], 2),
                }
                for doc in result
            ]

        except Exception as error:
            logger.error(f"MongoDB get_environment_trend failed: {error}")
            return []


    def is_enabled(self) -> bool:
        """Return True if MongoDB is connected and operational."""
        return self._enabled