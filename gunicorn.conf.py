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
    auto_seed = os.environ.get("AUTO_SEED", "").lower() in ("true", "1", "yes")
    if auto_seed:
        server.log.info("Seeding default admin / sample data (AUTO_SEED=true)...")
        call_command("seed_data")
    # Close connections opened in the master so forked workers do not inherit
    # a stale socket (that shows up as OperationalError on login).
    from django.db import connections

    connections.close_all()
