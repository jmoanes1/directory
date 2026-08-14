#!/usr/bin/env bash
# Render start script: migrate against the runtime database, then serve.
set -o errexit
set -o pipefail

echo "==> Applying database migrations..."
python manage.py migrate --no-input

# Always create admin on a fresh Render database (local users are not copied).
echo "==> Ensuring admin login account exists..."
python manage.py ensure_admin

# Idempotent sample data so demo logins from the README work on Render.
echo "==> Seeding sample data if the database is empty..."
python manage.py seed_data

echo "==> Starting gunicorn..."
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}"
