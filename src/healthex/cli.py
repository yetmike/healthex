"""Typer CLI — healthex commands."""

import datetime as dt
from collections.abc import Callable

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

    failed: list[str] = []

    def fetch(
        label: str, call: Callable[[], list[dict[str, object]]]
    ) -> list[dict[str, object]] | None:
        """Return the dataPoints, or None if the fetch failed.

        None and [] mean different things: a failure the scheduler must hear
        about, versus a day the API genuinely had nothing for.
        """
        try:
            return call()
        except Exception as e:  # noqa: BLE001
            typer.echo(f"{label} fetch FAILED: {e}", err=True)
            failed.append(label)
            return None

    with client.HealthClient(str(creds.token)) as hc:
        sleep_points = fetch("sleep", lambda: hc.list_sleep(since))
        step_points = fetch("steps", lambda: hc.list_steps(since))
        rhr_points = fetch("rhr", lambda: hc.list_daily("daily-resting-heart-rate"))
        hrv_points = fetch("hrv", lambda: hc.list_daily("daily-heart-rate-variability"))

    stored = dict.fromkeys(("sleep", "steps", "rhr", "hrv"), 0)

    if sleep_points:
        rows = [sleep_mod.parse_session(p, user_id=user_id) for p in sleep_points]
        stored["sleep"] = repository.upsert_sleep(settings.database_url, rows)
    elif sleep_points is not None:
        typer.echo("No sleep data returned from API.")

    if step_points:
        step_rows = steps_mod.aggregate_days(step_points, user_id=user_id)
        stored["steps"] = repository.upsert_steps(settings.database_url, step_rows)
    elif step_points is not None:
        typer.echo("No steps data returned from API.")

    if rhr_points:
        rhr_rows = [r for p in rhr_points if (r := heart.parse_rhr(p, user_id=user_id)) is not None]
        stored["rhr"] = repository.upsert_rhr(settings.database_url, rhr_rows)
    elif rhr_points is not None:
        typer.echo("No RHR data returned from API.")

    if hrv_points:
        hrv_rows = [r for p in hrv_points if (r := heart.parse_hrv(p, user_id=user_id)) is not None]
        stored["hrv"] = repository.upsert_hrv(settings.database_url, hrv_rows)
    elif hrv_points is not None:
        typer.echo("No HRV data returned from API.")

    counts = " ".join(f"{k}={v}" for k, v in stored.items())
    status = "complete" if not failed else f"PARTIAL (failed: {', '.join(failed)})"
    typer.echo(f"sync {status}: {counts}")

    # Non-zero so a scheduler notices. Whatever succeeded is still committed.
    if failed:
        raise typer.Exit(1)


@app.command("db-init")
def db_init() -> None:
    """Apply pending schema migrations to DATABASE_URL (idempotent)."""
    from healthex import migrate  # noqa: PLC0415

    applied = migrate.apply(settings.database_url)
    if applied:
        for name in applied:
            typer.echo(f"Applied {name}")
    else:
        typer.echo("Schema already up to date.")
