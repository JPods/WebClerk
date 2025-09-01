import os
import sys
from pathlib import Path
from decouple import config
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

BASE_DIR = Path(__file__).resolve().parent.parent

# Provide fallback secret for local/dev or test runs if not supplied via env
SECRET_KEY = config('SECRET_KEY', default='insecure-dev-test-key')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

INSTALLED_APPS = [
    #'debug_toolbar',

    'apps.communications',
    'apps.core',
    'apps.docs',
    'apps.orgs',
    'apps.products',
    'apps.support',
    'apps.sync',
    'apps.transactions',
    'common',
    'corsheaders',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',
    'rest_framework',
    'rest_framework_simplejwt',
    'django_filters',
    'drf_spectacular',
    'django_celery_beat',
    'django_celery_results',
    'django_extensions',
]

MIDDLEWARE = [
    #'debug_toolbar.middleware.DebugToolbarMiddleware',
    'corsheaders.middleware.CorsMiddleware', 
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'common.middleware.RequestLogMiddleware',
]

ROOT_URLCONF = 'webclerk3_api.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',  # Only core/templates now
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


WSGI_APPLICATION = 'webclerk3_api.wsgi.application'

# Database selection
# Previous logic defaulted to in-memory SQLite which caused missing tables in dev.
# New logic: default to Postgres; only use in-memory SQLite during pytest (PYTEST_CURRENT_TEST) or when USE_SQLITE_TEST=1 explicitly.
_force_pg = os.environ.get('PYTEST_FORCE_DB') == '1'
_explicit_sqlite = os.environ.get('USE_SQLITE_TEST') == '1'
_running_pytest = bool(os.environ.get('PYTEST_CURRENT_TEST'))

if _force_pg or (not _explicit_sqlite and not _running_pytest and not _force_pg):
    # Postgres path (default)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DATABASE_NAME', default='commerce_expert'),
            'USER': config('DATABASE_USER', default='postgres'),
            'PASSWORD': config('DATABASE_PASS', default=''),
            'HOST': config('DATABASE_HOST', default='localhost'),
            'PORT': config('DATABASE_PORT', default='5432'),
            'ATOMIC_REQUESTS': False,
        }
    }
else:
    # Fast in-memory database for tests
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
            'ATOMIC_REQUESTS': False,
        }
    }

# Warn if running development server with in-memory DB (data will vanish per process)
if DATABASES['default']['ENGINE'].endswith('sqlite3') and DATABASES['default']['NAME'] == ':memory:' and 'runserver' in ' '.join(sys.argv):
    print('[WARNING] runserver using in-memory SQLite (:memory:). Data will not persist. Set USE_SQLITE_TEST=0 or PYTEST_FORCE_DB=1 for Postgres.')

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',  # keep for existing HTML form login
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
        #QQQDevelopment ONLY
        #'rest_framework.permissions.AllowAny',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.ScopedRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.AnonRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'user': '10000/day',
        'anon': '100/day',
        'tx_parent': '2000/day',
        'tx_line': '5000/day',
        'tx_aggregate': '1000/day',
    },
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.OrderingFilter',
        'rest_framework.filters.SearchFilter',
    ],
}

from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'AUTH_HEADER_TYPES': ('Bearer',),
}

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST')
EMAIL_PORT = config('EMAIL_PORT', cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'

import os
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'core', 'static'),
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'core.Contact'
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, '.local/logs/webclerk3.log'),
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'DEBUG',
    },
    'loggers': {
        'core.views': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'request': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}



DRF_SPECTACULAR_SETTINGS = {
    'TITLE': 'WEBCLERK 3.0 API',
    'DESCRIPTION': 'API for managing full ERP system with role-based access, email verification, and JWT authentication.',
    'VERSION': '3.0.0',
    'SERVE_INCLUDE_SCHEMA': True,
    'SECURITY': [
        {
            'BearerAuth': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
            },
        },
    ],
}

# CORS settings
CORS_ALLOW_ALL_ORIGINS = True  # For development only; restrict in production
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]
CORS_ALLOW_CREDENTIALS = True  # Allow cookies/JWT in cross-origin requests

# Add this at the bottom
INTERNAL_IPS = [
    '127.0.0.1',
    'localhost',
]

CELERY_BROKER_URL = 'redis://localhost:6379/0'  # or use RabbitMQ if you prefer
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_BEAT_SCHEDULE = {
    # Lightweight periodic normalization of stats structures
    'recompute-basic-stats-hourly': {
        'task': 'common.tasks.recompute_basic_stats',
        'schedule': 60 * 60,  # hourly
        'options': {'expires': 55 * 60},
    },
    # Relationship counts (org link heuristics) - run less frequently
    'recompute-relationship-counts-2h': {
        'task': 'common.tasks.recompute_relationship_counts',
        'schedule': 2 * 60 * 60,  # every 2 hours
        'options': {'expires': 115 * 60},
    },
    # Keyword refresh (kept modest cadence; task self-limits work)
    'refresh-keywords-30m': {
        'task': 'common.tasks.refresh_keywords_task',
        'schedule': 30 * 60,  # every 30 minutes
        'options': {'expires': 25 * 60},
    },
}

GRAPH_MODELS = {
    'all_applications': True,
    'group_models': True,
}

SENTRY_DSN = config('SENTRY_DSN', default='')

if isinstance(SENTRY_DSN, str) and SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=1.0,
        send_default_pii=True
    )

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
X_FRAME_OPTIONS = 'DENY'

LANGUAGES = [
    ('en', 'English'),
    # ('es', 'Spanish'),
    # Add more as needed
]

# --- WCAPI optional relaxed read mode (development convenience) ---
# If WCAPI_OPEN_READ=1 and WCAPI_JWT_ONLY is False, unauthenticated GET/POST (query) requests to
# wcapi read endpoints are permitted and treated as role PUBLIC. Writes still require auth.
WCAPI_OPEN_READ = os.getenv('WCAPI_OPEN_READ', '0') == '1'
WCAPI_JWT_ONLY = os.getenv('WCAPI_JWT_ONLY', '0') == '1'

# --- Test Environment Overrides (Celery eager, in‑memory broker) ---
import os as _os  # local alias to avoid shadowing
if _os.environ.get('PYTEST_CURRENT_TEST'):
    # Execute Celery tasks synchronously to prevent broker dependency in tests
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
    CELERY_BROKER_URL = 'memory://'
    CELERY_RESULT_BACKEND = 'cache+memory://'