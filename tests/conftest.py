"""Shared pytest fixtures."""

import os
from collections.abc import Generator

import pytest
from sqlalchemy import Engine, create_engine, text

from healthex.models import Base

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://healthex:healthex@localhost:5432/healthex"
)


@pytest.fixture(scope="session")
def db_engine() -> Generator[Engine, None, None]:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def clean_db(db_engine: Engine) -> Generator[None, None, None]:
    yield
    with db_engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE sleep_sessions"))
        conn.commit()
