#!/usr/bin/env bash
# Render build script for Employee Directory (Django)
# Fail the deploy immediately if any step errors.
set -o errexit
set -o pipefail

echo "==> Upgrading pip..."
pip install --upgrade pip

echo "==> Installing Python dependencies..."
pip install -r requirements.txt

echo "==> Collecting static files..."
python manage.py collectstatic --no-input

# Migrate against Postgres only when DATABASE_URL is already available.
# If it is missing at build time, migrate runs at process start instead —
# otherwise we would migrate SQLite here and then hit an empty Postgres on login.
if [ -n "${DATABASE_URL:-}" ]; then
  echo "==> Running database migrations..."
  python manage.py migrate --no-input
else
  echo "==> DATABASE_URL not set; skipping migrate during build (will run at start)."
fi

echo "==> Build finished successfully."
