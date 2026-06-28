# healthex

Open-source Python CLI that exports Google Health (Fitbit / Pixel Watch) sleep data to PostgreSQL.

## Quick start

```bash
# 1. Install
uv sync

# 2. Configure (copy and fill in your values)
cp .env.example .env

# 3. Authenticate with Google
healthex auth login

# 4. Sync sleep data
healthex sync --since "2026-06-01T00:00:00"
```

## Setup

### Prerequisites
- Python 3.12+
- `uv` — install from https://docs.astral.sh/uv/
- A Google account with sleep data synced from a Fitbit or Pixel Watch device
- A PostgreSQL database (see below)

### Database options

**Local (fast, offline — for dev/testing):**
```bash
docker compose up -d
# DATABASE_URL=postgresql+psycopg://healthex:healthex@localhost:5432/healthex
```

**Homelab (persistent — for real data + Grafana visualization):**
```
DATABASE_URL=postgresql+psycopg://healthex:<pw>@pg.yetmike.com:5432/healthex
```
`pg.yetmike.com` resolves to the Traefik LoadBalancer IP via external-dns/pihole.
See the homelab repo for deployment instructions.

### Schema migration
```bash
uv run alembic upgrade head
# or use the CLI shortcut:
healthex db-migrate
```

### Getting Google API credentials

> See `healthex-mvp-plan.md` §3 for the full step-by-step walkthrough.

1. Create a Google Cloud project and enable the **Google Health API**.
2. Create an OAuth consent screen (External, add yourself as Test user, add scope
   `https://www.googleapis.com/auth/googlehealth.sleep.readonly`).
3. Create an OAuth Client ID (Desktop app), download `client_secret.json` to the project root.
4. Run `healthex auth login` — it opens a browser, you consent, tokens are cached to `token.json`.

> **Note:** With restricted scopes in Testing mode, refresh tokens expire ~weekly. Run
> `healthex auth login` again when that happens.

## Commands

| Command | Description |
|---|---|
| `healthex auth login` | OAuth flow — opens browser, caches tokens |
| `healthex sync --since ISO_DATE` | Fetch + upsert sleep data |
| `healthex db-migrate` | Run Alembic migrations |

## Development

```bash
uv sync --dev
uv run pytest
uv run ruff check .
uv run mypy src
```

Pre-commit hooks (lint, format, type-check, secrets scan):
```bash
uv run pre-commit install
```

## License

Apache-2.0
