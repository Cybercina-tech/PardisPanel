from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-j&hjb3ypz=33k0kr0g1t(qi^4pyz0dy**jm&y*qalq7q)q&o@g'

DEBUG = True

ALLOWED_HOSTS = ['panel.sarafipardis.co.uk', 'www.panel.sarafipardis.co.uk', "localhost", "127.0.0.1", "admin.sarafipardis.co.uk", "www.admin.sarafipardis.co.uk"] # For development. In production, only list your domains.

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
    # third-party apps
    'rest_framework',

]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # Enforce login for all views (allows exceptions in middleware)
    'accounts.middleware.LoginRequiredMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Custom 404 middleware to show custom 404 page even when DEBUG=True
    'SarafiPardis.middleware.Custom404Middleware',
]

ROOT_URLCONF = 'SarafiPardis.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # Custom templates path
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'category.context_processors.categories_processor',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'SarafiPardis.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

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

# -----------------------------
# Static & Media configuration
# -----------------------------

# URL address for static files
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',  # Location of static files in development
    BASE_DIR / 'assets',  # Shared template assets (backgrounds, fonts, presets)
]
STATIC_ROOT = BASE_DIR / 'public' / 'staticfiles'  # Collection location for files in production

# URL address for uploaded files (images, etc.)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'public' / 'media'

# -----------------------------
# Template & Rendering extras
# -----------------------------
TEMPLATE_EDITOR_DEFAULT_FONT = str(BASE_DIR / 'assets' / 'fonts' / 'YekanBakh.ttf')
PRICE_RENDERER_FONT_ROOT = BASE_DIR / 'assets' / 'fonts'
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
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
SESSION_COOKIE_AGE = 1209600  # 2 weeks in seconds
SESSION_EXPIRE_AT_BROWSER_CLOSE = False