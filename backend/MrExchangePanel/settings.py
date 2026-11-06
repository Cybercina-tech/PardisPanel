from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# Security: DEBUG should be False in production
# Set DJANGO_DEBUG=False in environment variables for production
DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() in ('true', '1', 'yes')
DEPLOYMENT_MODE = os.environ.get('DEPLOYMENT_MODE', 'cloud').strip().lower()
TRIAL_EXPIRY_CHECK_SECONDS = float(os.environ.get('TRIAL_EXPIRY_CHECK_SECONDS', '3600'))
APP_VERSION = os.environ.get('APP_VERSION', '').strip()

# Security: Use environment variable for SECRET_KEY
# Generate a new key with: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
_SECRET_KEY_RAW = os.environ.get('DJANGO_SECRET_KEY', '')
if not _SECRET_KEY_RAW:
    if DEBUG:
        import warnings
        warnings.warn(
            'DJANGO_SECRET_KEY not set — using insecure dev-only default. '
            'Set the env var before deploying to production.',
            stacklevel=1,
        )
        SECRET_KEY = 'django-insecure-dev-only-DO-NOT-USE-IN-PRODUCTION'
    else:
        raise ValueError(
            'DJANGO_SECRET_KEY environment variable is required in production. '
            'Generate one with: python -c "from django.core.management.utils '
            'import get_random_secret_key; print(get_random_secret_key())"'
        )
else:
    SECRET_KEY = _SECRET_KEY_RAW

# Security: ALLOWED_HOSTS should only contain production domains
# Set DJANGO_ALLOWED_HOSTS in environment (comma-separated) for production
allowed_hosts_env = os.environ.get('DJANGO_ALLOWED_HOSTS', '')
if allowed_hosts_env:
    ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_env.split(',')]
else:
    # Development defaults
    ALLOWED_HOSTS = ['panel.sarafipardis.co.uk', 'www.panel.sarafipardis.co.uk', 'localhost', '127.0.0.1']

# When behind a reverse proxy (e.g. Vite dev proxy) that sends X-Forwarded-Host, use it for
# request.build_absolute_uri().
_xfh_env = os.environ.get('DJANGO_USE_X_FORWARDED_HOST')
if _xfh_env is not None:
    USE_X_FORWARDED_HOST = _xfh_env.lower() in ('1', 'true', 'yes')
else:
    USE_X_FORWARDED_HOST = DEBUG

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # local apps
    'category',
    'dashboard',
    'accounts',
    'change_price',
    'special_price',
    'telegram_app',
    'setting',
    'finalize',
    'price_publisher',
    'template_editor',
    'analysis',
    # third-party apps
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'accounts.auth.JWTAuthenticationWithTokenVersion',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'EXCEPTION_HANDLER': 'core.exceptions.custom_exception_handler',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'finalize': '60/hour',
        'settings': '200/hour',
        'public_prices': '2000/hour',
        'public_site': '1000/hour',
        # One heartbeat a day per install; the headroom absorbs restarts and
        # retries without letting an unknown key hammer the endpoint.
        'fleet_checkin': '60/hour',
        # Guessing the current password is the only way through this endpoint,
        # so it is rate-limited like a login rather than like an ordinary write.
        'password_change': '10/hour',
        # Registration is anonymous and creates rows; keep it well under the
        # generic anon rate so a script cannot fill the user table.
        'signup': '10/hour',
        # Password guessing is the reason this exists; the generic anon rate
        # is far too generous for an endpoint that hands out tokens.
        'login': '30/hour',
        # Anonymous customers submitting orders from WhatsApp or the Telegram
        # Mini App; generous enough for a real conversation, tight enough that
        # a leaked webapp link cannot flood the queue.
        # A desk's own customers signing up and signing in on its website.
        # Same reasoning as 'signup'/'login' above, counted separately so a
        # busy public site cannot exhaust the staff allowance.
        'customer_signup': '10/hour',
        'customer_login': '30/hour',
        'customer_panel': '600/hour',
        # The console's only anonymous endpoint. Counted per IP: the owner's
        # address is public knowledge, so a per-address lockout would be a way
        # to lock the owner out of their own console rather than a defence.
        'console_login': '30/hour',
    },
}

# Finalize: when True, do not persist finalization if Telegram publish fails (rollback semantics).
# When False, persist with message_sent=False on Telegram failure.
FINALIZE_STRICT_TELEGRAM = os.environ.get('FINALIZE_STRICT_TELEGRAM', 'False').lower() in ('true', '1', 'yes')

from datetime import timedelta as _td  # noqa: E402

# How long a customer stays signed in to the Customer Panel on a desk's
# website. Longer than a staff session: a customer checks a rate and leaves,
# and being logged out between visits is what pushes them back to Telegram.
CUSTOMER_PANEL_JWT_LIFETIME_MINUTES = int(
    os.environ.get('CUSTOMER_PANEL_JWT_LIFETIME_MINUTES', '720')
)

# Refresh-token lifetime when "Remember me" is ticked at login.
REMEMBER_ME_REFRESH_DAYS = int(os.environ.get('REMEMBER_ME_REFRESH_DAYS', '30'))

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': _td(hours=12),
    'REFRESH_TOKEN_LIFETIME': _td(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://localhost:5250',
    'http://127.0.0.1:5250',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'https://mrexchange.co.uk',
    'https://www.mrexchange.co.uk',
]
CORS_ALLOW_CREDENTIALS = True

# Required when the SPA runs on another origin/port (e.g. Vite :5173) and proxies API
# to Django: the browser sends Origin: http://localhost:5173 while Host may be backend:8000.
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://localhost:5250',
    'http://127.0.0.1:5250',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'https://mrexchange.co.uk',
    'https://www.mrexchange.co.uk',
]
_csrf_extra = os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').strip()
if _csrf_extra:
    CSRF_TRUSTED_ORIGINS = list(
        dict.fromkeys(CSRF_TRUSTED_ORIGINS + [o.strip() for o in _csrf_extra.split(',') if o.strip()])
    )

# Split-host deployments only (e.g. landing on mrexchange.co.uk, panel on
# app.mrexchange.co.uk). Both are handed to the SPA as <meta> tags, which moves
# panel routes to PANEL_ORIGIN and the landing page to LANDING_ORIGIN. Leave
# both empty to serve everything from one host.
LANDING_ORIGIN = os.environ.get('LANDING_ORIGIN', '').strip().rstrip('/')
PANEL_ORIGIN = os.environ.get('PANEL_ORIGIN', '').strip().rstrip('/')

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # Enforce login for all views (allows exceptions in middleware)
    'accounts.middleware.LoginRequiredMiddleware',
    'accounts.middleware.AccountScopeMiddleware',
    'accounts.middleware.TrialAccessMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Custom 404 middleware to show custom 404 page even when DEBUG=True
    'MrExchangePanel.middleware.Custom404Middleware',
]

ROOT_URLCONF = 'MrExchangePanel.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # Custom templates path
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': False,
        'OPTIONS': {
            # Un-cached loaders: templates are re-read on every request so HTML
            # edits hot-reload even with DEBUG=False (Django 6.1 would otherwise
            # default to the cached loader).
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ],
            'context_processors': [
                'django.template.context_processors.debug',
                'setting.context_processors.site_settings_processor',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'MrExchangePanel.wsgi.application'

# Database
#
# Production: set POSTGRES_DB (or DATABASE_URL) for PostgreSQL.
# Development default: SQLite with WAL (see docker-compose.yml).
def _database_config():
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if database_url.startswith("postgres://") or database_url.startswith("postgresql://"):
        from urllib.parse import unquote, urlparse

        parsed = urlparse(database_url)
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": unquote(parsed.path.lstrip("/")),
            "USER": unquote(parsed.username or ""),
            "PASSWORD": unquote(parsed.password or ""),
            "HOST": parsed.hostname or "localhost",
            "PORT": str(parsed.port or 5432),
            "CONN_MAX_AGE": int(os.environ.get("POSTGRES_CONN_MAX_AGE", "60")),
        }

    postgres_db = os.environ.get("POSTGRES_DB", "").strip()
    if postgres_db:
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": postgres_db,
            "USER": os.environ.get("POSTGRES_USER", "postgres"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
            "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": int(os.environ.get("POSTGRES_CONN_MAX_AGE", "60")),
        }

    return {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("SQLITE_PATH", str(BASE_DIR / "db.sqlite3")),
        "OPTIONS": {
            "timeout": int(os.environ.get("SQLITE_TIMEOUT", "30")),
            "init_command": (
                "PRAGMA journal_mode=WAL;"
                "PRAGMA synchronous=NORMAL;"
                "PRAGMA busy_timeout=30000;"
                "PRAGMA foreign_keys=ON;"
            ),
            "transaction_mode": "IMMEDIATE",
        },
    }


DATABASES = {"default": _database_config()}

# Caching - Removed: No caching is used in this application

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Tehran'  # Change to Iran's time zone
USE_I18N = True
USE_TZ = True

# Max span (days) for GET /api/analysis/dashboard/?start=&end=
ANALYTICS_MAX_RANGE_DAYS = int(os.environ.get('ANALYTICS_MAX_RANGE_DAYS', '366'))

# -----------------------------
# Static & Media configuration
# -----------------------------

# URL address for static files
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',  # Location of static files in development
]
STATIC_ROOT = BASE_DIR / 'public' / 'staticfiles'  # Collection location for files in production

# URL address for uploaded files (images, etc.)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'public' / 'media'

# Redirect uploads to a temp copy during tests so a run cannot dirty or
# overwrite the tracked seed media.
TEST_RUNNER = 'MrExchangePanel.test_runner.IsolatedMediaTestRunner'

# -----------------------------
# Template & Rendering extras
# -----------------------------
TEMPLATE_EDITOR_DEFAULT_FONT = str(BASE_DIR / 'static' / 'fonts' / 'Kalameh.ttf')
PRICE_RENDERER_FONT_ROOT = BASE_DIR / 'static' / 'fonts'
LEGACY_CATEGORY_BACKGROUNDS = {
    "pound": "price_theme/1.png",
    "gbp": "price_theme/1.png",
    "پوند": "price_theme/1.png",
}

# -----------------------------
# Other settings
# -----------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
# Custom user model and auth settings
AUTH_USER_MODEL = 'accounts.CustomUser'
LOGIN_URL = '/login'
LOGIN_REDIRECT_URL = '/'
SESSION_COOKIE_AGE = 1209600  # 2 weeks in seconds
SESSION_EXPIRE_AT_BROWSER_CLOSE = False


# -----------------------------
# Trial tier — one isolated stack per signup, hosted on our own VPS
# -----------------------------
# Trial length itself lives in accounts/trial.py; these govern what happens
# around it. INDIVIDUAL_TRIAL_DAYS is read here so a deployment can only ever
# widen the window deliberately, never by accident.
INDIVIDUAL_TRIAL_DAYS = int(os.environ.get('INDIVIDUAL_TRIAL_DAYS', '14'))
# How many days before expiry the customer and staff get warned, once.
TRIAL_REMINDER_DAYS = int(os.environ.get('TRIAL_REMINDER_DAYS', '3'))
# Grace after expiry: access is already blocked, but the stack and its data
# stay in place so a late conversion still finds them.
TRIAL_GRACE_DAYS = int(os.environ.get('TRIAL_GRACE_DAYS', '7'))
TRIAL_REMINDER_CHECK_SECONDS = float(os.environ.get('TRIAL_REMINDER_CHECK_SECONDS', '3600'))
TRIAL_TEARDOWN_CHECK_SECONDS = float(os.environ.get('TRIAL_TEARDOWN_CHECK_SECONDS', '86400'))

# Docker-touching provisioning is off unless this host is the trial host.
TRIAL_PROVISIONING_ENABLED = os.environ.get(
    'TRIAL_PROVISIONING_ENABLED', 'False'
).lower() in ('true', '1', 'yes')
TRIAL_BASE_DOMAIN = os.environ.get('TRIAL_BASE_DOMAIN', 'mrexchange.co.uk').strip()
TRIAL_STACKS_ROOT = os.environ.get('TRIAL_STACKS_ROOT', '/srv/mrexchange/trials')
TRIAL_ARCHIVE_ROOT = os.environ.get('TRIAL_ARCHIVE_ROOT', '/srv/mrexchange/trial-archives')
TRIAL_COMPOSE_TEMPLATE = os.environ.get(
    'TRIAL_COMPOSE_TEMPLATE',
    str(BASE_DIR.parent / 'docker' / 'trial-stack.compose.yml'),
)
TRIAL_IMAGE = os.environ.get('TRIAL_IMAGE', 'mrexchange/panel:latest')
TRIAL_CERT_RESOLVER = os.environ.get('TRIAL_CERT_RESOLVER', 'letsencrypt')
TRIAL_EDGE_NETWORK = os.environ.get('TRIAL_EDGE_NETWORK', 'edge')
TRIAL_ADMIN_USERNAME = os.environ.get('TRIAL_ADMIN_USERNAME', 'admin')
DOCKER_COMPOSE_COMMAND = os.environ.get(
    'DOCKER_COMPOSE_COMMAND', 'docker compose'
).split()

# -----------------------------
# Bot gateway — WhatsApp and the Telegram Mini App order form
# -----------------------------
# Customers here are BotCustomer rows, not panel users: they authenticate with a
# short-lived token of their own (bot_gateway.auth), never a staff JWT.
BOT_CUSTOMER_JWT_LIFETIME_MINUTES = int(
    os.environ.get('BOT_CUSTOMER_JWT_LIFETIME_MINUTES', '60')
)
# Absolute base the Mini App is opened at, e.g. https://panel.mrexchange.co.uk
BOT_GATEWAY_FRONTEND_URL = os.environ.get(
    'BOT_GATEWAY_FRONTEND_URL', 'http://localhost:3000'
).rstrip('/')

# -----------------------------
# Headless template rendering (Playwright)
# -----------------------------
# Off by default and per-install: SiteSettings.use_playwright_for_template_render
# is the switch, these only tune it. The engine loads the SPA's
# /headless-render/<id> route in a real browser and screenshots it, so the PNG a
# channel receives matches the editor exactly; any failure falls back to Pillow.
# cPanel cannot run a headless browser: the Playwright path is hard-disabled here
# whatever SiteSettings says, so publishing always uses the Pillow renderer.
PLAYWRIGHT_RENDER_ALLOWED = False
PLAYWRIGHT_FRONTEND_BASE_URL = os.environ.get(
    'PLAYWRIGHT_FRONTEND_BASE_URL', 'http://127.0.0.1:5250'
).rstrip('/')
PLAYWRIGHT_SCREENSHOT_TIMEOUT_MS = int(
    os.environ.get('PLAYWRIGHT_SCREENSHOT_TIMEOUT_MS', '30000')
)
# Chromium is memory-hungry; two at a time is what a small VPS survives.
PLAYWRIGHT_MAX_CONCURRENT = int(os.environ.get('PLAYWRIGHT_MAX_CONCURRENT', '2'))
# Every cache key is namespaced by the account in context. Cached price
# snapshots, formatted captions and settings are customer data, and a shared key
# would serve whichever desk warmed the cache first to all the others — the leak
# the scoped managers close at the database, reopened one layer up. Doing it in
# KEY_FUNCTION rather than at each call site means a cache added later is
# namespaced without anyone remembering to.
CACHES = {
    'default': {
        # Passenger runs several worker processes; an in-memory cache would give
        # each its own copy and serve stale prices after an update. A file cache
        # is shared between them and needs no extra service on cPanel.
        'BACKEND': os.environ.get(
            'CACHE_BACKEND', 'django.core.cache.backends.filebased.FileBasedCache'
        ),
        'LOCATION': os.environ.get('CACHE_LOCATION', str(BASE_DIR / 'cache')),
        'KEY_FUNCTION': 'accounts.cache.account_scoped_key',
    }
}

SCREENSHOT_CACHE_TTL = int(os.environ.get('SCREENSHOT_CACHE_TTL', '300'))

# -----------------------------
# Self-serve signup — email address in, own panel out, trial running
# -----------------------------
# A signup creates a role=management account that owns its own workspace: it is
# the same shape of account the programmer hub creates for a client, minus the
# BotFather token, which the customer adds from the panel afterwards.
SIGNUP_ENABLED = os.environ.get('SIGNUP_ENABLED', 'True').lower() in ('true', '1', 'yes')
# Access is granted immediately; the verification link only clears the banner.
# Kept separate from SIGNUP_ENABLED so a deployment can stop sending mail
# without closing registration.
SIGNUP_EMAIL_VERIFICATION = os.environ.get(
    'SIGNUP_EMAIL_VERIFICATION', 'True'
).lower() in ('true', '1', 'yes')
# How long a verification link stays valid, in seconds (default 3 days).
EMAIL_VERIFICATION_TIMEOUT = int(os.environ.get('EMAIL_VERIFICATION_TIMEOUT', '259200'))
# Absolute base for links inside outgoing mail. Falls back to the first
# non-wildcard allowed host so a misconfigured deployment still sends a
# clickable link rather than "http://None/".
PUBLIC_BASE_URL = os.environ.get('PUBLIC_BASE_URL', '').strip().rstrip('/')

# -----------------------------
# Outgoing email
# -----------------------------
# No SMTP host configured means console output: development and CI print the
# verification link instead of failing, and nothing silently disappears.
EMAIL_HOST = os.environ.get('EMAIL_HOST', '').strip()
if EMAIL_HOST:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', 'False').lower() in ('true', '1', 'yes')
EMAIL_TIMEOUT = int(os.environ.get('EMAIL_TIMEOUT', '10'))
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'Sarafi Pardis <no-reply@sarafipardis.co.uk>')

# "Sign in with Google". Unset means the feature is off end to end: the endpoint
# refuses and the frontend hides the button, so the install ships dormant until
# a client id exists.
GOOGLE_OAUTH_CLIENT_ID = os.environ.get('GOOGLE_OAUTH_CLIENT_ID', '').strip()

# -----------------------------
# Fleet — how this install reports to the owner panel
# -----------------------------
# Set on every deployed install (trial container and customer server alike).
# Security settings
# HTTP-only reverse proxies (e.g. Dokploy *.traefik.me preview URLs): set
# DJANGO_USE_HTTP_BEHIND_PROXY=true so Django does not force HTTPS redirects
# or Secure-only cookies (which break plain-HTTP preview domains).
_use_http_behind_proxy = os.environ.get('DJANGO_USE_HTTP_BEHIND_PROXY', '').lower() in ('true', '1', 'yes')

# cPanel/Passenger sits behind Apache, which terminates TLS and forwards the scheme.
# Without this Django sees plain HTTP and SECURE_SSL_REDIRECT loops forever.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

if not DEBUG:
    if _use_http_behind_proxy:
        SECURE_SSL_REDIRECT = False
        CSRF_COOKIE_SECURE = False
        SESSION_COOKIE_SECURE = False
        SECURE_HSTS_SECONDS = 0
        SECURE_HSTS_INCLUDE_SUBDOMAINS = False
        SECURE_HSTS_PRELOAD = False
    else:
        SECURE_SSL_REDIRECT = True
        CSRF_COOKIE_SECURE = True
        SESSION_COOKIE_SECURE = True
        SECURE_HSTS_SECONDS = 31536000
        SECURE_HSTS_INCLUDE_SUBDOMAINS = True
        SECURE_HSTS_PRELOAD = True
    # Additional security headers
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
else:
    # In development, disable secure cookies for easier testing
    SECURE_SSL_REDIRECT = False
    CSRF_COOKIE_SECURE = False
    SESSION_COOKIE_SECURE = False
    # Still enable some security headers in development
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'

# Application logs: console (human-readable) + rotating JSON file for aggregation (Loki/ELK).
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(parents=True, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {'format': '%(levelname)s %(name)s: %(message)s'},
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'fmt': '%(asctime)s %(name)s %(levelname)s %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file_json': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(LOGS_DIR / 'app.json.log'),
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'json',
            'encoding': 'utf-8',
        },
    },
    'root': {
        'handlers': ['console', 'file_json'],
        'level': 'INFO',
    },
    'loggers': {
        # RBAC debug: console only (avoid duplicate structured noise in app.json.log).
        'accounts.permissions': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': False,
        },
        'django.server': {
            'level': 'INFO',
            'handlers': ['console', 'file_json'],
            'propagate': False,
        },
        'django.request': {
            'level': 'WARNING',
            'handlers': ['console', 'file_json'],
            'propagate': False,
        },
        # Quiet SQL in logs unless troubleshooting.
        'django.db.backends': {
            'level': 'WARNING',
            'handlers': ['console'],
            'propagate': False,
        },
        'finalize': {
            'level': 'INFO',
            'handlers': ['console', 'file_json'],
            'propagate': False,
        },
        'telegram_app': {
            'level': 'INFO',
            'handlers': ['console', 'file_json'],
            'propagate': False,
        },
    },
}

# Celery configuration
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "memory://")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "cache+memory://")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = USE_TZ
CELERY_TASK_TIME_LIMIT = int(os.environ.get("CELERY_TASK_TIME_LIMIT", "120"))
CELERY_TASK_SOFT_TIME_LIMIT = int(os.environ.get("CELERY_TASK_SOFT_TIME_LIMIT", "90"))
CELERY_RESULT_EXPIRES = int(os.environ.get("CELERY_RESULT_EXPIRES", "3600"))
# cPanel has no Redis or worker process: tasks run in-process (eager).
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = False
# Public rates API of the Pardis website (finalize pushes GBP/USDT rates here).
# The key is a secret: set EXTERNAL_API_KEY in the cPanel app environment.
EXTERNAL_API_URL = os.environ.get(
    'EXTERNAL_API_URL', 'https://sarafipardis.co.uk/wp-json/pardis/v1/rates'
)
EXTERNAL_API_KEY = os.environ.get('EXTERNAL_API_KEY', '')
FINALIZE_TASK_WAIT_TIMEOUT = int(os.environ.get("FINALIZE_TASK_WAIT_TIMEOUT", "75"))
