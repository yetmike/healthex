"""Typer CLI — healthex commands."""

import datetime as dt

import typer

from healthex import auth, client, heart, repository
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
    since: str | None = typer.Option(
        None, help='ISO-8601 local start time, e.g. "2026-06-01T00:00:00"'
    ),  # noqa: E501
    days: int | None = typer.Option(
        None, help="Sync the last N days (computes --since automatically)."
    ),  # noqa: E501
    user_id: str = typer.Option("me", help="User identifier stored in the DB (default: me)."),
) -> None:
    """Fetch sleep, steps, RHR and HRV from Google Health and upsert into PostgreSQL."""
    if since is not None and days is not None:
        raise typer.BadParameter("Pass either --since or --days, not both.")
    if days is not None:
        since = (dt.datetime.now() - dt.timedelta(days=days)).strftime("%Y-%m-%dT00:00:00")
    if since is None:
        raise typer.BadParameter("Provide --since or --days.")
    creds = auth.get_credentials(settings.google_client_secret_file, settings.healthex_token_file)
    with client.HealthClient(str(creds.token)) as hc:
        raw_points = hc.list_sleep(since)
        try:
            step_points = hc.list_steps(since)
        except Exception as e:  # noqa: BLE001
            typer.echo(f"Steps fetch skipped: {e}", err=True)
            step_points = []
        try:
            rhr_points = hc.list_daily("daily-resting-heart-rate")
        except Exception as e:  # noqa: BLE001
            typer.echo(f"RHR fetch skipped: {e}", err=True)
            rhr_points = []
        try:
            hrv_points = hc.list_daily("daily-heart-rate-variability")
        except Exception as e:  # noqa: BLE001
            typer.echo(f"HRV fetch skipped: {e}", err=True)
            hrv_points = []

    typer.echo(f"Fetched {len(raw_points)} sleep dataPoints.")
    rows = [sleep_mod.parse_session(p, user_id=user_id) for p in raw_points]
    n = repository.upsert_sleep(settings.database_url, rows)
    typer.echo(f"Upserted {n} sleep sessions.")

    if step_points:
        typer.echo(f"Fetched {len(step_points)} steps dataPoints.")
        step_rows = steps_mod.aggregate_days(step_points, user_id=user_id)
        ns = repository.upsert_steps(settings.database_url, step_rows)
        typer.echo(f"Upserted {ns} step days.")
    else:
        typer.echo("No steps data returned from API.")

    if rhr_points:
        typer.echo(f"Fetched {len(rhr_points)} RHR dataPoints.")
        rhr_rows = [r for p in rhr_points if (r := heart.parse_rhr(p, user_id=user_id)) is not None]
        nr = repository.upsert_rhr(settings.database_url, rhr_rows)
        typer.echo(f"Upserted {nr} RHR days.")
    else:
        typer.echo("No RHR data returned from API.")

    if hrv_points:
        typer.echo(f"Fetched {len(hrv_points)} HRV dataPoints.")
        hrv_rows = [r for p in hrv_points if (r := heart.parse_hrv(p, user_id=user_id)) is not None]
        nh = repository.upsert_hrv(settings.database_url, hrv_rows)
        typer.echo(f"Upserted {nh} HRV days.")
    else:
        typer.echo("No HRV data returned from API.")


@app.command("db-init")
def db_init() -> None:
    """Create all tables in DATABASE_URL (idempotent, safe to re-run)."""
    from healthex.db import make_engine  # noqa: PLC0415
    from healthex.models import Base  # noqa: PLC0415

    Base.metadata.create_all(make_engine(settings.database_url))
    typer.echo("Database tables created.")
