from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    google_client_secret_file: Path = Path("client_secret.json")
    healthex_token_file: Path = Path("token.json")
    database_url: str = "postgresql+psycopg://healthex:healthex@localhost:5432/healthex"


settings = Settings()
