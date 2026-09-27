# Changelog

## [Unreleased]

### Added

- Django 5 + DRF API with JWT auth. Local HS256 for tests and offline work; Cognito
  (RS256 / JWKS) when `AUTH_ISSUER=cognito`.
- Policy, redaction, and audit live in `core/`. The API never returns fields the
  caller is not allowed to see. A subject can only act on their own record.
- Two example domains: identity (`domain/`) and assets (`domain2/`). `core/` does
  not import either.
- Optional Vite + React demo SPA in `frontend/`. Token stays in memory, not
  localStorage. Dev login or Cognito Hosted UI.
- Optional Cognito post-confirmation Lambda in `infra/cognito/` that puts new
  sign-ups in `public_caller`. Safe to delete.
- Optional Stripe webhook port in `core/payments/`. Off by default.
- Docker Compose (web + Postgres + Redis), GitHub Actions CI, and a secrets
  helper in `config/secrets.py`.

### Security

- Missing or empty reads return 404, not 403, so callers cannot probe whether a
  person exists.
- Writes only accept keys on the server allow-list. Extra keys get 403 and
  nothing is saved.
- Tokens are not logged or put in error messages.
- Production settings turn Django admin off, require Postgres and a shared cache,
  and keep `/api/v1/dev/login` hidden.
