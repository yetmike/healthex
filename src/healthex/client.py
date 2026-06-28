import httpx

BASE = "https://health.googleapis.com/v4"


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
        params: dict[str, str] = {"pageSize": "1000"}
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

    def list_daily(self, data_type: str) -> list[dict[str, object]]:
        points: list[dict[str, object]] = []
        params: dict[str, str] = {"pageSize": "1000"}
        while True:
            r = self._c.get(f"/users/me/dataTypes/{data_type}/dataPoints", params=params)
            r.raise_for_status()
            body = r.json()
            points.extend(body.get("dataPoints", []))
            token = body.get("nextPageToken")
            if not token:
                return points
            params["pageToken"] = str(token)

    def list_sleep(self, since_iso: str) -> list[dict[str, object]]:
        points: list[dict[str, object]] = []
        params: dict[str, str] = {"pageSize": "50"}
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
