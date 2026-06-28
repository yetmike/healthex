"""Shared pytest fixtures."""

import os

import pytest
from sqlalchemy import create_engine, text

from healthex.models import Base

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://healthex:healthex@localhost:5432/healthex"
)


@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def clean_db(db_engine):
    """Truncate all tables between tests."""
    yield
    with db_engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE sleep_sessions"))
        conn.commit()
