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
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '85.31.234.194']


CORS_ALLOWED_ORIGINS = (
    'http://localhost:5173',
    'http://127.0.0.1:5173',
)
CORS_ALLOW_CREDENTIALS = True

# Required by Django when making cookie-authenticated requests from the Vite origin.
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
]

INSTALLED_APPS = [
    'apps.accounts',
    'apps.communications',
    'apps.core',
    'apps.docs',
    'apps.orgs',
    'apps.products',
    'apps.support',
    'apps.sync',
    'apps.transactions.apps.TransactionsConfig',
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
    "apps.core.wcapi.middleware.JSONOnlyMiddleware",
    'corsheaders.middleware.CorsMiddleware',
    'common.middleware.EnsureRenderedMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',  # keep this before any auth-dependent logic
    'django.contrib.messages.middleware.MessageMiddleware',
    'common.middleware.WriteGateMiddleware',
    'common.middleware.RequestLogMiddleware',
    'common.middleware.ExceptionAsJsonMiddleware',
    'common.middleware.AutoEnvelopeMiddleware',
    # Add after DRF/Django exception handling so it can see 404 responses
]


ROOT_URLCONF = 'webclerk3_api.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    "DEFAULT_PARSER_CLASSES": ("rest_framework.parsers.JSONParser",),
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",  # keep if you still want session auth
    ),
}

from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# Email configuration
# - Default to SMTP backend, but switch to console backend automatically during pytest runs
# - Provide safe defaults for host/port/user/pass so settings import never fails in CI
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')

# Use console backend when running tests to avoid real SMTP connections
if os.environ.get('PYTEST_CURRENT_TEST'):
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

EMAIL_HOST = config('EMAIL_HOST', default='localhost')
EMAIL_PORT = config('EMAIL_PORT', default=1025, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default=EMAIL_HOST_USER or 'noreply@example.com')

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'

STATIC_ROOT = BASE_DIR / 'staticfiles'

import os

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

# JSON-by-default configuration: treat all paths as API (JSON) unless explicitly allowed as HTML.
# You can extend these in environment-specific settings or override in local settings.
API_JSON_DEFAULT = True
HTML_EXEMPT_PATH_PREFIXES = (
    '/admin/', '/admin-django/', '/static/', '/media/', '/api/docs/',
)
WRITE_GATE_ENABLED = True
WRITE_GATE_EXACT_PATHS = (
    '/wcapi/save', '/wcapi/save/',
    '/wcapi/query', '/wcapi/query/',
    '/wcapi/delete', '/wcapi/delete/',
)
WRITE_GATE_PREFIXES = (
    '/wcapi/',
    '/api/auth/', '/api/token/', '/wcapi/login/', '/wcapi/signup/',
    '/admin/', '/admin-django/',
)
WRITE_GATE_ALLOWED_REGEX = (
    r'^/[a-z0-9_]+/\d+/?$',    # /<model>/<id>  (POST update, DELETE single)
    r'^/[a-z0-9_]+/?$',        # /<model>       (DELETE batch by body)
)

# WCAPI blessed models (present in your project)
WCAPI_BLESSED_MODELS = {
    "contact": "core.Contact",
    "domain": "communications.Domain",
    "document": "docs.Document",
    "linkage": "docs.Linkage",
    "action": "core.Action",
    "qa": "docs.QuestionAnswer",  # alias key for QA if present
    "tag": "docs.Tag",            # enable /tag/ endpoints
}

# Enable canonical routes for Tag if not already set
if 'WCAPI_BLESSED_MODELS' not in globals():
    WCAPI_BLESSED_MODELS = {}
WCAPI_BLESSED_MODELS.setdefault("tag", "docs.Tag")

# WCAPI per-model policies (opt-in, safe by default)
WCAPI_MODEL_POLICIES = {
    # Example: docs.Tag
    "tag": {
        "fields": {
            # Read allowlist
            "read": {
                "default": ["id", "name", "status", "purpose", "parent_id", "created_at", "updated_at"],
                "by_role": {
                    "admin": ["*"],  # '*' means all fields
                },
            },
            # Write allowlist
            "write": {
                "default": ["name", "status", "purpose", "parent_id"],
                "by_role": {
                    "admin": ["*"],
                },
            },
        },
        # Related data to embed in GET responses
        "relations": {
            # Single FK
            "parent": {"type": "fk", "fields": ["id", "name", "status"]},
            # Reverse children, auto-discovered related_name if omitted
            "children": {"type": "reverse", "fields": ["id", "name", "status"], "limit": 100},
        },
        # Optional hooks (dotted paths to callables)
        "hooks": {
            "pre_save": "apps.docs.hooks.tag_pre_save",    # def fn(ctx) -> None
            "post_save": "apps.docs.hooks.tag_post_save",  # def fn(ctx) -> None
        },
    },
}

# Helper to enable policies only during tests or per-env
WCAPI_POLICIES_ENABLED = True

# Add this at the bottom
INTERNAL_IPS = [
    '127.0.0.1',
    'localhost',
]

# (Removed old MIGRATION_MODULES override that pointed to temporary squashed_migrations modules.)

CELERY_BROKER_URL = 'redis://localhost:6379/0'  # or use RabbitMQ if you prefer
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_WORKER_LOGLEVEL = 'WARNING'  # Reduce Celery worker log verbosity
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
    # Documentation/registry hygiene: refresh artifacts daily and remind every 3 days
    'refresh-model-registry-docs-daily': {
        'task': 'common.tasks.refresh_model_registry_docs',
        'schedule': 24 * 60 * 60,  # daily
        'options': {'expires': 23 * 60 * 60},
    },
    'docs-staleness-reminder-3d': {
        'task': 'common.tasks.docs_staleness_reminder',
        'schedule': 3 * 24 * 60 * 60,  # every 3 days
        'options': {'expires': 2 * 24 * 60 * 60},
    },
    # Cache management tasks
    'update-access-cache-5m': {
        'task': 'apps.core.tasks.cache_tasks.update_access_fields_cache',
        'schedule': 5 * 60,  # every 5 minutes
        'options': {'expires': 4 * 60},
    },
    'update-keywords-cache-10m': {
        'task': 'apps.core.tasks.cache_tasks.update_keyword_requirements_cache',
        'schedule': 10 * 60,  # every 10 minutes
        'options': {'expires': 9 * 60},
    },
    'update-registry-cache-daily': {
        'task': 'apps.core.tasks.cache_tasks.update_model_registry_cache',
        'schedule': 24 * 60 * 60,  # daily
        'options': {'expires': 23 * 60 * 60},
    },
    'update-constants-cache-30m': {
        'task': 'apps.core.tasks.cache_tasks.update_constants_cache',
        'schedule': 30 * 60,  # every 30 minutes
        'options': {'expires': 25 * 60},
    },
    # Drain pending inventory adjustments frequently (short task; self-limiting via limit arg)
    'inventory-pending-drain-1m': {
        'task': 'products.tasks.process_pending_inventory',
        'schedule': 60,  # every minute
        'options': {'expires': 55},
        # args can be configured in DB scheduler; use default limit in task for now
    },
    # Expire stale inventory reservations every minute (short TTL reclamation)
    'expire-inventory-reservations-1m': {
        'task': 'products.tasks.expire_inventory_reservations',
        'schedule': 60,
        'options': {'expires': 55},
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

# --- WCAPI config ---
WCAPI_OPEN_READ = os.getenv('WCAPI_OPEN_READ', '0') == '1'
WCAPI_JWT_ONLY = os.getenv('WCAPI_JWT_ONLY', '0') == '1'
WCAPI_OPT_IN_ONLY = True           # prod: only models explicitly enabled

def _env_list(name: str):
    raw = os.getenv(name, '')
    items = [s.strip() for s in raw.split(',') if s.strip()]
    return tuple(items) if items else None

#QQQ whitelist apps in production; 
# None means all apps allowed (if opt-in disabled)
WCAPI_WHITELIST_APPS = _env_list('WCAPI_WHITELIST_APPS')  # e.g., "transactions,accounts"
WCAPI_ENFORCE_WRITES = True        # all writes via wcapi/save in views/tests/clients

# --- Test Environment Overrides (Celery eager, in‑memory broker) ---
import os as _os  # local alias to avoid shadowing
if _os.environ.get('PYTEST_CURRENT_TEST'):
    # Execute Celery tasks synchronously to prevent broker dependency in tests
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
    CELERY_BROKER_URL = 'memory://'
    CELERY_RESULT_BACKEND = 'cache+memory://'

    # Relax wcapi gating in tests so any model can be fetched via /<model>/ routes
    WCAPI_OPT_IN_ONLY = False
    # Leave WCAPI_WHITELIST_APPS as-is (from env) instead of redundantly setting None
    # WCAPI_WHITELIST_APPS = None

# Force Celery to use solo pool to avoid fork issues on macOS
CELERY_WORKER_POOL = 'solo'

# Ensure mandatory constants exist when running development server
if DEBUG and not os.environ.get('PYTEST_CURRENT_TEST') and 'runserver' in ' '.join(sys.argv) and os.environ.get('RUN_MAIN') == 'true':
    try:
        # Import Django settings to ensure apps are loaded
        import django
        from django.conf import settings as django_settings
        if not django_settings.configured:
            django.setup()

        from apps.core.constants.mandatory_constants import ensure_mandatory_constants_exist
        result = ensure_mandatory_constants_exist(verbose=False)  # Less verbose for runserver
        print(f"[INIT] Constants ready: {result['total_categories']} categories, {result['total_constants']} constants")
    except Exception as e:
        print(f"[INIT] Warning: Failed to initialize mandatory constants: {e}")

# Auto-start Celery worker when running Django development server
if DEBUG and not os.environ.get('PYTEST_CURRENT_TEST') and 'runserver' in ' '.join(sys.argv) and os.environ.get('RUN_MAIN') == 'true':
    import subprocess
    import atexit
    import signal
    import threading

    # Use a more robust check to prevent multiple starts
    _celery_started_flag = os.path.join(BASE_DIR, '.celery_started')
    _should_start_celery = True

    if os.path.exists(_celery_started_flag):
        try:
            with open(_celery_started_flag, 'r') as f:
                _stored_pid = int(f.read().strip())
            # Check if the stored PID is still running and is a celery process
            if _stored_pid > 0:
                try:
                    os.kill(_stored_pid, 0)  # Signal 0 just checks if process exists
                    # Additional check: verify it's actually a celery process
                    result = subprocess.run(['ps', '-p', str(_stored_pid), '-o', 'comm='], capture_output=True, text=True)
                    if result.returncode == 0 and 'celery' in result.stdout.lower():
                        _should_start_celery = False
                        print("Celery worker already running (PID: %s)" % _stored_pid)
                    else:
                        # Process exists but not celery, remove stale flag
                        os.remove(_celery_started_flag)
                        print("Removed stale Celery flag file (PID %s not a celery process)" % _stored_pid)
                except OSError:
                    # Process is dead, remove stale flag
                    os.remove(_celery_started_flag)
                    print("Removed stale Celery flag file (PID %s not running)" % _stored_pid)
        except (ValueError, IOError):
            # Invalid flag file, remove it
            os.remove(_celery_started_flag)

    if _should_start_celery:
        try:
            with open(_celery_started_flag, 'w') as f:
                f.write(str(os.getpid()))

            _celery_process = None

            def _start_celery_worker():
                global _celery_process
                try:
                    # Start Celery worker in background
                    _celery_process = subprocess.Popen(
                        ['celery', '-A', 'celery_app', 'worker'],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        cwd=os.path.dirname(os.path.dirname(__file__))
                    )
                    print("Celery worker started automatically (PID: %s)" % _celery_process.pid)
                except Exception as e:
                    print("Failed to start Celery worker: %s" % e)

            def _stop_celery_worker():
                global _celery_process
                if _celery_process:
                    try:
                        _celery_process.terminate()
                        _celery_process.wait(timeout=5)
                        print("Celery worker stopped")
                    except subprocess.TimeoutExpired:
                        _celery_process.kill()
                        print("Celery worker killed")
                # Clean up flag file
                try:
                    os.remove(_celery_started_flag)
                except:
                    pass

            # Register cleanup function
            atexit.register(_stop_celery_worker)

            # Start Celery worker in a separate thread
            threading.Thread(target=_start_celery_worker, daemon=True).start()

        except Exception as e:
            print("Failed to initialize Celery worker: %s" % e)

# Disable test DB serialization to avoid querying unmanaged/legacy tables
try:
    DATABASES["default"].setdefault("TEST", {})
    DATABASES["default"]["TEST"]["SERIALIZE"] = False
except Exception:
    pass