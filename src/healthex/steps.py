"""Parse raw Google Health API steps dataPoints into row dicts ready for upsert."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from typing import Any


def parse_day(point: dict[str, Any], user_id: str | None = None) -> dict[str, Any]:
    """
    Map a single steps dataPoint from the Google Health API v4 into a dict
    matching the daily_steps table columns.

    Expected API shape (mirrors sleep — needs confirmation against real response):
      point.name            = "users/<uid>/dataTypes/steps/dataPoints/<id>"
      point.dataSource.platform = "FITBIT"
      point.steps.interval.startTime  (UTC ISO-8601, midnight of the day)
      point.steps.interval.startUtcOffset  e.g. "7200s"
      point.steps.summary.steps  (string)
    """
    name: str = point.get("name", "")
    if user_id is None:
        parts = name.split("/")
        user_id = parts[1] if len(parts) > 1 else "me"

    steps_data: dict[str, Any] = point.get("steps", {})
    interval: dict[str, Any] = steps_data.get("interval", {})

    start_time: str = interval.get("startTime", "")
    utc_offset_str: str = interval.get("startUtcOffset", "0s")
    civil_date = _civil_date(start_time, utc_offset_str)

    summary: dict[str, Any] = steps_data.get("summary", {})
    raw_steps = summary.get("steps")
    steps = int(raw_steps) if raw_steps is not None else 0

    source_platform: str | None = None
    ds: Any = point.get("dataSource", {})
    if isinstance(ds, dict):
        source_platform = ds.get("platform") or ds.get("recordingMethod")

    row_id = hashlib.sha256(f"{user_id}|{civil_date}".encode()).hexdigest()[:32]

    return {
        "id": row_id,
        "user_id": user_id,
        "step_date": civil_date,
        "steps": steps,
        "source_platform": source_platform,
        "raw": point,
    }


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
