"""Tests for config.Settings — exercises real pydantic-settings parsing.

Settings is instantiated per-test (not the module singleton) so env and
.env handling is actually executed rather than covered at import time.
"""

from pathlib import Path

import pytest

from healthex.config import Settings


def test_defaults_when_no_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for var in ("DATABASE_URL", "GOOGLE_CLIENT_SECRET_FILE", "HEALTHEX_TOKEN_FILE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.chdir(tmp_path)  # no .env to pick up

    s = Settings()
    assert s.database_url.startswith("postgresql+psycopg://")
    assert s.google_client_secret_file == Path("client_secret.json")
    assert s.healthex_token_file == Path("token.json")


def test_env_var_overrides_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@example:5432/db")

    assert Settings().database_url == "postgresql+psycopg://u:p@example:5432/db"


def test_env_var_is_case_insensitive(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("database_url", "postgresql+psycopg://lower:case@h/db")

    assert Settings().database_url == "postgresql+psycopg://lower:case@h/db"


def test_str_env_is_coerced_to_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Path fields must come back as Path, not str — auth.py calls .exists() on them."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HEALTHEX_TOKEN_FILE", "/secrets/token.json")

    token_file = Settings().healthex_token_file
    assert isinstance(token_file, Path)
    assert token_file == Path("/secrets/token.json")


def test_dotenv_file_is_loaded(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    (tmp_path / ".env").write_text("DATABASE_URL=postgresql+psycopg://from:dotenv@h/db\n")
    monkeypatch.chdir(tmp_path)

    assert Settings().database_url == "postgresql+psycopg://from:dotenv@h/db"


def test_real_env_wins_over_dotenv(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("DATABASE_URL=postgresql+psycopg://from:dotenv@h/db\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://from:env@h/db")

    assert Settings().database_url == "postgresql+psycopg://from:env@h/db"
