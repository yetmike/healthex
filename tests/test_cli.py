"""Tests for the CLI sync command argument handling."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from healthex.cli import app

runner = CliRunner()


def _mock_sync_deps() -> tuple[MagicMock, MagicMock]:
    """Return a stack of patches that prevents any real I/O during sync."""
    mock_creds = MagicMock()
    mock_creds.token = "fake-token"
    mock_creds.valid = True

    mock_hc = MagicMock()
    mock_hc.__enter__ = lambda s: s
    mock_hc.__exit__ = MagicMock(return_value=False)
    mock_hc.list_sleep.return_value = []
    mock_hc.list_steps.return_value = []
    mock_hc.list_daily.return_value = []

    return mock_creds, mock_hc


def test_sync_requires_since_or_days() -> None:
    """Running sync with neither --since nor --days must fail."""
    result = runner.invoke(app, ["sync"])
    assert result.exit_code != 0


def test_sync_since_and_days_are_mutually_exclusive() -> None:
    """Passing both --since and --days must fail."""
    result = runner.invoke(app, ["sync", "--since", "2026-01-01T00:00:00", "--days", "3"])
    assert result.exit_code != 0


def test_sync_days_accepted() -> None:
    """--days N should resolve to a --since value and run normally."""
    mock_creds, mock_hc = _mock_sync_deps()
    with (
        patch("healthex.cli.auth.get_credentials", return_value=mock_creds),
        patch("healthex.cli.client.HealthClient", return_value=mock_hc),
        patch("healthex.cli.repository.upsert_sleep", return_value=0),
        patch("healthex.cli.repository.upsert_steps", return_value=0),
        patch("healthex.cli.repository.upsert_rhr", return_value=0),
        patch("healthex.cli.repository.upsert_hrv", return_value=0),
    ):
        result = runner.invoke(app, ["sync", "--days", "3"])
    assert result.exit_code == 0


def test_sync_since_accepted() -> None:
    """--since should still work (backwards compat)."""
    mock_creds, mock_hc = _mock_sync_deps()
    with (
        patch("healthex.cli.auth.get_credentials", return_value=mock_creds),
        patch("healthex.cli.client.HealthClient", return_value=mock_hc),
        patch("healthex.cli.repository.upsert_sleep", return_value=0),
        patch("healthex.cli.repository.upsert_steps", return_value=0),
        patch("healthex.cli.repository.upsert_rhr", return_value=0),
        patch("healthex.cli.repository.upsert_hrv", return_value=0),
    ):
        result = runner.invoke(app, ["sync", "--since", "2026-01-01T00:00:00"])
    assert result.exit_code == 0


def test_missing_database_url_is_a_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """No URL anywhere must fail loudly, not fall back to localhost."""
    from healthex.config import settings

    monkeypatch.setattr(settings, "database_url", None)
    result = runner.invoke(app, ["db-init"])

    assert result.exit_code != 0
    assert "No database URL" in result.output


def test_database_url_flag_overrides_env(monkeypatch: pytest.MonkeyPatch, db_url: str) -> None:
    """--database-url wins over DATABASE_URL/.env."""
    from healthex.cli import _resolve_db_url
    from healthex.config import settings

    monkeypatch.setattr(settings, "database_url", "postgresql+psycopg://from:env@h/db")
    assert _resolve_db_url(db_url) == db_url
    assert _resolve_db_url(None) == "postgresql+psycopg://from:env@h/db"
