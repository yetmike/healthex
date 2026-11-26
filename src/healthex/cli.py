"""Typer CLI — healthex commands."""

import datetime as dt
from collections.abc import Callable

import typer

from healthex import auth, client, heart, metrics, migrate, models, repository
from healthex import sleep as sleep_mod
from healthex import steps as steps_mod
from healthex.config import settings

# Intraday heart rate resolution. 5 minutes is 288 rows a day: enough to see a
# workout or a stressful afternoon without storing every per-second sample.
_HR_BUCKET_SECONDS = 300

app = typer.Typer(help="Export Google Health sleep data to PostgreSQL.")
auth_app = typer.Typer(help="OAuth authentication commands.")
app.add_typer(auth_app, name="auth")


@auth_app.command("login")
def auth_login() -> None:
    """Authenticate with Google and cache tokens to disk."""
    auth.get_credentials(settings.google_client_secret_file, settings.healthex_token_file)
    typer.echo("Authenticated. Token cached.")


def _resolve_db_url(override: str | None) -> str:
    """--database-url beats DATABASE_URL beats .env; nothing means stop."""
    url = override or settings.database_url
    if not url:
        raise typer.BadParameter(
            "No database URL. Pass --database-url, set the DATABASE_URL environment "
            "variable, or put DATABASE_URL in a .env file in the current directory."
        )
    return url


@app.command("sync")
def sync(
    since: str | None = typer.Option(
        None, help='ISO-8601 local start time, e.g. "2026-06-01T00:00:00"'
    ),  # noqa: E501
    days: int | None = typer.Option(
        None, help="Sync the last N days (computes --since automatically)."
    ),  # noqa: E501
    user_id: str = typer.Option("me", help="User identifier stored in the DB (default: me)."),
    database_url: str | None = typer.Option(
        None, help="PostgreSQL DSN. Overrides DATABASE_URL and .env."
    ),
) -> None:
    """Fetch sleep, activity, heart, body and exercise data from Google Health into PostgreSQL."""
    if since is not None and days is not None:
        raise typer.BadParameter("Pass either --since or --days, not both.")
    if days is not None:
        since = (dt.datetime.now() - dt.timedelta(days=days)).strftime("%Y-%m-%dT00:00:00")
    if since is None:
        raise typer.BadParameter("Provide --since or --days.")
    db_url = _resolve_db_url(database_url)

    # Apply any pending migrations first: a fresh database has no tables, and an
    # upgraded healthex may add columns the upsert below writes to.
    from healthex import migrate  # noqa: PLC0415

    for name in migrate.apply(db_url):
        typer.echo(f"Applied {name}")
    # Bootstrap the schema so a fresh database needs no separate db-init.
    # apply() only runs pending migrations, so this is a no-op on a current DB.
    for name in migrate.apply(db_url):
        typer.echo(f"Applied {name}")
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
        rhr_points = fetch("rhr", lambda: hc.list_daily("daily-resting-heart-rate", since))
        hrv_points = fetch("hrv", lambda: hc.list_daily("daily-heart-rate-variability", since))

        start = dt.datetime.fromisoformat(since[:19]).astimezone()  # naive = local
        tomorrow = dt.date.today() + dt.timedelta(days=1)
        metric_points: list[dict[str, object]] = []
        for dtype, chunk in metrics.DAILY_ROLLUPS.items():
            metric_points += (
                fetch(dtype, lambda: hc.daily_rollup(dtype, start.date(), tomorrow, chunk)) or []  # noqa: B023
            )
        for dtype in metrics.DAILY_LISTS:
            metric_points += fetch(dtype, lambda: hc.list_daily(dtype, since)) or []  # noqa: B023
        exercise_points = fetch("exercise", lambda: hc.list_exercises(since)) or []
        hr_points = (
            fetch(
                "heart-rate-intraday",
                lambda: hc.rollup("heart-rate", start, dt.datetime.now(dt.UTC), _HR_BUCKET_SECONDS),
            )
            or []
        )

    stored = dict.fromkeys(("sleep", "steps", "rhr", "hrv"), 0)
    stored["metrics"] = repository.upsert(
        db_url, models.DailyMetric, metrics.daily_rows(metric_points, user_id=user_id)
    )
    stored["exercises"] = repository.upsert(
        db_url, models.Exercise, metrics.exercise_rows(exercise_points, user_id=user_id)
    )
    stored["heart_rate"] = repository.upsert(
        db_url, models.HeartRate, metrics.heart_rate_rows(hr_points, user_id=user_id)
    )

    if sleep_points:
        rows = [sleep_mod.parse_session(p, user_id=user_id) for p in sleep_points]
        stored["sleep"] = repository.upsert_sleep(db_url, rows)
    elif sleep_points is not None:
        typer.echo("No sleep data returned from API.")

    if step_points:
        step_rows = steps_mod.aggregate_days(step_points, user_id=user_id)
        stored["steps"] = repository.upsert_steps(db_url, step_rows)
    elif step_points is not None:
        typer.echo("No steps data returned from API.")

    if rhr_points:
        rhr_rows = [r for p in rhr_points if (r := heart.parse_rhr(p, user_id=user_id)) is not None]
        stored["rhr"] = repository.upsert_rhr(db_url, rhr_rows)
    elif rhr_points is not None:
        typer.echo("No RHR data returned from API.")

    if hrv_points:
        hrv_rows = [r for p in hrv_points if (r := heart.parse_hrv(p, user_id=user_id)) is not None]
        stored["hrv"] = repository.upsert_hrv(db_url, hrv_rows)
    elif hrv_points is not None:
        typer.echo("No HRV data returned from API.")

    counts = " ".join(f"{k}={v}" for k, v in stored.items())
    status = "complete" if not failed else f"PARTIAL (failed: {', '.join(failed)})"
    typer.echo(f"sync {status}: {counts}")

    # Non-zero so a scheduler notices. Whatever succeeded is still committed.
    if failed:
        raise typer.Exit(1)


@app.command("db-init")
def db_init(
    database_url: str | None = typer.Option(
        None, help="PostgreSQL DSN. Overrides DATABASE_URL and .env."
    ),
) -> None:
    """Apply pending schema migrations to the target database (idempotent)."""
    applied = migrate.apply(_resolve_db_url(database_url))
    if applied:
        for name in applied:
            typer.echo(f"Applied {name}")
    else:
        typer.echo("Schema already up to date.")
