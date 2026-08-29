# Example Grafana dashboard

`grafana-dashboard.json` is a starting point, not a supported artefact. Import it, then edit it —
it is expected to diverge from whatever you end up running.

## Import

Grafana → Dashboards → New → Import → upload `grafana-dashboard.json`. You will be prompted for the
PostgreSQL datasource pointing at the database healthex syncs into.

## Variables

| Variable | Purpose |
|---|---|
| `user_id` | Which `user_id` to chart, populated from `sleep_sessions`. Matches `healthex sync --user-id`. |
| `tz` | IANA zone used to bucket bedtime and wake time (default `Europe/Berlin`). |

Panel time is rendered in the browser's timezone; `tz` only affects the two SQL-computed
bedtime/wake-time panels, because those bucket by local wall-clock hour.

## What it reads

Plain SQL over the healthex schema — `sleep_sessions`, `daily_steps`, `daily_rhr`, `daily_hrv`. Two
notes on derived values:

- **Sleep score** is healthex's own 0–100 proxy, not Fitbit's. Fitbit's uses heart rate and SpO2 that
  the API does not expose.
- **Time to fall asleep** reads `sleep_latency_minutes`, derived at ingest from the sleep stage
  timeline. The API's `summary.minutesToFallAsleep` is unreliable — it reports `0` for every session
  on some devices — so healthex does not use it when stages are available.

## Caveat

The panels assume the schema of the healthex release you are running. If a panel is empty after
import, check that `healthex db-init` has applied all migrations.
