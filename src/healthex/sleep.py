"""Parse raw Google Health API sleep dataPoints into row dicts ready for upsert."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
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
      No efficiency or sleep_score in the API — both are derived here.
    """
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

    stages_map: dict[str, int] = {}
    for stage in summary.get("stagesSummary", []):
        t = str(stage.get("type", "")).upper()
        stages_map[t] = int(stage.get("minutes", 0))

    minutes_light = stages_map.get("LIGHT")
    minutes_deep = stages_map.get("DEEP")
    minutes_rem = stages_map.get("REM")
    if minutes_awake is None:
        minutes_awake = stages_map.get("AWAKE")

    # Derived metrics (not in API)
    efficiency = _derive_efficiency(minutes_asleep, minutes_in_period)
    sleep_score = _derive_sleep_score(minutes_asleep, minutes_in_period, minutes_deep, minutes_rem)

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
        "efficiency": efficiency,
        "sleep_score": sleep_score,
        "source_platform": source_platform,
        "raw": point,
    }


def _derive_efficiency(minutes_asleep: int | None, minutes_in_period: int | None) -> float | None:
    """minutes_asleep / minutes_in_period * 100, rounded to 2 dp."""
    if minutes_asleep is None or not minutes_in_period:
        return None
    return round(minutes_asleep / minutes_in_period * 100, 2)


def _derive_sleep_score(
    minutes_asleep: int | None,
    minutes_in_period: int | None,
    minutes_deep: int | None,
    minutes_rem: int | None,
) -> int | None:
    """
    Proxy 0-100 sleep score approximating Fitbit's algorithm from available fields.

    Components:
      Duration    (0-40): minutes_asleep scaled to 8h target
      Efficiency  (0-30): minutes_asleep / minutes_in_period
      Stage quality (0-30): (deep + REM) as % of asleep, target ~45%

    Not the actual Fitbit score (which also uses HR and SpO2 not in the API).
    """
    if minutes_asleep is None or not minutes_in_period:
        return None

    # Duration: 480 min (8h) = full 40 pts, linear below
    duration_score = min(minutes_asleep / 480 * 40, 40.0)

    # Efficiency
    efficiency_score = (minutes_asleep / minutes_in_period) * 30

    # Stage quality: deep + REM vs asleep time, ideal ~45%
    stage_score = 0.0
    if minutes_deep is not None and minutes_rem is not None and minutes_asleep > 0:
        deep_rem_pct = (minutes_deep + minutes_rem) / minutes_asleep
        stage_score = min(deep_rem_pct / 0.45 * 30, 30.0)

    return min(max(round(duration_score + efficiency_score + stage_score), 0), 100)


def _int(val: Any, scale: int = 1) -> int | None:
    if val is None:
        return None
    try:
        return int(val) * scale
    except (ValueError, TypeError):
        return None


def _civil_date(start_time_utc: str, utc_offset_str: str) -> str | None:
    if not start_time_utc:
        return None
    try:
        dt = datetime.fromisoformat(start_time_utc.replace("Z", "+00:00"))
        offset_seconds = int(utc_offset_str.rstrip("s"))
        local_dt = dt + timedelta(seconds=offset_seconds)
        return local_dt.date().isoformat()
    except (ValueError, AttributeError):
        return None
