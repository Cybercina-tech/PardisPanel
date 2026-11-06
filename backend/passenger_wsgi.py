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

# Secrets live outside the repo in KEY=VALUE lines (see docs/CPANEL_DEPLOY.md), so a
# `git pull` never touches them and they are not in the web-served tree.
_env_file = os.environ.get("PARDIS_ENV_FILE") or os.path.join(
    os.path.dirname(os.path.dirname(PROJECT_DIR)), ".env.production"
)
if os.path.isfile(_env_file):
    with open(_env_file, encoding="utf-8") as _fh:
        for _line in _fh:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MrExchangePanel.settings")
os.environ.setdefault("DJANGO_DEBUG", "False")

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
