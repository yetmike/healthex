"""Tests for auth.get_credentials.

These deliberately use real google.oauth2 Credentials objects and a fake
HTTP transport rather than mocking the library away, so google-auth's own
token parsing, expiry logic and refresh-grant handling are executed.
"""

import datetime as dt
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

from google.oauth2.credentials import Credentials

from healthex import auth


def _token_json(expiry: dt.datetime, refresh_token: str | None = "refresh-abc") -> dict[str, Any]:
    body: dict[str, Any] = {
        "token": "access-old",
        "refresh_token": refresh_token,
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "cid.apps.googleusercontent.com",
        "client_secret": "csecret",
        "scopes": auth.SCOPES,
        "expiry": expiry.replace(microsecond=0).isoformat(),
    }
    if refresh_token is None:
        del body["refresh_token"]
    return body


class _FakeResponse:
    """Shape google-auth's transport expects back."""

    def __init__(self, payload: dict[str, Any], status: int = 200) -> None:
        self.status = status
        self.data = json.dumps(payload).encode()


class _FakeRequest:
    """Stands in for google.auth.transport.requests.Request."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.calls: list[dict[str, Any]] = []

    def __call__(self, *args: Any, **kwargs: Any) -> _FakeResponse:
        self.calls.append(kwargs)
        return _FakeResponse(self.payload)


def test_valid_token_is_reused_without_network(tmp_path: Path) -> None:
    """A still-valid cached token must not trigger a refresh or a browser flow."""
    token_file = tmp_path / "token.json"
    future = dt.datetime.now(dt.UTC).replace(tzinfo=None) + dt.timedelta(hours=1)
    token_file.write_text(json.dumps(_token_json(future)))

    with patch.object(auth, "Request") as req, patch.object(auth, "InstalledAppFlow") as flow:
        creds = auth.get_credentials(tmp_path / "client_secret.json", token_file)

    assert creds.token == "access-old"
    assert creds.valid
    req.assert_not_called()
    flow.from_client_secrets_file.assert_not_called()


def test_expired_token_is_refreshed(tmp_path: Path) -> None:
    """Real google-auth refresh_grant runs against a fake transport."""
    token_file = tmp_path / "token.json"
    past = dt.datetime.now(dt.UTC).replace(tzinfo=None) - dt.timedelta(hours=1)
    token_file.write_text(json.dumps(_token_json(past)))

    fake_req = _FakeRequest(
        {"access_token": "access-new", "expires_in": 3600, "scope": " ".join(auth.SCOPES)}
    )
    with (
        patch.object(auth, "Request", return_value=fake_req),
        patch.object(auth, "InstalledAppFlow") as flow,
    ):
        creds = auth.get_credentials(tmp_path / "client_secret.json", token_file)

    assert creds.token == "access-new"
    assert creds.valid
    flow.from_client_secrets_file.assert_not_called()
    assert len(fake_req.calls) == 1  # exactly one token endpoint round trip

    # refreshed token is persisted, so the next run starts from the new token
    assert json.loads(token_file.read_text())["token"] == "access-new"


def test_refreshed_token_file_is_owner_only(tmp_path: Path) -> None:
    token_file = tmp_path / "token.json"
    past = dt.datetime.now(dt.UTC).replace(tzinfo=None) - dt.timedelta(hours=1)
    token_file.write_text(json.dumps(_token_json(past)))

    fake_req = _FakeRequest({"access_token": "access-new", "expires_in": 3600})
    with (
        patch.object(auth, "Request", return_value=fake_req),
        patch.object(auth, "InstalledAppFlow"),
    ):
        auth.get_credentials(tmp_path / "client_secret.json", token_file)

    assert token_file.stat().st_mode & 0o777 == 0o600


def test_missing_token_file_triggers_browser_flow(tmp_path: Path) -> None:
    token_file = tmp_path / "token.json"
    future = dt.datetime.now(dt.UTC).replace(tzinfo=None) + dt.timedelta(hours=1)
    new_creds = Credentials(
        **{  # type: ignore[no-untyped-call]
            k: v for k, v in _token_json(future).items() if k != "expiry"
        }
    )

    with patch.object(auth, "InstalledAppFlow") as flow, patch.object(auth, "Request"):
        flow.from_client_secrets_file.return_value.run_local_server.return_value = new_creds
        creds = auth.get_credentials(tmp_path / "client_secret.json", token_file)

    flow.from_client_secrets_file.assert_called_once()
    assert flow.from_client_secrets_file.call_args[0][1] == auth.SCOPES
    assert creds is new_creds
    assert token_file.exists()  # freshly authorised token got cached


def test_expired_without_refresh_token_falls_back_to_browser_flow(tmp_path: Path) -> None:
    """No refresh_token means refresh is impossible — must re-authorise, not crash."""
    token_file = tmp_path / "token.json"
    past = dt.datetime.now(dt.UTC).replace(tzinfo=None) - dt.timedelta(hours=1)
    token_file.write_text(json.dumps(_token_json(past, refresh_token=None)))

    future = dt.datetime.now(dt.UTC).replace(tzinfo=None) + dt.timedelta(hours=1)
    new_creds = Credentials(
        **{  # type: ignore[no-untyped-call]
            k: v for k, v in _token_json(future).items() if k != "expiry"
        }
    )

    with patch.object(auth, "InstalledAppFlow") as flow, patch.object(auth, "Request") as req:
        flow.from_client_secrets_file.return_value.run_local_server.return_value = new_creds
        creds = auth.get_credentials(tmp_path / "client_secret.json", token_file)

    req.assert_not_called()
    flow.from_client_secrets_file.assert_called_once()
    assert creds is new_creds


def test_scopes_are_the_three_readonly_health_scopes() -> None:
    """A scope change silently breaks sync at runtime with a 403."""
    assert len(auth.SCOPES) == 3
    assert all(s.startswith("https://www.googleapis.com/auth/googlehealth.") for s in auth.SCOPES)
    assert all(s.endswith(".readonly") for s in auth.SCOPES)
