# Contributing

## Local setup

```bash
git clone https://github.com/yetmike/healthex
cd healthex
uv sync --dev
uv run pre-commit install
```

Start a local Postgres:

```bash
docker compose up -d
```

Copy and configure `.env`:

```bash
cp .env.example .env
# DATABASE_URL is already set for docker-compose
# add your GOOGLE_CLIENT_SECRET_FILE path
```

## Running tests

```bash
uv run pytest
```

The test suite uses a real Postgres connection (docker-compose). Integration tests in
`tests/test_repository.py` require `DATABASE_URL` to point to a running instance.

## Lint and type check

```bash
uv run ruff check .
uv run ruff format .
uv run mypy src
```

Pre-commit runs all of the above plus a secrets scan on every commit:

```bash
uv run pre-commit run --all-files
```

## Project structure

```
src/healthex/
  auth.py       - Google OAuth flow
  client.py     - Google Health REST API client
  sleep.py      - parse sleep dataPoints
  steps.py      - parse and aggregate steps dataPoints
  heart.py      - parse RHR and HRV dataPoints
  models.py     - SQLAlchemy ORM models
  repository.py - idempotent upserts
  db.py         - engine and session helpers
  cli.py        - Typer CLI entry point
  config.py     - pydantic-settings config
```

## Adding a new data type

1. Add a parser in `src/healthex/<type>.py` following the shape of `heart.py`.
2. Add the ORM model to `models.py`.
3. Add an upsert function to `repository.py`.
4. Wire it into `cli.py` `sync` command.
5. Run `healthex db-init` to create the new table (uses `create_all`, idempotent).

## Pull requests

- Keep PRs focused on one thing.
- All pre-commit checks must pass.
- Add or update tests for new behaviour.
