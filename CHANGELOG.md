# CHANGELOG


## v0.1.1 (2026-08-23)

### Bug Fixes

- Silence mypy no-untyped-call for google-auth stubs across mypy versions
  ([`a414416`](https://github.com/yetmike/healthex/commit/a414416f2e99b1fd7a0d8d2c7bb019f3f2fe7bff))

google-auth has no type stubs for Credentials.from_authorized_user_file and Credentials.refresh —
  these trigger [no-untyped-call] in mypy 2.x but not 1.x. Add type: ignore comments and set
  warn_unused_ignores=false so both the pinned pre-commit version (1.11.2) and CI's latest mypy pass
  without errors.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Update test_repository fixture to match real API shape
  ([`f35a985`](https://github.com/yetmike/healthex/commit/f35a985c8a2148e4074beb4bc60f983bf31a6459))

SAMPLE_POINT used the old flat shape (point.interval, point.sleepType). The real Google Health API
  nests data under point.sleep.interval and point.sleep.summary — matching what parse_session
  actually reads. Stale fixture caused start_time/end_time to be empty strings, failing the DB
  insert in CI.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Chores

- **deps**: Bump cryptography from 49.0.0 to 50.0.0
  ([#5](https://github.com/yetmike/healthex/pull/5),
  [`b31a208`](https://github.com/yetmike/healthex/commit/b31a208a2184f8f8999b958fb5cb7ea0a9cab868))

Bumps [cryptography](https://github.com/pyca/cryptography) from 49.0.0 to 50.0.0. -
  [Changelog](https://github.com/pyca/cryptography/blob/main/CHANGELOG.rst) -
  [Commits](https://github.com/pyca/cryptography/compare/49.0.0...50.0.0)

--- updated-dependencies: - dependency-name: cryptography dependency-version: 50.0.0

dependency-type: indirect ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

- **deps**: Bump pyasn1 from 0.6.3 to 0.6.4 ([#4](https://github.com/yetmike/healthex/pull/4),
  [`fafcb98`](https://github.com/yetmike/healthex/commit/fafcb98f8b63581d45c163c085f44411fa668c25))

Bumps [pyasn1](https://github.com/pyasn1/pyasn1) from 0.6.3 to 0.6.4. - [Release
  notes](https://github.com/pyasn1/pyasn1/releases) -
  [Changelog](https://github.com/pyasn1/pyasn1/blob/main/CHANGES.rst) -
  [Commits](https://github.com/pyasn1/pyasn1/compare/v0.6.3...v0.6.4)

--- updated-dependencies: - dependency-name: pyasn1 dependency-version: 0.6.4

dependency-type: indirect ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

- **deps**: Bump python from 3.12-slim to 3.14-slim
  ([#1](https://github.com/yetmike/healthex/pull/1),
  [`ea86392`](https://github.com/yetmike/healthex/commit/ea86392628d80438b84ec9bff0ae0e14aab32950))

Bumps python from 3.12-slim to 3.14-slim.

--- updated-dependencies: - dependency-name: python dependency-version: 3.14-slim

dependency-type: direct:production ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

- **deps**: Bump the all group with 5 updates ([#2](https://github.com/yetmike/healthex/pull/2),
  [`5f1561a`](https://github.com/yetmike/healthex/commit/5f1561a0e35ba084566bea05704f1250be0baeef))

Bumps the all group with 5 updates:

| Package | From | To | | --- | --- | --- | |
  [actions/checkout](https://github.com/actions/checkout) | `4` | `7` | |
  [astral-sh/setup-uv](https://github.com/astral-sh/setup-uv) | `3` | `7` | |
  [docker/login-action](https://github.com/docker/login-action) | `3` | `4` | |
  [docker/metadata-action](https://github.com/docker/metadata-action) | `5` | `6` | |
  [docker/build-push-action](https://github.com/docker/build-push-action) | `6` | `7` |

Updates `actions/checkout` from 4 to 7 - [Release
  notes](https://github.com/actions/checkout/releases) -
  [Changelog](https://github.com/actions/checkout/blob/main/CHANGELOG.md) -
  [Commits](https://github.com/actions/checkout/compare/v4...v7)

Updates `astral-sh/setup-uv` from 3 to 7 - [Release
  notes](https://github.com/astral-sh/setup-uv/releases) -
  [Commits](https://github.com/astral-sh/setup-uv/compare/v3...v7)

Updates `docker/login-action` from 3 to 4 - [Release
  notes](https://github.com/docker/login-action/releases) -
  [Commits](https://github.com/docker/login-action/compare/v3...v4)

Updates `docker/metadata-action` from 5 to 6 - [Release
  notes](https://github.com/docker/metadata-action/releases) -
  [Commits](https://github.com/docker/metadata-action/compare/v5...v6)

Updates `docker/build-push-action` from 6 to 7 - [Release
  notes](https://github.com/docker/build-push-action/releases) -
  [Commits](https://github.com/docker/build-push-action/compare/v6...v7)

--- updated-dependencies: - dependency-name: actions/checkout dependency-version: '7'

dependency-type: direct:production

update-type: version-update:semver-major

dependency-group: all

- dependency-name: astral-sh/setup-uv dependency-version: '7'

- dependency-name: docker/login-action dependency-version: '4'

- dependency-name: docker/metadata-action dependency-version: '6'

- dependency-name: docker/build-push-action dependency-version: '7'

dependency-group: all ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

- **deps**: Bump the all group with 6 updates ([#3](https://github.com/yetmike/healthex/pull/3),
  [`3d44c3f`](https://github.com/yetmike/healthex/commit/3d44c3ff3c224c8c53c70eff617b5cff0dcc5025))

Bumps the all group with 6 updates:

| Package | From | To | | --- | --- | --- | | [typer](https://github.com/fastapi/typer) | `0.26.8` |
  `0.27.1` | | [google-auth](https://github.com/googleapis/google-cloud-python) | `2.55.1` |
  `2.56.3` | | [sqlalchemy](https://github.com/sqlalchemy/sqlalchemy) | `2.0.51` | `2.0.52` | |
  [pydantic-settings](https://github.com/pydantic/pydantic-settings) | `2.14.2` | `2.15.0` | |
  [ruff](https://github.com/astral-sh/ruff) | `0.15.20` | `0.16.3` | |
  [mypy](https://github.com/python/mypy) | `2.1.0` | `2.3.1` |

Updates `typer` from 0.26.8 to 0.27.1 - [Release notes](https://github.com/fastapi/typer/releases) -
  [Changelog](https://github.com/fastapi/typer/blob/master/docs/release-notes.md) -
  [Commits](https://github.com/fastapi/typer/compare/0.26.8...0.27.1)

Updates `google-auth` from 2.55.1 to 2.56.3 - [Release
  notes](https://github.com/googleapis/google-cloud-python/releases) -
  [Changelog](https://github.com/googleapis/google-cloud-python/blob/main/packages/google-cloud-documentai/CHANGELOG.md)
  -
  [Commits](https://github.com/googleapis/google-cloud-python/compare/google-auth-v2.55.1...google-auth-v2.56.3)

Updates `sqlalchemy` from 2.0.51 to 2.0.52 - [Release
  notes](https://github.com/sqlalchemy/sqlalchemy/releases) -
  [Changelog](https://github.com/sqlalchemy/sqlalchemy/blob/main/CHANGES.rst) -
  [Commits](https://github.com/sqlalchemy/sqlalchemy/commits)

Updates `pydantic-settings` from 2.14.2 to 2.15.0 - [Release
  notes](https://github.com/pydantic/pydantic-settings/releases) -
  [Commits](https://github.com/pydantic/pydantic-settings/compare/v2.14.2...v2.15.0)

Updates `ruff` from 0.15.20 to 0.16.3 - [Release notes](https://github.com/astral-sh/ruff/releases)
  - [Changelog](https://github.com/astral-sh/ruff/blob/main/CHANGELOG.md) -
  [Commits](https://github.com/astral-sh/ruff/compare/0.15.20...0.16.3)

Updates `mypy` from 2.1.0 to 2.3.1 -
  [Changelog](https://github.com/python/mypy/blob/master/CHANGELOG.md) -
  [Commits](https://github.com/python/mypy/compare/v2.1.0...v2.3.1)

--- updated-dependencies: - dependency-name: typer dependency-version: 0.27.1

dependency-type: direct:production

update-type: version-update:semver-minor

dependency-group: all

- dependency-name: google-auth dependency-version: 2.56.3

- dependency-name: sqlalchemy dependency-version: 2.0.52

update-type: version-update:semver-patch

- dependency-name: pydantic-settings dependency-version: 2.15.0

- dependency-name: ruff dependency-version: 0.16.3

dependency-type: direct:development

- dependency-name: mypy dependency-version: 2.3.1

dependency-group: all ...

Signed-off-by: dependabot[bot] <support@github.com>

Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>

### Continuous Integration

- Add dependabot with auto-merge on green tests
  ([`e3ca4c6`](https://github.com/yetmike/healthex/commit/e3ca4c6e1684695da3552a0b70b9701371f85f1c))

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>

Claude-Session: https://claude.ai/code/session_014wZzrDo7GnKNYGDHx21tui

- Automate releases with release-please ([#8](https://github.com/yetmike/healthex/pull/8),
  [`1a92b3e`](https://github.com/yetmike/healthex/commit/1a92b3ebbaa0a5198996b99d86af69823a4d0756))

Conventional commits on main maintain a release PR; merging it bumps pyproject.toml, writes
  CHANGELOG.md and pushes vX.Y.Z, which docker.yml turns into the semver image tags.

Uses a PAT rather than GITHUB_TOKEN so the release PR gets its required test check and the tag
  actually triggers the image build.

Co-authored-by: Mike <Mykhailo>

Co-authored-by: Claude Opus 5 (1M context) <noreply@anthropic.com>

- Replace release-please with python-semantic-release
  ([#10](https://github.com/yetmike/healthex/pull/10),
  [`6f5d0e1`](https://github.com/yetmike/healthex/commit/6f5d0e1b8f0a244cf6828b10da275d7c51f515fa))

pyproject.toml is now the single source of truth for the version; the git tag and image tag are both
  derived from it. Removes the release-please manifest, which duplicated the version in a second
  file.

Pins allow_zero_version/major_on_zero because the defaults resolve a plain fix: on 0.1.0 to 1.0.0
  rather than 0.1.1.

Co-authored-by: Mike <Mykhailo>

Co-authored-by: Claude Opus 5 (1M context) <noreply@anthropic.com>


## v0.1.0 (2026-06-29)

### Bug Fixes

- Add googlehealth.readonly scope for steps, fix steps fetch inside client context
  ([`16f5a10`](https://github.com/yetmike/healthex/commit/16f5a100fe216e147e8aee68e02011a9a6194f6c))

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

- Align parser and client with real Google Health API v4 shape
  ([`8b35e64`](https://github.com/yetmike/healthex/commit/8b35e64c3deca04fae45a9bc4bd4431d07293739))

- client: drop unsupported server-side filter; paginate all and filter client-side by
  sleep.interval.startTime - sleep: rewrite parse_session() for actual response shape — data nested
  under point.sleep, stage minutes are strings, civil_date computed from startTime + startUtcOffset,
  user_id extracted from resource name - repository: use RETURNING id to count upserted rows
  (psycopg3 rowcount returns -1 for INSERT ON CONFLICT) - tests: update sample fixture to match real
  API response

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

- Correct steps API shape and aggregate intervals per day
  ([`09d7f25`](https://github.com/yetmike/healthex/commit/09d7f250901ca418445faa319aef78ad5ee216a4))

Real API returns one dataPoint per short activity interval (not per day): - steps at
  point.steps.count (not summary.steps) - civil date from civilStartTime.date directly - ~158
  intervals/day, so aggregate_days() sums them per civil_date

Also bump pageSize to 1000 to reduce API round-trips.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

- Correct steps OAuth scope to googlehealth.activity_and_fitness.readonly
  ([`16c35ba`](https://github.com/yetmike/healthex/commit/16c35ba65335063b0daae1d82a673f3acc87a18e))

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

- Deduplicate steps sources per day to avoid double-counting
  ([`af17665`](https://github.com/yetmike/healthex/commit/af1766505f84ae128baa1e25d72441526ad7efe7))

The API returns overlapping dataPoints from multiple HealthKit sources (aggregate, iPhone, Watch).
  Without deduplication, steps were ~2x the actual count (e.g. 31399 vs 16499 for June 13).

Strategy: group by (civil_date, formFactor), then pick the best source: None (HealthKit aggregate) >
  WATCH > PHONE

Result matches Google Health app to within ~1%.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

- Rename DailySteps.date to step_date to avoid Python type name clash
  ([`597fd4b`](https://github.com/yetmike/healthex/commit/597fd4bd02ca53a09b42da2aa6d4ef61c94b5aa8))

SQLAlchemy resolved Mapped[date] as the mapped_column object because the class attribute name
  shadowed the datetime.date import.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

### Chores

- Install pre-commit, fix all mypy errors
  ([`b3882d2`](https://github.com/yetmike/healthex/commit/b3882d2a2cdc78013e7f5b112ed25975f68dea7f))

- pre-commit hook installed - Removed stale type: ignore comments in auth.py and models.py - Fixed
  bare dict types in tests -> dict[str, object] - Added Engine type annotations to conftest and
  test_repository - Added mypy overrides: disallow_untyped_decorators=false globally,
  disallow_untyped_defs=false for tests, disallow_subclassing_any=false for models - Removed uv-lock
  hook (breaks lockfile in isolated pre-commit env)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Documentation

- Rewrite README, add LICENSE and CONTRIBUTING
  ([`2e83be4`](https://github.com/yetmike/healthex/commit/2e83be4eb853c051f84c02b180f56d3cabeb3954))

- README: updated for current feature set (sleep/steps/RHR/HRV), removed stale Alembic references,
  correct commands and scopes - LICENSE: Apache-2.0 - CONTRIBUTING: setup, test, lint, project
  structure, how to add a data type

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Use pg.yetmike.com FQDN for homelab database URL
  ([`40af697`](https://github.com/yetmike/healthex/commit/40af697d5786de0e8c4311a330012f166c0b7206))

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

### Features

- Add --days sync option, Dockerfile, and GHCR CI workflow
  ([`518e184`](https://github.com/yetmike/healthex/commit/518e1849e1be003d63d0e0354dade167d5989a15))

- Add `healthex sync --days N` to compute --since automatically (mutual exclusive with --since;
  keeps --since for backwards compat) - Add tests/test_cli.py covering --days, --since, and mutual
  exclusion - Add Dockerfile (python:3.12-slim + uv, runtime deps only) - Add .dockerignore
  (excludes credentials, .git, tests, .venv) - Add .github/workflows/docker.yml: builds
  ghcr.io/yetmike/healthex on v* semver tags (1.2.3 / 1.2 / 1 / latest); edge+sha on main pushes -
  Fix ci.yml: replace broken `alembic upgrade head` with `healthex db-init` - Remove
  healthex-mvp-plan.md from git (moved to ~/healthex-mvp-plan.md); add it + .claude/ to .gitignore
  so planning docs stay out of the repo - Add container/scheduled sync section to README.md

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Add health_metrics_and_measurements.readonly scope for RHR and HRV
  ([`ecbc738`](https://github.com/yetmike/healthex/commit/ecbc738e0133048980e6f23205171479f0ca08a8))

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

- Add RHR and HRV ingestion
  ([`3bf929c`](https://github.com/yetmike/healthex/commit/3bf929c55dd5117fdc16a0c9261314978b0e1b55))

- New daily-resting-heart-rate and daily-heart-rate-variability API endpoints (kebab-case IDs,
  googlehealth.health_metrics_and_measurements.readonly scope) - heart.py: parse_rhr / parse_hrv for
  the confirmed API shapes - Migration 0003: daily_rhr and daily_hrv tables - CLI sync: fetches and
  upserts RHR + HRV alongside sleep and steps

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Add steps tracking (daily_steps table, API fetch, upsert)
  ([`81d5e43`](https://github.com/yetmike/healthex/commit/81d5e43241164ded673690c761db627d3057b9d7))

- DailySteps ORM model + migration 0002 - HealthClient.list_steps() mirrors list_sleep() pattern -
  steps.parse_day() parses steps dataPoints - repository.upsert_steps() idempotent upsert on
  (user_id, date) - sync command fetches steps after sleep; skips gracefully on API error

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

- Derive sleep efficiency from minutesAsleep / minutesInSleepPeriod
  ([`fdfa0e7`](https://github.com/yetmike/healthex/commit/fdfa0e7bf13949927edb772d52c1ffc77d85768d))

API does not provide efficiency directly; compute it during parsing so the column is populated in
  the DB and visible in Grafana.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

- Derive sleep score from duration, efficiency, and stage quality
  ([`a08ff57`](https://github.com/yetmike/healthex/commit/a08ff57f2eab4e368a5ff18a84bdbef4baa85af6))

Proxy 0-100 score (Fitbit score not available via API): - Duration (0-40): minutes_asleep scaled to
  8h target - Efficiency (0-30): minutes_asleep / minutes_in_period - Stage quality (0-30):
  (deep+REM) % of asleep, target ~45%

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

- Initial healthex MVP scaffold
  ([`b5dc8eb`](https://github.com/yetmike/healthex/commit/b5dc8eba7b81f4932fb13e90243e1e86c643818f))

Full Python CLI for exporting Google Health sleep data to PostgreSQL: - auth: OAuth2 flow via
  google-auth-oauthlib (loopback server) - client: httpx-based Google Health REST API client with
  pagination - sleep: parse_session() maps raw dataPoints to row dicts (score nullable) -
  models/db/repository: SQLAlchemy 2.0 + idempotent ON CONFLICT upsert - migrations: Alembic
  migration creating sleep_sessions table with JSONB raw column - cli: `healthex auth login` and
  `healthex sync --since` commands - tests: 7 unit tests (sleep parsing + respx-mocked API); DB
  tests for CI - ci: GitHub Actions workflow with ephemeral Postgres service - pre-commit: ruff,
  mypy, gitleaks, uv-lock hooks

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

### Refactoring

- Fix all lint errors and simplify code
  ([`99f6f8a`](https://github.com/yetmike/healthex/commit/99f6f8a84baccffd253e3a3102a90ff19cf7682c))

- client.py: inline _paginate, remove comments - heart.py: extract long RMSSD key into constant, fix
  line lengths - steps.py: use setdefault, fix line lengths - repository.py: expand long set_ dict
  onto multiple lines - ruff format applied to steps.py and tests/test_client.py

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Replace Alembic migrations with Base.metadata.create_all
  ([`7345829`](https://github.com/yetmike/healthex/commit/7345829d5b9624728c8cbe79103d33340eb5e49e))

Single-user project with a fully recoverable data source - drop and resync is simpler than tracked
  migrations. db-migrate -> db-init.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
