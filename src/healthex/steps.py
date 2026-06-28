"""Parse and aggregate Google Health API steps dataPoints into daily rows."""

from __future__ import annotations

import hashlib
from typing import Any


def aggregate_days(points: list[dict[str, Any]], user_id: str = "me") -> list[dict[str, Any]]:
    """
    Aggregate raw steps dataPoints (one per short interval) into one row per civil date.

    Real API shape (confirmed 2026-06-28):
      point.steps.count                          string, e.g. "25"
      point.steps.interval.civilStartTime.date   {year, month, day}
      point.dataSource.platform                  "HEALTH_KIT"

    The API returns many sub-minute intervals per day; we SUM steps per civil date.
    """
    daily: dict[str, dict[str, Any]] = {}

    for point in points:
        steps_data: dict[str, Any] = point.get("steps", {})
        raw_count = steps_data.get("count")
        count = int(raw_count) if raw_count is not None else 0

        civil_date = _civil_date(steps_data)
        if civil_date is None:
            continue

        source_platform: str | None = None
        ds: Any = point.get("dataSource", {})
        if isinstance(ds, dict):
            source_platform = ds.get("platform") or ds.get("recordingMethod")

        if civil_date not in daily:
            daily[civil_date] = {
                "steps": 0,
                "source_platform": source_platform,
                "raw_sample": point,
            }
        daily[civil_date]["steps"] += count

    rows = []
    for civil_date, data in daily.items():
        row_id = hashlib.sha256(f"{user_id}|{civil_date}".encode()).hexdigest()[:32]
        rows.append({
            "id": row_id,
            "user_id": user_id,
            "step_date": civil_date,
            "steps": data["steps"],
            "source_platform": data["source_platform"],
            "raw": data["raw_sample"],
        })

    return rows


def _civil_date(steps_data: dict[str, Any]) -> str | None:
    try:
        d = steps_data["interval"]["civilStartTime"]["date"]
        return f"{d['year']:04d}-{d['month']:02d}-{d['day']:02d}"
    except (KeyError, TypeError):
        return None
