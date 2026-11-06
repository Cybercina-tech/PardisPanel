"""Passenger WSGI entry point for cPanel ("Setup Python App").

cPanel activates the app's virtualenv itself, so this file only needs the project
directory on ``sys.path`` and the settings module. Configuration (secret key,
hosts, API keys) comes from the environment variables set in the cPanel UI.
"""
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MrExchangePanel.settings")
os.environ.setdefault("DJANGO_DEBUG", "False")

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
