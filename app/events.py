"""
Purpose:
    Defines all named system events as module-level string constants.

    Having all event codes in one place means the full set of events the
    system can produce is visible at a glance.

    These event codes must EXACTLY match the event codes configured in the
    Blynk console (case-sensitive).
"""

# ── Detection events ──────────────────────────────────────────────────────────────
DOG_DETECTED_EVENT   = "dog_detected"
HUMAN_DETECTED_EVENT = "human_detected"

# ── System lifecycle events ─────────────────────────────────────────────────────
SYSTEM_START_EVENT = "system_started"
SYSTEM_ERROR_EVENT = "system_error"

# ── Camera events ───────────────────────────────────────────────────────────────
CAMERA_OFFLINE_EVENT = "camera_offline"
