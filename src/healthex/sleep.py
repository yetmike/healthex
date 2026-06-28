"""Parse raw Google Health API sleep dataPoints into row dicts ready for upsert."""

from __future__ import annotations

import hashlib
from typing import Any


def _int(val: Any) -> int | None:  # noqa: ANN401
    """Return int or None."""
    return int(val) if val is not None else None


def _float(val: Any) -> float | None:  # noqa: ANN401
    """Return float or None."""
    return float(val) if val is not None else None


def parse_session(point: dict[str, Any], user_id: str = "me") -> dict[str, Any]:
    """
    Map a single sleep dataPoint from the Google Health API into a dict that matches
    the sleep_sessions table columns.

    The exact JSON shape should be confirmed via the OAuth Playground (plan §3g) before
    hardening column mappings.  Fields that aren't present in the API response are left
    as None so the schema's nullable columns absorb them gracefully.
    """
    # Top-level interval
    interval: dict[str, Any] = point.get("interval", {})
    start_time: str = interval.get("startTime", "")
    end_time: str = interval.get("endTime", "")

    # Stable ID: hash of (user_id, start_time) so re-fetching the same point is idempotent
    row_id = hashlib.sha256(f"{user_id}|{start_time}".encode()).hexdigest()[:32]

    # The API returns a "civil_date" field for the night boundary (e.g. "2026-06-27")
    civil_date: str | None = point.get("civil_date") or point.get("civilDate")

    # Top-level summary; field names may differ — verify against real response
    summary: dict[str, Any] = point.get("summary", {})
    sleep_type: str | None = point.get("sleepType") or point.get("type")
    source_platform: str | None = _extract_source(point)

    # Duration fields — common names seen in legacy Fitbit API migration guide
    duration_seconds = _int(summary.get("durationSeconds") or summary.get("duration_seconds"))
    minutes_asleep = _int(summary.get("minutesAsleep") or summary.get("minutes_asleep"))
    minutes_awake = _int(summary.get("minutesAwake") or summary.get("minutes_awake"))
    efficiency = _float(summary.get("efficiency"))
    sleep_score = _int(summary.get("sleepScore") or summary.get("sleep_score"))

    # Stage breakdown lives under stages or summary.stages
    stages: dict[str, Any] = summary.get("stages", {})
    minutes_light = _int(stages.get("light") or stages.get("minutesLight"))
    minutes_deep = _int(stages.get("deep") or stages.get("minutesDeep"))
    minutes_rem = _int(stages.get("rem") or stages.get("minutesRem"))

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
        "raw": point,  # full raw payload stored as JSONB
    }


def _extract_source(point: dict[str, Any]) -> str | None:
    """Best-effort extraction of source platform (e.g. 'FITBIT', 'PIXEL_WATCH')."""
    ds = point.get("dataSource") or point.get("data_source") or {}
    if isinstance(ds, dict):
        return str(ds.get("type") or ds.get("dataStreamName") or "") or None
    return None
