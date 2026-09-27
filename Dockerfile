# Python 3.11 slim, non-root, gunicorn on config.wsgi.
# Secrets and DATABASE_URL come from env at runtime. Do not COPY .env* (see .dockerignore).

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod

WORKDIR /app

# Install deps before copying the app so requirement changes reuse cached layers.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn==23.0.0

COPY . .

# Fixed UID/GID so bind mounts and compose volumes behave predictably; no root at runtime.
RUN groupadd --gid 1000 app \
    && useradd --uid 1000 --gid app --home /app --shell /usr/sbin/nologin app \
    && chown -R app:app /app

USER app

EXPOSE 8000

# Migrations and collectstatic are a compose concern. gunicorn only serves WSGI.
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
