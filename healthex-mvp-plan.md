# healthex — MVP Implementation Plan

> Open-source Python CLI that exports Google Health (Fitbit / Pixel Watch) sleep data to PostgreSQL.
> **MVP goal:** authenticate, pull nightly sleep data, and upsert it into Postgres idempotently.

---

## 0. Read this first — the API reality (mid-2026)

| Option | Verdict for healthex |
|---|---|
| **Google Fit REST API** | ❌ Dead. No new developer sign-ups since 2024-05-01; fully deprecated end of 2026. |
| **Health Connect** | ❌ On-device Android datastore only. No cloud REST API. Wrong tool for a server-side CLI. |
| **Fitbit Web API (legacy)** | ⚠️ Works today but the legacy Web API is being turned down ~September 2026. Don't build new on it. |
| **Google Health API** (`health.googleapis.com/v4`) | ✅ **Use this.** Official successor to the Fitbit Web API. REST + OAuth2, registered via Google Cloud Console, first-class `sleep` data type. |

**The "sleep score" gotcha:** the 0–100 Sleep Score shown in the app is an analysis/Premium feature, *not* raw exported data. The API's `sleep` endpoint returns sleep **sessions, stages, and summary metrics** (durations, efficiency-type fields), but there is no documented composite score field. **Before writing code**, authorize the `sleep.readonly` scope in the [OAuth 2.0 Playground](https://developers.google.com/oauthplayground/) and hit the sleep endpoint against your own data to confirm the exact JSON shape. Design the schema so `sleep_score` is **nullable/derived**.

Reference docs to keep open:
- Setup & OAuth: https://developers.google.com/health/setup
- Scopes: https://developers.google.com/health/scopes
- Endpoints (filters, pagination): https://developers.google.com/health/endpoints
- Data types index: https://developers.google.com/health/data-types
- Migrate-from-Fitbit guide (schema diffs): https://developers.google.com/health/migration

---

## 1. Tech stack

| Concern | Choice | Why |
|---|---|---|
| Python | 3.12+ | Modern typing, `tomllib`. |
| Project/dep manager | **uv** | Fast, lockfile, one tool for venv + deps + build + publish. |
| CLI framework | **Typer** | Type-hint driven, ergonomic, good `--help`. |
| HTTP | **httpx** | Sync+async, timeouts, retries-friendly. |
| OAuth | **google-auth** + **google-auth-oauthlib** | Handles the installed-app loopback flow + token refresh for you. |
| DB driver | **psycopg[binary]** (psycopg 3) | Modern, fast, good Postgres support. |
| ORM / schema | **SQLAlchemy 2.0** + **Alembic** | Typed models + migrations. (Lighter alt: raw SQL + a `schema.sql`.) |
| Config | **pydantic-settings** | `.env` + env-var config with validation. |
| Lint/format | **Ruff** | Lint + format in one. |
| Types | **mypy** | Static checks in pre-commit + CI. |
| Secrets scan | **gitleaks** | You're handling health data + OAuth secrets — scan every commit. |
| Tests | **pytest**, **respx** (mock httpx), **pytest-cov** | Unit + API mocking. |
| Local DB | **docker-compose** Postgres | Reproducible dev DB. |
| Build backend | **hatchling** | Standard, works cleanly with uv. |
| License | **Apache-2.0** or **MIT** | Pick one; Apache-2.0 gives explicit patent grant. |

---

## 2. Project structure

```
healthex/
├── pyproject.toml
├── uv.lock
├── README.md
├── LICENSE
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── .github/workflows/ci.yml
├── docker-compose.yml          # local Postgres
├── alembic.ini
├── migrations/
│   ├── env.py
│   └── versions/
├── src/
│   └── healthex/
│       ├── __init__.py
│       ├── __main__.py          # python -m healthex
│       ├── cli.py               # Typer app + commands
│       ├── config.py            # pydantic-settings
│       ├── auth.py              # OAuth flow + token cache
│       ├── client.py            # Google Health API httpx client
│       ├── sleep.py             # fetch + parse sleep dataPoints
│       ├── models.py            # SQLAlchemy ORM
│       ├── db.py                # engine/session
│       └── repository.py        # upsert into Postgres
└── tests/
    ├── conftest.py
    ├── test_auth.py
    ├── test_sleep.py
    └── test_repository.py
```

`.gitignore` must include: `client_secret.json`, `token.json`, `.env`, `.venv/`, `__pycache__/`, `*.egg-info/`.

---

## 3. Getting the API keys — full walkthrough (mandatory)

You need **two** credential sets: Google OAuth (to read sleep) and a Postgres connection string. There is no simple "API key" — Google Health uses OAuth2, so you generate an OAuth **client ID + secret** and exchange a user consent for access/refresh tokens.

### 3a. Prerequisites
1. A Google account that actually **has sleep data** synced (Fitbit device or Pixel Watch + the Fitbit app installed and synced). No data = empty responses.
2. Confirm sleep exists: open the Fitbit / Google Health app and verify recent sleep sessions.

### 3b. Create the Google Cloud project
1. Go to https://console.cloud.google.com → project picker → **New Project** → name it `healthex` → **Create** → select it.

### 3c. Enable the Google Health API
2. **APIs & Services → Library** → search **"Google Health API"** → **Enable**.

### 3d. Configure the OAuth consent screen
3. **APIs & Services → OAuth consent screen** (a.k.a. Google Auth Platform). If prompted, click **Get Started**.
4. **User type: External**. Fill app name, your support email, developer email.
5. **Add scope:** `https://www.googleapis.com/auth/googlehealth.sleep.readonly`. It's flagged **Restricted** — you'll see a warning; that's expected.
6. **Add yourself as a Test user** (your Google email).
7. **Keep Publishing status = Testing.** This is correct for a personal CLI.
   - ⚠️ **Known limitation:** with restricted scopes in Testing mode, **refresh tokens expire after ~7 days**, so you'll re-auth roughly weekly. Removing this requires publishing the app, which triggers a Google security assessment (expensive, not worth it for personal use). Plan for weekly `healthex auth login`.

### 3e. Create the OAuth client ID
8. **APIs & Services → Credentials → Create Credentials → OAuth client ID**.
9. **Application type: Desktop app** (simplest for a CLI — `google-auth-oauthlib` will run a loopback server automatically). Name it `healthex-cli`.
10. **Download JSON** → save as `client_secret.json` in the project root (already gitignored).

### 3f. First-run authorization
11. Run `healthex auth login`. It opens a browser, you select your account, you'll see "Google hasn't verified this app" + the restricted-scope warning → because you're a test user, **continue**. The loopback redirect captures the code, exchanges it for access + refresh tokens, and caches them to `token.json` (chmod 600).

### 3g. Optional 15-minute pre-flight (do this before coding)
- Open https://developers.google.com/oauthplayground/, gear icon → "Use your own OAuth credentials" → paste client ID/secret → select the Health API `sleep.readonly` scope → authorize → call:
  ```
  GET https://health.googleapis.com/v4/users/me/dataTypes/sleep/dataPoints?pageSize=5
  ```
- Inspect the JSON. **This is how you confirm whether a score field exists and what the summary fields are actually called**, so your `models.py` matches reality.

### 3h. Postgres "keys"
- Local dev: `docker compose up -d` (see §6) gives you `postgresql://healthex:healthex@localhost:5432/healthex`.
- Put both sets of secrets in `.env` (copy from `.env.example`):
  ```
  GOOGLE_CLIENT_SECRET_FILE=client_secret.json
  HEALTHEX_TOKEN_FILE=token.json
  DATABASE_URL=postgresql+psycopg://healthex:healthex@localhost:5432/healthex
  ```

---

## 4. The sleep endpoint

```
GET https://health.googleapis.com/v4/users/me/dataTypes/sleep/dataPoints
    ?filter=sleep.interval.civil_start_time >= "2026-06-01T00:00:00"
    &pageSize=50
Authorization: Bearer <access_token>
Accept: application/json
```

Notes:
- Endpoint data-type name is **kebab-case** (`sleep`); filter field is **snake_case** (`sleep.interval.civil_start_time`).
- Paginate with `pageToken` until it's absent.
- To dedupe across multiple devices, use the `:reconcile` variant with `dataSourceFamily=users/me/dataSourceFamilies/google-wearables`.
- Use `civil_*` time filters so day boundaries follow the user's local time, not UTC.

---

## 5. Database schema (MVP)

Keep the **raw payload in `jsonb`** so you never have to re-fetch when you add fields later. Promote only the columns you query on.

```sql
CREATE TABLE sleep_sessions (
    id              TEXT PRIMARY KEY,          -- stable hash of (user_id, start_time) or the dataPoint name
    user_id         TEXT        NOT NULL,
    civil_date      DATE        NOT NULL,      -- the night this main sleep belongs to
    start_time      TIMESTAMPTZ NOT NULL,
    end_time        TIMESTAMPTZ NOT NULL,
    sleep_type      TEXT,                       -- 'classic' | 'stages'
    duration_seconds      INTEGER,
    minutes_asleep        INTEGER,
    minutes_awake         INTEGER,
    minutes_light         INTEGER,
    minutes_deep          INTEGER,
    minutes_rem           INTEGER,
    efficiency            NUMERIC(5,2),
    sleep_score           INTEGER,              -- nullable / derived; likely NOT in the API
    source_platform       TEXT,                 -- e.g. 'FITBIT'
    raw                   JSONB       NOT NULL,
    ingested_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, start_time)
);

CREATE INDEX idx_sleep_user_date ON sleep_sessions (user_id, civil_date);
```

Idempotent upsert:
```sql
INSERT INTO sleep_sessions (...) VALUES (...)
ON CONFLICT (user_id, start_time) DO UPDATE
SET raw = EXCLUDED.raw,
    sleep_score = EXCLUDED.sleep_score,
    efficiency = EXCLUDED.efficiency,
    ingested_at = now();
```

---

## 6. Config files

### pyproject.toml
```toml
[project]
name = "healthex"
version = "0.1.0"
description = "Export Google Health sleep data to PostgreSQL."
readme = "README.md"
requires-python = ">=3.12"
license = "Apache-2.0"
dependencies = [
    "typer>=0.12",
    "httpx>=0.27",
    "google-auth>=2.30",
    "google-auth-oauthlib>=1.2",
    "sqlalchemy>=2.0",
    "psycopg[binary]>=3.2",
    "alembic>=1.13",
    "pydantic-settings>=2.3",
]

[project.scripts]
healthex = "healthex.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/healthex"]

[dependency-groups]   # uv dev deps
dev = [
    "ruff>=0.6",
    "mypy>=1.11",
    "pytest>=8.3",
    "pytest-cov>=5.0",
    "respx>=0.21",
]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]

[tool.mypy]
python_version = "3.12"
strict = true
ignore_missing_imports = true
```

### .pre-commit-config.yaml
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.11.2
    hooks:
      - id: mypy
        additional_dependencies: [pydantic, types-requests]
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.4
    hooks:
      - id: gitleaks
  - repo: https://github.com/astral-sh/uv-pre-commit
    rev: 0.4.20
    hooks:
      - id: uv-lock          # keep uv.lock in sync with pyproject
```

### docker-compose.yml
```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: healthex
      POSTGRES_PASSWORD: healthex
      POSTGRES_DB: healthex
    ports: ["5432:5432"]
    volumes: ["pgdata:/var/lib/postgresql/data"]
volumes:
  pgdata:
```

### .github/workflows/ci.yml
```yaml
name: ci
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: healthex
          POSTGRES_PASSWORD: healthex
          POSTGRES_DB: healthex
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready --health-interval 10s
          --health-timeout 5s --health-retries 5
    env:
      DATABASE_URL: postgresql+psycopg://healthex:healthex@localhost:5432/healthex
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --all-extras --dev
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run mypy src
      - run: uv run pytest --cov=healthex
```

---

## 7. Code skeletons

### auth.py
```python
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/googlehealth.sleep.readonly"]

def get_credentials(client_secret_file: Path, token_file: Path) -> Credentials:
    creds: Credentials | None = None
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_file), SCOPES)
            creds = flow.run_local_server(port=0)  # loopback redirect
        token_file.write_text(creds.to_json())
        token_file.chmod(0o600)
    return creds
```

### client.py
```python
import httpx

BASE = "https://health.googleapis.com/v4"

class HealthClient:
    def __init__(self, access_token: str) -> None:
        self._c = httpx.Client(
            base_url=BASE,
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
            timeout=30.0,
        )

    def list_sleep(self, since_iso: str) -> list[dict]:
        points: list[dict] = []
        params = {
            "filter": f'sleep.interval.civil_start_time >= "{since_iso}"',
            "pageSize": "50",
        }
        while True:
            r = self._c.get("/users/me/dataTypes/sleep/dataPoints", params=params)
            r.raise_for_status()
            body = r.json()
            points.extend(body.get("dataPoints", []))
            token = body.get("nextPageToken")
            if not token:
                return points
            params["pageToken"] = token
```

### cli.py
```python
import typer
from healthex.config import settings
from healthex import auth, client, sleep, repository

app = typer.Typer(help="Export Google Health sleep data to PostgreSQL.")
auth_app = typer.Typer()
app.add_typer(auth_app, name="auth")

@auth_app.command("login")
def auth_login() -> None:
    auth.get_credentials(settings.client_secret_file, settings.token_file)
    typer.echo("Authenticated. Token cached.")

@app.command("sync")
def sync(since: str = typer.Option(..., help='e.g. "2026-06-01T00:00:00"')) -> None:
    creds = auth.get_credentials(settings.client_secret_file, settings.token_file)
    raw = client.HealthClient(creds.token).list_sleep(since)
    rows = [sleep.parse_session(p) for p in raw]
    n = repository.upsert_sleep(settings.database_url, rows)
    typer.echo(f"Upserted {n} sleep sessions.")
```

`sleep.parse_session` and `repository.upsert_sleep` are where you map the **real** JSON shape (confirmed in §3g) into the schema and run the `ON CONFLICT` upsert.

---

## 8. Build order (phased)

| Phase | Outcome |
|---|---|
| **0. Verify** | OAuth Playground call confirms sleep JSON shape & what "score" really means. Lock the schema. |
| **1. Scaffold** | `uv init`, structure, `pyproject.toml`, pre-commit installed, CI green on an empty test, `docker compose up` Postgres. |
| **2. Auth** | `healthex auth login` caches a token end-to-end. |
| **3. Fetch** | `client.list_sleep` returns parsed dataPoints with pagination. |
| **4. Persist** | Alembic migration creates `sleep_sessions`; `upsert_sleep` is idempotent (re-run = no dupes). |
| **5. Wire CLI** | `healthex sync --since ...` does the full fetch→parse→upsert path. |
| **6. Test** | respx-mocked API tests + a Postgres-backed repository test; CI fully green. |
| **7. Ship** | README (incl. the §3 key walkthrough), LICENSE, push to GitHub. Optional: `uv build` + `uv publish` to PyPI. |

---

## 9. Post-MVP backlog
- Incremental sync (store last successful `civil_date`, fetch only newer).
- More data types (steps, HRV, resting HR) — same client, new parsers/tables.
- Webhook subscriptions instead of polling (the Health API supports push notifications for `sleep`).
- A derived sleep-score model if the API truly doesn't expose one.
- `--format json|csv` export command for downstream tools.
