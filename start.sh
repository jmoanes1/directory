#!/usr/bin/env bash
# Render start script: migrate against the runtime database, then serve.
set -o errexit
set -o pipefail

echo "==> Applying database migrations..."
python manage.py migrate --no-input

if [ "${AUTO_SEED:-false}" = "true" ]; then
  echo "==> Seeding default admin (AUTO_SEED=true)..."
  python manage.py seed_data
fi

echo "==> Starting gunicorn..."
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}"
