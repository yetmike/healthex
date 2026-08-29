from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    google_client_secret_file: Path = Path("client_secret.json")
    healthex_token_file: Path = Path("token.json")
    # Deliberately no default. A plausible localhost URL fails silently: run
    # the tool outside a directory holding .env and it would quietly write to
    # whatever Postgres happened to be listening locally.
    database_url: str | None = None


settings = Settings()
