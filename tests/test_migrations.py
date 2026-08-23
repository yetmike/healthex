"""Migrations must produce exactly the schema healthex.models describes.

Without this, migrations/ and models.py are two sources of truth that drift
silently — add a column to the model, forget the migration, and the mismatch
only surfaces at runtime.
"""

from typing import Any

import pytest
from sqlalchemy import Engine, create_engine, inspect, text

from healthex import migrate
from healthex.db import make_engine
from healthex.models import Base


def _describe(engine: Engine) -> dict[str, Any]:
    """Column names/types/defaults, uniques and indexes, per table."""
    insp = inspect(engine)
    out: dict[str, Any] = {}
    for table in sorted(Base.metadata.tables):
        out[table] = {
            "columns": {
                c["name"]: (str(c["type"]), bool(c["nullable"]), str(c.get("default")))
                for c in insp.get_columns(table)
            },
            "unique": sorted(
                tuple(sorted(u["column_names"])) for u in insp.get_unique_constraints(table)
            ),
            "indexes": sorted(
                tuple(sorted(c or "" for c in i["column_names"])) for i in insp.get_indexes(table)
            ),
        }
    return out


@pytest.fixture()
def two_databases(db_url: str) -> Any:
    """A pair of scratch databases, dropped afterwards."""
    admin = create_engine(db_url, isolation_level="AUTOCOMMIT")
    names = ("drift_migrated", "drift_models")
    with admin.connect() as conn:
        for n in names:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{n}"'))
            conn.execute(text(f'CREATE DATABASE "{n}"'))
    urls = tuple(db_url.rsplit("/", 1)[0] + f"/{n}" for n in names)
    yield urls

    # make_engine is lru_cached, so its pools outlive the test and would block
    # DROP DATABASE. Dispose them, then evict any stragglers.
    for url in urls:
        make_engine(url).dispose()
    make_engine.cache_clear()
    with admin.connect() as conn:
        for n in names:
            conn.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity"
                    " WHERE datname = :n AND pid <> pg_backend_pid()"
                ),
                {"n": n},
            )
            conn.execute(text(f'DROP DATABASE IF EXISTS "{n}"'))
    admin.dispose()


def test_migrations_match_the_models(two_databases: tuple[str, str]) -> None:
    migrated_url, models_url = two_databases

    migrate.apply(migrated_url)

    models_engine = create_engine(models_url)
    Base.metadata.create_all(models_engine)

    assert _describe(create_engine(migrated_url)) == _describe(models_engine)


def test_migrations_are_idempotent(two_databases: tuple[str, str]) -> None:
    migrated_url, _ = two_databases

    first = migrate.apply(migrated_url)
    second = migrate.apply(migrated_url)

    assert first  # something ran
    assert second == []  # nothing ran twice


def test_existing_create_all_database_is_adopted(two_databases: tuple[str, str]) -> None:
    """A database built by the old create_all path must not re-run the baseline."""
    _, legacy_url = two_databases
    Base.metadata.create_all(create_engine(legacy_url))

    applied = migrate.apply(legacy_url)

    assert "001_init.sql" not in applied  # adopted, not re-created
    assert "002_fix_ingested_at_default.sql" in applied


def test_ingested_at_defaults_to_insert_time(two_databases: tuple[str, str]) -> None:
    """Regression: server_default="now()" froze the default at CREATE TABLE time."""
    migrated_url, _ = two_databases
    migrate.apply(migrated_url)

    engine = create_engine(migrated_url)
    with engine.begin() as conn:
        row = conn.execute(
            text(
                "INSERT INTO daily_steps (id,user_id,step_date,steps,raw)"
                " VALUES ('x','u','2026-06-27',1,'{}')"
                " RETURNING ingested_at, now() AS actual_now"
            )
        ).one()
    assert abs((row.ingested_at - row.actual_now).total_seconds()) < 5
