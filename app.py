"""
WSGI entry so platforms that default to ``gunicorn app:app`` (Render) work.

Django's real callable is ``config.wsgi:application``. This module re-exports
it as ``app`` so a dashboard Start Command of ``gunicorn app:app`` does not
fail with ``ModuleNotFoundError: No module named 'app'``.
"""

from config.wsgi import application as app

# Keep the Django name available for ``gunicorn config.wsgi:application``.
application = app
