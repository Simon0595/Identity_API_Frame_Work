# API Web Framework

Django 5 + DRF backend (university final-project prototype). JWT auth (local mock or
Cognito), policy / redaction / audit in `core/`, optional Stripe, CI, and Docker
Compose.

`core/` never imports domain packages (see `tests/test_reuse.py`). Two example
domains, `domain` (identity) and `domain2` (assets), show the split. Delete or
replace them. Copy `domain2/` if you add another schema.

**Requirements:** Python 3.11+

## Quick start

```bash
# 1. Create and activate a virtual environment
python3.11 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 2. Install pinned dependencies
pip install -r requirements.txt

# 3. Configure local environment (never commit .env)
cp .env.example .env
# Edit .env and set a real SECRET_KEY for local use.

# 4. Apply migrations and run checks
python manage.py migrate
python manage.py check

# 5. Start the development server
python manage.py runserver
```

Open http://127.0.0.1:8000/health/ and you should see `{"status":"ok"}`.

The default settings use the local HS256 issuer (`AUTH_ISSUER=local`), so dev and
tests run offline with no AWS.

### Docker / Compose

Use `runserver` above for day-to-day work (SQLite, `config.settings.dev`).
For Postgres + gunicorn, use Docker Compose:

```bash
# 1. Ensure .env has compose-required vars (see .env.example Docker section)
cp .env.example .env   # skip if you already have .env
# Set at least: SECRET_KEY, POSTGRES_PASSWORD

# 2. Build and start web (gunicorn + config.settings.prod) + Postgres
docker compose up --build

# 3. Smoke check (migrations run on web startup)
curl -s http://127.0.0.1:8000/health/
```

Compose reads secrets from your git-ignored `.env`. Nothing is baked into the
image (see `.dockerignore`). The `web` service waits for Postgres, runs
`migrate` + `collectstatic`, then serves via gunicorn on port 8000. Stop with
`docker compose down`. `docker compose down -v` also drops the Postgres volume.

| Mode | Settings module | Database | Server |
|------|-----------------|----------|--------|
| Local dev | `config.settings.dev` (default) | SQLite | `manage.py runserver` |
| Compose / prod-like | `config.settings.prod` | Postgres (`db` service) | gunicorn in container |

### Running against a real Cognito pool

Put your pool values in a git-ignored `.env.cognito` (`AUTH_ISSUER=cognito`,
`COGNITO_REGION`, `COGNITO_USER_POOL_ID`, `COGNITO_APP_CLIENT_ID`), then:

```bash
python manage.py runserver --settings=config.settings.cognito
# management commands take the same flag, e.g.:
DJANGO_SETTINGS_MODULE=config.settings.cognito python manage.py seed
```

Token checks only fetch the pool's public JWKS. The API needs no AWS credentials
at runtime.

## Production deployment

Production uses `config.settings.prod`. Local dev, tests, and the Cognito overlay
never import it. Copy the production placeholders from `.env.example` into a
git-ignored `.env.prod`, or export the same vars on the host.

Required env (no wildcard hosts, no SQLite):

- `SECRET_KEY`: long random value (50+ chars)
- `ALLOWED_HOSTS`: comma-separated hostnames (e.g. `example.com,api.example.com`)
- `DATABASE_URL`: `postgresql://user:pass@host:5432/dbname`
- `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`: HTTPS settings (see `.env.example`)
- `AUTH_ISSUER=cognito` is what you want in production. Set the Cognito vars from
  `.env.example`.

Verify before deploy:

```bash
export DJANGO_SETTINGS_MODULE=config.settings.prod
# set SECRET_KEY, ALLOWED_HOSTS, DATABASE_URL, etc.
python manage.py check --deploy
```

Collect static files, then serve via WSGI (`config/wsgi.py`). Gunicorn is not a
project dependency. Install it on the host if you use it:

```bash
python manage.py collectstatic --noinput --settings=config.settings.prod
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

HSTS, secure cookies, and Postgres-via-env live in `config/settings/prod.py`.

### Before a public launch

Fine for demos and hand-in. Before putting real data on the public internet,
check TLS and secrets, CORS, throttling, a shared cache, and that Django admin
is off.

## Secrets & configuration

Runtime secrets go through `config.secrets.get_secret`. Copy names from
`.env.example`. Put real values only in git-ignored files (`.env`, `.env.prod`)
or the host environment.

| Context | `SECRETS_BACKEND` | Where values come from |
|---------|-------------------|------------------------|
| Local / tests / CI | `env` (default) | Environment variables |
| Production (optional) | `aws` | AWS SSM via the instance or task role |

**Local:** leave `SECRETS_BACKEND` unset. Set `SECRET_KEY`, `DATABASE_URL`, etc.
in `.env`.

**Production:** set `SECRETS_BACKEND=env` and supply vars from your platform, or
set `SECRETS_BACKEND=aws` and store values as SSM parameters (e.g.
`/myapp/prod/DATABASE_URL`). The API uses the instance or ECS task role. No
long-lived `AWS_ACCESS_KEY_ID` on the box.

Missing required secrets raise `SecretNotFoundError` with the key name only,
never the value. JWT / Cognito checks fetch public JWKS and do not use this
resolver.

See `config/secrets.py`.

## Tests and quality checks

Same commands CI runs:

```bash
ruff check .
mypy .
python manage.py makemigrations --check --dry-run
pytest -q --cov=core --cov-fail-under=85
```

Use test settings so JWT minting stays offline:
`export DJANGO_SETTINGS_MODULE=config.settings.test` and
`export AUTH_ISSUER=local` (CI sets these).

## Continuous integration

Every push and pull request runs [`.github/workflows/ci.yml`](.github/workflows/ci.yml).
A failing step fails the build.

| Step | Command / tool | Typical failure |
|------|----------------|-----------------|
| Ruff | `ruff check .` | Lint or import-order violation |
| Mypy | `mypy .` | Type error in `config/`, `core/`, `domain*`, or `tests/` |
| Migrations | `makemigrations --check --dry-run` | Model change without a migration file |
| Pytest | `pytest -q --cov=core --cov-fail-under=85` | Test failure or core coverage below 85% |
| Secrets | gitleaks (pinned action) | Committed credential or secret pattern |

CI uses a dummy `SECRET_KEY`, `DJANGO_SETTINGS_MODULE=config.settings.test`, and
`AUTH_ISSUER=local`. No `AWS_*`, `COGNITO_*`, or `STRIPE_*` in the workflow.

If a build goes red, open the failed Actions run and expand the first red step.
Reproduce with the commands above.

## Evaluation

`tests/test_threat_coverage.py` maps security tests to OWASP API risks (BOLA,
BOPLA, throttling, function-level authz, error handling) and JWT threats
(alg:none, signature, exp, aud, iss). The map test fails if a listed test is
renamed or removed.

```bash
pytest tests/test_threat_coverage.py -q
```

Coverage is measured on `core/` only (policy, redaction, permissions, audit,
JWT). Threshold is 85% in `pyproject.toml`.

```bash
pytest --cov=core --cov-report=term-missing -q
```

Optional OWASP ZAP baseline via Docker against a server you own. ZAP is not a
project dependency. Do not commit scan HTML.

## Payments (optional)

Payments sit behind `PaymentProvider` in `core/payments/`. Default is
`disabled`, so you do not need a Stripe account for tests. Set
`PAYMENT_PROVIDER=stripe` plus `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET`
to turn Stripe on. `POST /api/v1/payments/webhook` checks the Stripe signature,
not a JWT.

Webhook de-dupe uses Django's cache (`cache.add` on event id). LocMem is
per-process, so a multi-worker deploy needs Redis or similar. See
`core/payments/`.

## Project layout

| Path | Purpose |
|------|---------|
| `core/` | JWT auth, policy, redaction, audit, payments (no domain imports) |
| `domain/` | Identity example (Person / ProfileField). Optional. |
| `domain2/` | Assets example. Optional, safe to delete. |
| `config/` | Django project (settings, URLs, WSGI/ASGI) |
| `config/secrets.py` | Secret helper (`SECRETS_BACKEND=env` or `aws`) |
| `config/settings/base.py` | Shared settings |
| `config/settings/dev.py` | Local development (`manage.py` default) |
| `config/settings/cognito.py` | Dev + real Cognito pool (`.env.cognito`) |
| `config/settings/prod.py` | Production overlay (`.env.prod`) |
| `config/settings/test.py` | Pytest / mypy |
| `tests/` | Smoke, integration, and core isolation tests |
| `requirements.txt` | Pinned dependencies |
| `pyproject.toml` | pytest, ruff, mypy, coverage |
| `.env.example` | Copy to `.env` |
| `Dockerfile` | Python 3.11 slim, non-root, gunicorn |
| `docker-compose.yml` | Local `web` + Postgres + Redis |
| `.dockerignore` | Keeps secrets, venv, SQLite, caches out of the image |

## Database

SQLite is the default for local work (`db.sqlite3`, git-ignored). Settings use
Django's database config only, so PostgreSQL is a drop-in via env vars (see
`.env.example`).
