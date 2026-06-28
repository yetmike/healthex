# healthex

Python CLI that syncs Google Health data (sleep, steps, RHR, HRV) from Fitbit or Pixel Watch devices to PostgreSQL.

Designed to feed a Grafana dashboard but works with any SQL tool.

## Features

- Sleep sessions with stage breakdown (light / deep / REM / awake)
- Daily step counts
- Resting Heart Rate (RHR) — calculated from sleep via Fitbit
- Heart Rate Variability (HRV) — RMSSD measured during sleep
- Idempotent upserts — safe to re-run, no duplicates
- Secrets scan and type checking in pre-commit hooks

## Requirements

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/)
- PostgreSQL 15+
- A Google account with health data synced from a Fitbit or Pixel Watch device

## Quick start

```bash
# 1. Install
uv sync

# 2. Configure
cp .env.example .env
# edit .env: set DATABASE_URL for your Postgres instance

# 3. Set up Google API credentials (see below)

# 4. Authenticate
uv run healthex auth login

# 5. Create tables
uv run healthex db-init

# 6. Sync data
uv run healthex sync --since "2024-01-01T00:00:00"
```

## Google API credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com) and create a project.
2. Enable the **Google Health API**.
3. Create an OAuth consent screen — External, add your account as a Test user, add these scopes:
   - `https://www.googleapis.com/auth/googlehealth.sleep.readonly`
   - `https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly`
   - `https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly`
4. Create an **OAuth Client ID** (Desktop app), download `client_secret.json` to the project root.
5. Run `uv run healthex auth login` — opens a browser, you consent, token is cached to `token.json`.

> With restricted scopes in Testing mode, refresh tokens expire roughly weekly. Run `healthex auth login` again when that happens.

## Commands

| Command | Description |
|---|---|
| `healthex auth login` | OAuth flow - opens browser, caches token |
| `healthex db-init` | Create tables (idempotent) |
| `healthex sync --since ISO_DATE` | Fetch and upsert all data types |

## Local database (for development)

```bash
docker compose up -d
# DATABASE_URL=postgresql+psycopg://healthex:healthex@localhost:5432/healthex
```

## Development

```bash
uv sync --dev
uv run pre-commit install
uv run pytest
uv run ruff check .
uv run mypy src
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for more detail.

## License

[Apache-2.0](LICENSE)
