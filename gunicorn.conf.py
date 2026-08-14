"""
Gunicorn settings for Render (and local production-style runs).

Loaded automatically when the working directory contains this file, including
the dashboard default ``gunicorn app:app``.
"""

import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
timeout = 120
accesslog = "-"
errorlog = "-"

# SQLite cannot accept concurrent writers; multiple workers cause
# OperationalError: database is locked on /accounts/login/.
if os.environ.get("DATABASE_URL", "").strip():
    workers = int(os.environ.get("WEB_CONCURRENCY", "2"))
else:
    workers = 1


def on_starting(server):
    """Create missing tables before workers accept traffic (empty Render DB)."""
    import django
    from django.core.management import call_command

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()
    server.log.info("Applying database migrations...")
    call_command("migrate", interactive=False)
    server.log.info("Ensuring admin login account exists...")
    call_command("ensure_admin")
    # Idempotent: fills a fresh Render DB with the README demo accounts.
    server.log.info("Seeding sample data if the database is empty...")
    call_command("seed_data")
    # Close connections opened in the master so forked workers do not inherit
    # a stale socket (that shows up as OperationalError on login).
    from django.db import connections

    connections.close_all()
