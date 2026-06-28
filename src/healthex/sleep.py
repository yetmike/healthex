"""Parse raw Google Health API sleep dataPoints into row dicts ready for upsert."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any


def parse_session(point: dict[str, Any], user_id: str | None = None) -> dict[str, Any]:
    """
    Map a single sleep dataPoint from the Google Health API v4 into a dict that
    matches the sleep_sessions table columns.

    Real API shape (confirmed 2026-06-28):
      point.name            = "users/<uid>/dataTypes/sleep/dataPoints/<id>"
      point.dataSource.platform = "FITBIT"
      point.sleep.interval.startTime / endTime  (UTC ISO-8601)
      point.sleep.interval.startUtcOffset        e.g. "7200s"
      point.sleep.type       = "STAGES" | "CLASSIC"
      point.sleep.summary.minutesAsleep / minutesAwake / minutesInSleepPeriod  (strings)
      point.sleep.summary.stagesSummary = [{type, minutes (str), count (str)}, ...]
      No efficiency or sleep_score in the API response.
    """
    # Extract user_id from the resource name if not provided
    name: str = point.get("name", "")
    if user_id is None:
        parts = name.split("/")
        user_id = parts[1] if len(parts) > 1 else "me"

    sleep: dict[str, Any] = point.get("sleep", {})
    interval: dict[str, Any] = sleep.get("interval", {})

    start_time: str = interval.get("startTime", "")
    end_time: str = interval.get("endTime", "")
    utc_offset_str: str = interval.get("startUtcOffset", "0s")

    civil_date = _civil_date(start_time, utc_offset_str)

    # Stable row ID: hash of (user_id, start_time)
    row_id = hashlib.sha256(f"{user_id}|{start_time}".encode()).hexdigest()[:32]

    sleep_type: str | None = sleep.get("type")  # "STAGES" | "CLASSIC"

    source_platform: str | None = None
    ds: Any = point.get("dataSource", {})
    if isinstance(ds, dict):
        source_platform = ds.get("platform") or ds.get("recordingMethod")

    summary: dict[str, Any] = sleep.get("summary", {})
    minutes_asleep = _int(summary.get("minutesAsleep"))
    minutes_awake = _int(summary.get("minutesAwake"))
    minutes_in_period = _int(summary.get("minutesInSleepPeriod"))
    duration_seconds = minutes_in_period * 60 if minutes_in_period is not None else None

    # Derive efficiency = asleep / in_period * 100 (API doesn't provide it)
    efficiency = (
        round(minutes_asleep / minutes_in_period * 100, 2)
        if minutes_asleep is not None and minutes_in_period and minutes_in_period > 0
        else None
    )

    # stages: [{type, minutes, count}, ...]
    stages_map: dict[str, int] = {}
    for stage in summary.get("stagesSummary", []):
        t = str(stage.get("type", "")).upper()
        stages_map[t] = int(stage.get("minutes", 0))

    minutes_light = stages_map.get("LIGHT")
    minutes_deep = stages_map.get("DEEP")
    minutes_rem = stages_map.get("REM")
    # AWAKE in stages vs top-level minutesAwake — prefer top-level
    if minutes_awake is None:
        minutes_awake = stages_map.get("AWAKE")

    return {
        "id": row_id,
        "user_id": user_id,
        "civil_date": civil_date,
        "start_time": start_time,
        "end_time": end_time,
        "sleep_type": sleep_type,
        "duration_seconds": duration_seconds,
        "minutes_asleep": minutes_asleep,
        "minutes_awake": minutes_awake,
        "minutes_light": minutes_light,
        "minutes_deep": minutes_deep,
        "minutes_rem": minutes_rem,
        "efficiency": efficiency,  # derived: minutes_asleep / minutes_in_period * 100
        "sleep_score": None,       # not in API
        "source_platform": source_platform,
        "raw": point,
    }


def _int(val: Any, scale: int = 1) -> int | None:
    """Convert a string/int value to int, optionally multiplying by scale."""
    if val is None:
        return None
    try:
        return int(val) * scale
    except (ValueError, TypeError):
        return None


def _civil_date(start_time_utc: str, utc_offset_str: str) -> str | None:
    """
    Compute the local calendar date for the night boundary.
    startTime is UTC; utcOffset is like "7200s" (seconds east of UTC).
    """
    if not start_time_utc:
        return None
    try:
        dt = datetime.fromisoformat(start_time_utc.replace("Z", "+00:00"))
        offset_seconds = int(utc_offset_str.rstrip("s"))
        local_dt = dt + timedelta(seconds=offset_seconds)
        return local_dt.date().isoformat()
    except (ValueError, AttributeError):
        return None
