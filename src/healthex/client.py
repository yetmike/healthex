import datetime as dt
from typing import Any

import httpx

BASE = "https://health.googleapis.com/v4"

# The API caps pageSize at 10000; the defaults (1440, or 25 for sleep) mean
# many more round trips than necessary.
_PAGE_SIZE = "10000"


def _rfc3339(since_iso: str) -> str:
    """The filter grammar wants an explicit zone; --since is naive local ISO."""
    return since_iso if since_iso.endswith("Z") or "+" in since_iso[10:] else f"{since_iso}Z"


def _civil(d: dt.date) -> dict[str, int]:
    return {"year": d.year, "month": d.month, "day": d.day}


def _utc(t: dt.datetime) -> str:
    return t.astimezone(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class HealthClient:
    """Thin wrapper around the Google Health REST API."""

    def __init__(self, access_token: str) -> None:
        self._c = httpx.Client(
            base_url=BASE,
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
            timeout=30.0,
        )

    def list_steps(self, since_iso: str) -> list[dict[str, object]]:
        points: list[dict[str, object]] = []
        params: dict[str, str] = {
            "pageSize": _PAGE_SIZE,
            "filter": f'steps.interval.start_time >= "{_rfc3339(since_iso)}"',
        }
        while True:
            r = self._c.get("/users/me/dataTypes/steps/dataPoints", params=params)
            r.raise_for_status()
            body = r.json()
            for p in body.get("dataPoints", []):
                start = str(p.get("steps", {}).get("interval", {}).get("startTime", ""))
                if start >= since_iso:
                    points.append(p)
            token = body.get("nextPageToken")
            if not token:
                return points
            params["pageToken"] = str(token)

    def list_daily(self, data_type: str, since_iso: str | None = None) -> list[dict[str, object]]:
        params: dict[str, str] = {"pageSize": _PAGE_SIZE}
        if since_iso is not None:
            # daily-resting-heart-rate -> daily_resting_heart_rate.date
            member = data_type.replace("-", "_")
            params["filter"] = f'{member}.date >= "{since_iso[:10]}"'

        return self._get_all(data_type, params)

    def list_exercises(self, since_iso: str) -> list[dict[str, object]]:
        # Sessions filter on civil start time only, and page at 25 max.
        flt = f'exercise.interval.civil_start_time >= "{since_iso[:10]}"'
        return self._get_all("exercise", {"pageSize": "25", "filter": flt})

    def daily_rollup(
        self, data_type: str, start: dt.date, end: dt.date, chunk_days: int = 90
    ) -> list[dict[str, object]]:
        """One aggregate per civil day in [start, end), over the reconciled
        (de-duplicated, on-wrist) stream. The API caps the range per request at
        90 days, or 14 for a few types, hence the chunking."""
        points: list[dict[str, object]] = []
        while start < end:
            stop = min(start + dt.timedelta(days=chunk_days), end)
            body = {
                "range": {"start": {"date": _civil(start)}, "end": {"date": _civil(stop)}},
                "windowSizeDays": 1,
            }
            points += self._post_all(f"{data_type}/dataPoints:dailyRollUp", body)
            start = stop
        return points

    def rollup(
        self, data_type: str, start: dt.datetime, end: dt.datetime, window_seconds: int
    ) -> list[dict[str, object]]:
        """Fixed-width aggregates over physical time; same 14-day cap, chunked."""
        points: list[dict[str, object]] = []
        while start < end:
            stop = min(start + dt.timedelta(days=14), end)
            body = {
                "range": {"startTime": _utc(start), "endTime": _utc(stop)},
                "windowSize": f"{window_seconds}s",
                "pageSize": int(_PAGE_SIZE),
            }
            points += self._post_all(f"{data_type}/dataPoints:rollUp", body)
            start = stop
        return points

    def _get_all(self, data_type: str, params: dict[str, str]) -> list[dict[str, object]]:
        points: list[dict[str, object]] = []
        while True:
            r = self._c.get(f"/users/me/dataTypes/{data_type}/dataPoints", params=params)
            r.raise_for_status()
            body = r.json()
            points.extend(body.get("dataPoints", []))
            token = body.get("nextPageToken")
            if not token:
                return points
            params["pageToken"] = str(token)

    def _post_all(self, path: str, body: dict[str, Any]) -> list[dict[str, object]]:
        points: list[dict[str, object]] = []
        while True:
            r = self._c.post(f"/users/me/dataTypes/{path}", json=body)
            r.raise_for_status()
            data = r.json()
            points.extend(data.get("rollupDataPoints", []))
            token = data.get("nextPageToken")
            if not token:
                return points
            body = {**body, "pageToken": token}

    def list_sleep(self, since_iso: str) -> list[dict[str, object]]:
        points: list[dict[str, object]] = []
        # Sleep is a session type: only end_time is a filterable member, so the
        # server returns a superset (a session ending after `since` may have
        # started before it) and the start_time check below narrows it exactly.
        params: dict[str, str] = {
            "pageSize": _PAGE_SIZE,
            "filter": f'sleep.interval.end_time >= "{_rfc3339(since_iso)}"',
        }
        while True:
            r = self._c.get("/users/me/dataTypes/sleep/dataPoints", params=params)
            r.raise_for_status()
            body = r.json()
            for p in body.get("dataPoints", []):
                start = str(p.get("sleep", {}).get("interval", {}).get("startTime", ""))
                if start >= since_iso:
                    points.append(p)
            token = body.get("nextPageToken")
            if not token:
                return points
            params["pageToken"] = str(token)

    def close(self) -> None:
        self._c.close()

    def __enter__(self) -> "HealthClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
