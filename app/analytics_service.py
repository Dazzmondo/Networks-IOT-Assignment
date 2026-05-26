"""
Purpose:
    Computes statistical analytics over the detection history stored in SQLite
    or MongoDB Atlas, depending on which backend is available.


Analytics produced:

    Rolling average (detections / hour):
        Mean of per-hour detection counts over the last 24 hours.
        Provides a stable baseline that smooths out short bursts.
        Formula: sum(hourly_counts) / number_of_hours_in_window

    Current hour count:
        Number of detections in the current calendar hour.
        Compared against the rolling average to flag unusual activity.

    Peak hour:
        The hour label (e.g. "14:00") with the highest detection count
        in the last 24 hours.  Useful for spotting recurring activity patterns
        (e.g. postman arrives every day at 10:00).

    Anomaly score (Z-score):
        Measures how many standard deviations the current hour count
        is above the 24-hour mean.
        Formula: (current_hour - mean) / std_dev
        Thresholds:
            score < 1.5  -> Normal
            1.5 <= score < 2.5 -> Elevated
            score >= 2.5 -> High

    Why Z-score?
        Simple threshold checks ("alert if > 5 detections") are fragile --
        the right threshold depends on how busy the environment normally is.
        A Z-score normalises against the system's own baseline so the
        anomaly detector self-calibrates to each deployment.


MongoDB vs SQLite analytics:
    When MongoService is connected, compute() and chart_data() delegate
    the heavy aggregation work to MongoDB's pipeline ($dateTrunc, $group,
    $avg, $sum).  This pushes computation to the database tier rather than
    pulling raw rows into Python -- more efficient at scale and demonstrates
    the aggregation pipeline from the Databases module.

    When MongoDB is not available, the same metrics are computed locally
    from SQLite rows using Python.  The output format is identical in both
    cases so dashboard.py and the SSE worker do not need to distinguish
    between backends.
"""

import math
from collections import defaultdict
from datetime import datetime, timedelta

from app.logger_service import logger

# Anomaly score thresholds.
_ANOMALY_ELEVATED = 1.5
_ANOMALY_HIGH     = 2.5

class AnalyticsService:
    """
    Computes rolling statistics and chart-ready bucket data.

    Prefers MongoDB aggregation pipeline when MongoService is connected.
    Falls back to SQLite-based Python computation when MongoDB is absent.

    Usage:
        analytics = AnalyticsService(db_service, mongo_service)
        stats      = analytics.compute()
        c_data     = analytics.chart_data()
    """

    def __init__(self, db_service, mongo_service=None):
        self._db = db_service

        # -- Store optional MongoDB reference ---------------------------------
        # _mongo is None when MongoDB is not configured.
        # Methods check self._mongo.is_enabled() before delegating to Atlas
        # so the SQLite fallback path is always available.
        self._mongo = mongo_service


    # -- Public API -----------------------------------------------------------
    def compute(self) -> dict:
        """
        Compute rolling average, current hour count, peak hour, and anomaly score.

        Delegates to MongoDB aggregation pipeline when available.
        Falls back to SQLite + Python computation otherwise.

        Returns:
            {
                "rolling_avg":   float,
                "current_hour":  int,
                "peak_hour":     str,
                "anomaly_score": float,
                "anomaly_label": str,
                "anomaly_class": str,
                "source":        str  ("mongodb" | "sqlite"),
            }
        """
        if self._mongo and self._mongo.is_enabled():
            return self._compute_from_mongo()
        return self._compute_from_sqlite()


    def chart_data(self) -> dict:
        """
        Build Chart.js-ready time-series data for the last 24 hours.

        Delegates to MongoDB when available for server-side bucketing.
        Falls back to SQLite row processing in Python otherwise.

        Returns:
            {
                "timeseries": {
                    "dog":    [{"x": ISO_str, "y": int}, ...],
                    "person": [{"x": ISO_str, "y": int}, ...],
                    "temp":   [{"x": ISO_str, "y": float}, ...],
                },
                "hourly": {
                    "labels":           [str, ...],
                    "counts":           [int, ...],
                    "rolling_avg_line": [float, ...],
                },
                "counts": {"dog": int, "person": int},
            }
        """
        if self._mongo and self._mongo.is_enabled():
            return self._chart_data_from_mongo()
        return self._chart_data_from_sqlite()


    # -- MongoDB-backed computation -------------------------------------------
    def _compute_from_mongo(self) -> dict:
        """
        Compute analytics using MongoDB aggregation pipeline results.

        get_hourly_buckets() returns pre-grouped (hour, label, count) tuples
        from Atlas. No raw rows are transferred. Python only post-processes
        the already-aggregated bucket list, not individual detection records.
        """
        try:
            buckets = self._mongo.get_hourly_buckets(hours=24)

            # Aggregate per-(hour, label) bucket counts into per-hour totals.
            hourly_totals = defaultdict(int)
            for b in buckets:
                hourly_totals[b["hour"]] += b["count"]

            # -- Current hour ------------------------------------------------
            current_key  = datetime.now().strftime("%Y-%m-%dT%H:00:00")
            current_hour = hourly_totals.get(current_key, 0)

            # -- Rolling average (pre-computed by MongoDB) --------------------
            rolling_avg = self._mongo.get_rolling_average(hours=24)

            # -- Peak hour ---------------------------------------------------
            if hourly_totals and max(hourly_totals.values()) > 0:
                peak_key  = max(hourly_totals, key=hourly_totals.get)
                peak_hour = datetime.fromisoformat(peak_key).strftime("%H:%M")
            else:
                peak_hour = "---"

            # -- Anomaly score (Z-score against hourly bucket counts) --------
            counts        = list(hourly_totals.values())
            anomaly_score = self._zscore(current_hour, counts)
            anomaly_label, anomaly_class = self._anomaly_classification(anomaly_score)

            return {
                "rolling_avg":   rolling_avg,
                "current_hour":  current_hour,
                "peak_hour":     peak_hour,
                "anomaly_score": round(anomaly_score, 2),
                "anomaly_label": anomaly_label,
                "anomaly_class": anomaly_class,
                # Source label lets the dashboard show which backend provided the analytics
                "source":        "mongodb",
            }

        except Exception as error:
            logger.error(f"MongoDB analytics compute failed: {error}. Falling back to SQLite.")
            return self._compute_from_sqlite()


    def _chart_data_from_mongo(self) -> dict:
        """
        Build Chart.js series using MongoDB aggregation pipeline results.

        get_hourly_buckets() provides detection counts per (hour, label).
        get_environment_trend() provides averaged temperature per hour.
        Both are aggregated server-side -- only summary data is transferred.
        """
        try:
            buckets  = self._mongo.get_hourly_buckets(hours=24)
            env_data = self._mongo.get_environment_trend(hours=24)

            # Separate dog and person counts from the flat bucket list.
            hourly_dog    = defaultdict(int)
            hourly_person = defaultdict(int)
            for b in buckets:
                if b["label"] == "dog":
                    hourly_dog[b["hour"]] += b["count"]
                elif b["label"] == "person":
                    hourly_person[b["hour"]] += b["count"]

            # Temperature trend from environment aggregation.
            hourly_temp = {e["hour"]: e["avg_temp"] for e in env_data}

            # Build ordered 24-hour bucket list -- always 24 points.
            now         = datetime.now().replace(minute=0, second=0, microsecond=0)
            bucket_keys = [
                (now - timedelta(hours=i)).strftime("%Y-%m-%dT%H:00:00")
                for i in range(23, -1, -1)
            ]

            dog_series    = [{"x": b, "y": hourly_dog.get(b, 0)}    for b in bucket_keys]
            person_series = [{"x": b, "y": hourly_person.get(b, 0)} for b in bucket_keys]
            temp_series   = [
                {"x": b, "y": hourly_temp[b]}
                for b in bucket_keys if b in hourly_temp
            ]

            hourly_labels = [
                datetime.fromisoformat(b).strftime("%H:%M") for b in bucket_keys
            ]
            hourly_counts = [
                hourly_dog.get(b, 0) + hourly_person.get(b, 0) for b in bucket_keys
            ]

            # Rolling average flat line repeated for all bucket positions.
            rolling_avg = self._mongo.get_rolling_average(hours=24)
            avg_line    = [rolling_avg] * len(bucket_keys)

            counts = self._mongo.get_counts()

            return {
                "timeseries": {
                    "dog":    dog_series,
                    "person": person_series,
                    "temp":   temp_series,
                },
                "hourly": {
                    "labels":           hourly_labels,
                    "counts":           hourly_counts,
                    "rolling_avg_line": avg_line,
                },
                "counts": {
                    "dog":    counts.get("dog",    0),
                    "person": counts.get("person", 0),
                },
            }

        except Exception as error:
            logger.error(f"MongoDB chart_data failed: {error}. Falling back to SQLite.")
            return self._chart_data_from_sqlite()


    # -- SQLite-backed computation --------------------------------------------
    def _compute_from_sqlite(self) -> dict:
        """
        Compute analytics from raw SQLite rows using Python.

        Fetches all detections in the 24-hour window and builds hourly
        buckets locally. Less efficient than MongoDB aggregation
        """
        try:
            hourly = self._hourly_buckets_raw()

            counts      = list(hourly.values())
            total       = sum(counts)
            rolling_avg = round(total / 24, 1)

            current_key  = datetime.now().strftime("%Y-%m-%dT%H:00:00")
            current_hour = hourly.get(current_key, 0)

            if counts and max(counts) > 0:
                peak_key  = max(hourly, key=hourly.get)
                peak_hour = datetime.fromisoformat(peak_key).strftime("%H:%M")
            else:
                peak_hour = "---"

            anomaly_score = self._zscore(current_hour, counts)
            anomaly_label, anomaly_class = self._anomaly_classification(anomaly_score)

            return {
                "rolling_avg":   rolling_avg,
                "current_hour":  current_hour,
                "peak_hour":     peak_hour,
                "anomaly_score": round(anomaly_score, 2),
                "anomaly_label": anomaly_label,
                "anomaly_class": anomaly_class,
                "source":        "sqlite",
            }

        except Exception as error:
            logger.error(f"SQLite analytics compute failed: {error}")
            return self._empty_stats()


    def _chart_data_from_sqlite(self) -> dict:
        """
        Build Chart.js series from raw SQLite rows using Python bucketing.
        """
        try:
            rows          = self._db.get_last_24h()
            hourly_dog    = defaultdict(int)
            hourly_person = defaultdict(int)
            hourly_temp   = {}

            for row in rows:
                ts    = row["timestamp"][:13] + ":00:00"
                label = row.get("label", "")

                if label == "dog":
                    hourly_dog[ts] += 1
                elif label == "person":
                    hourly_person[ts] += 1

                if row.get("temp") is not None:
                    hourly_temp[ts] = row["temp"]

            now     = datetime.now().replace(minute=0, second=0, microsecond=0)
            buckets = [
                (now - timedelta(hours=i)).strftime("%Y-%m-%dT%H:00:00")
                for i in range(23, -1, -1)
            ]

            dog_series    = [{"x": b, "y": hourly_dog.get(b, 0)}    for b in buckets]
            person_series = [{"x": b, "y": hourly_person.get(b, 0)} for b in buckets]
            temp_series   = [
                {"x": b, "y": hourly_temp[b]}
                for b in buckets if b in hourly_temp
            ]

            hourly_labels = [
                datetime.fromisoformat(b).strftime("%H:%M") for b in buckets
            ]
            hourly_counts = [
                hourly_dog.get(b, 0) + hourly_person.get(b, 0) for b in buckets
            ]

            total       = sum(hourly_counts)
            rolling_avg = round(total / 24, 1)
            avg_line    = [rolling_avg] * len(buckets)

            counts = self._db.get_counts()

            return {
                "timeseries": {
                    "dog":    dog_series,
                    "person": person_series,
                    "temp":   temp_series,
                },
                "hourly": {
                    "labels":           hourly_labels,
                    "counts":           hourly_counts,
                    "rolling_avg_line": avg_line,
                },
                "counts": {
                    "dog":    counts.get("dog",    0),
                    "person": counts.get("person", 0),
                },
            }

        except Exception as error:
            logger.error(f"SQLite chart_data failed: {error}")
            return self._empty_chart_data()


    # -- Shared helpers -------------------------------------------------------
    def _hourly_buckets_raw(self) -> dict:
        """
        Return a dict mapping ISO hour strings to total detection counts
        for the last 24 hours, initialised to 0 for every hour so the
        rolling average denominator is always 24.
        """
        rows    = self._db.get_last_24h()
        now     = datetime.now().replace(minute=0, second=0, microsecond=0)
        buckets = {
            (now - timedelta(hours=i)).strftime("%Y-%m-%dT%H:00:00"): 0
            for i in range(24)
        }
        for row in rows:
            ts = row["timestamp"][:13] + ":00:00"
            if ts in buckets:
                buckets[ts] += 1
        return buckets


    @staticmethod
    def _zscore(value: int, population: list) -> float:
        """
        Compute Z-score of value against population.

        Z = (value - mean) / std_dev

        Returns 0.0 if std_dev is zero to avoid division-by-zero when
        the system is new or activity is perfectly uniform.
        """
        if not population:
            return 0.0
        mean     = sum(population) / len(population)
        variance = sum((x - mean) ** 2 for x in population) / len(population)
        std_dev  = math.sqrt(variance)
        if std_dev == 0:
            return 0.0
        return (value - mean) / std_dev


    @staticmethod
    def _anomaly_classification(score: float) -> tuple[str, str]:
        """
        Map a Z-score to a human-readable label and CSS badge class.

        Returns:
            (label, css_class) e.g. ("Elevated", "anomaly-elevated")
        """
        if score >= _ANOMALY_HIGH:
            return "High",     "anomaly-high"
        if score >= _ANOMALY_ELEVATED:
            return "Elevated", "anomaly-elevated"
        return "Normal",       "anomaly-normal"


    @staticmethod
    def _empty_stats() -> dict:
        """Safe fallback returned on DB error."""
        return {
            "rolling_avg":   0.0,
            "current_hour":  0,
            "peak_hour":     "---",
            "anomaly_score": 0.0,
            "anomaly_label": "Normal",
            "anomaly_class": "anomaly-normal",
            "source":        "unavailable",
        }


    @staticmethod
    def _empty_chart_data() -> dict:
        """Safe fallback returned on DB error."""
        return {
            "timeseries": {"dog": [], "person": [], "temp": []},
            "hourly": {"labels": [], "counts": [], "rolling_avg_line": []},
            "counts": {"dog": 0, "person": 0},
        }