"""Apply numbered SQL migrations, once each, in order.

Deliberately not Alembic: one database, one maintainer, four tables. What is
irreducible is (1) ordered scripts, (2) a record of which ones a database has
already run, (3) something that applies the rest. That is all this is.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Connection, text

from healthex.db import make_engine

# Inside the package so the .sql files ship with the wheel and the image.
MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"

_VERSION_TABLE = """
CREATE TABLE IF NOT EXISTS schema_version (
    filename    TEXT PRIMARY KEY,
    applied_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
)
"""


_BASELINE = "001_init.sql"


def pending(database_url: str, migrations_dir: Path | None = None) -> list[Path]:
    """Migration files this database has not run yet, in filename order."""
    directory = migrations_dir or MIGRATIONS_DIR
    engine = make_engine(database_url)
    with engine.begin() as conn:
        conn.execute(text(_VERSION_TABLE))
        done = {r[0] for r in conn.execute(text("SELECT filename FROM schema_version"))}

        # Adopt a database created by the old `create_all` path: its tables
        # already match the baseline, so record it as applied rather than
        # re-running CREATE TABLE and failing.
        if not done and _has_existing_schema(conn):
            conn.execute(
                text("INSERT INTO schema_version (filename) VALUES (:f)"), {"f": _BASELINE}
            )
            done = {_BASELINE}

    return [p for p in sorted(directory.glob("*.sql")) if p.name not in done]


def _has_existing_schema(conn: Connection) -> bool:
    return bool(conn.execute(text("SELECT to_regclass('public.sleep_sessions')")).scalar())


def apply(database_url: str, migrations_dir: Path | None = None) -> list[str]:
    """Apply every pending migration. Returns the filenames applied."""
    applied: list[str] = []
    engine = make_engine(database_url)
    for path in pending(database_url, migrations_dir):
        # One transaction per migration: Postgres has transactional DDL, so a
        # failing script leaves neither a half-applied schema nor a version row.
        with engine.begin() as conn:
            conn.execute(text(path.read_text()))
            conn.execute(
                text("INSERT INTO schema_version (filename) VALUES (:f)"), {"f": path.name}
            )
        applied.append(path.name)
    return applied
