"""Typer CLI — healthex commands."""

import typer

from healthex import auth, client, repository
from healthex import sleep as sleep_mod
from healthex import steps as steps_mod
from healthex.config import settings

app = typer.Typer(help="Export Google Health sleep data to PostgreSQL.")
auth_app = typer.Typer(help="OAuth authentication commands.")
app.add_typer(auth_app, name="auth")


@auth_app.command("login")
def auth_login() -> None:
    """Authenticate with Google and cache tokens to disk."""
    auth.get_credentials(settings.google_client_secret_file, settings.healthex_token_file)
    typer.echo("Authenticated. Token cached.")


@app.command("sync")
def sync(
    since: str = typer.Option(..., help='ISO-8601 local start time, e.g. "2026-06-01T00:00:00"'),
    user_id: str = typer.Option("me", help="User identifier stored in the DB (default: me)."),
) -> None:
    """Fetch sleep data from Google Health and upsert it into PostgreSQL."""
    creds = auth.get_credentials(settings.google_client_secret_file, settings.healthex_token_file)
    with client.HealthClient(str(creds.token)) as hc:
        raw_points = hc.list_sleep(since)

    typer.echo(f"Fetched {len(raw_points)} sleep dataPoints.")
    rows = [sleep_mod.parse_session(p, user_id=user_id) for p in raw_points]
    n = repository.upsert_sleep(settings.database_url, rows)
    typer.echo(f"Upserted {n} sleep sessions.")

    try:
        step_points = hc.list_steps(since)
        typer.echo(f"Fetched {len(step_points)} steps dataPoints.")
        step_rows = [steps_mod.parse_day(p, user_id=user_id) for p in step_points]
        ns = repository.upsert_steps(settings.database_url, step_rows)
        typer.echo(f"Upserted {ns} step days.")
    except Exception as e:  # noqa: BLE001
        typer.echo(f"Steps sync skipped: {e}", err=True)


@app.command("db-migrate")
def db_migrate() -> None:
    """Run Alembic migrations against DATABASE_URL (shortcut for `alembic upgrade head`)."""
    import subprocess  # noqa: PLC0415
    import sys  # noqa: PLC0415

    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        check=False,
        capture_output=False,
    )
    sys.exit(result.returncode)
