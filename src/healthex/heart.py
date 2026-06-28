"""Parse Google Health API daily RHR and HRV dataPoints."""

from __future__ import annotations

import hashlib
from typing import Any

_RMSSD_KEY = "deepSleepRootMeanSquareOfSuccessiveDifferencesMilliseconds"


def parse_rhr(point: dict[str, Any], user_id: str = "me") -> dict[str, Any] | None:
    data: dict[str, Any] = point.get("dailyRestingHeartRate", {})
    date_str = _date(data.get("date"))
    raw_bpm = data.get("beatsPerMinute")
    if not date_str or raw_bpm is None:
        return None

    meta: dict[str, Any] = data.get("dailyRestingHeartRateMetadata", {})
    ds: Any = point.get("dataSource", {})
    source_platform = (
        ds.get("platform") or ds.get("recordingMethod") if isinstance(ds, dict) else None
    )

    return {
        "id": hashlib.sha256(f"{user_id}|rhr|{date_str}".encode()).hexdigest()[:32],
        "user_id": user_id,
        "rhr_date": date_str,
        "bpm": int(raw_bpm),
        "calculation_method": meta.get("calculationMethod"),
        "source_platform": source_platform,
        "raw": point,
    }


def parse_hrv(point: dict[str, Any], user_id: str = "me") -> dict[str, Any] | None:
    data: dict[str, Any] = point.get("dailyHeartRateVariability", {})
    date_str = _date(data.get("date"))
    avg_hrv = data.get("averageHeartRateVariabilityMilliseconds")
    if not date_str or avg_hrv is None:
        return None

    ds: Any = point.get("dataSource", {})
    source_platform = (
        ds.get("platform") or ds.get("recordingMethod") if isinstance(ds, dict) else None
    )
    non_rem_raw = data.get("nonRemHeartRateBeatsPerMinute")
    rmssd_raw = data.get(_RMSSD_KEY)

    return {
        "id": hashlib.sha256(f"{user_id}|hrv|{date_str}".encode()).hexdigest()[:32],
        "user_id": user_id,
        "hrv_date": date_str,
        "avg_hrv_ms": float(avg_hrv),
        "non_rem_bpm": int(non_rem_raw) if non_rem_raw is not None else None,
        "entropy": float(data["entropy"]) if data.get("entropy") is not None else None,
        "deep_sleep_rmssd_ms": float(rmssd_raw) if rmssd_raw is not None else None,
        "source_platform": source_platform,
        "raw": point,
    }


def _date(d: Any) -> str | None:
    if not isinstance(d, dict):
        return None
    try:
        return f"{d['year']:04d}-{d['month']:02d}-{d['day']:02d}"
    except (KeyError, TypeError):
        return None
