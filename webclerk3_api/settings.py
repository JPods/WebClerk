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
    'http://85.31.234.194',
)
CORS_ALLOW_CREDENTIALS = True

# Required by Django when making cookie-authenticated requests from the Vite origin.
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://85.31.234.194',
]

INSTALLED_APPS = [
    'apps.accounts',
    'apps.communications',
    'apps.core',
    'apps.docs',
    'apps.orgs',
    'apps.products',
    # 'apps.scheduler',  # TODO: Create scheduler app
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
    'drf_spectacular_sidecar',
]

_running_django_test = 'test' in sys.argv
_disable_contrib_migrations = config('DISABLE_CONTRIB_MIGRATIONS', default=False, cast=bool)
if _running_django_test or _disable_contrib_migrations:
    MIGRATION_MODULES = {
        'admin': None,
        'auth': None,
        'contenttypes': None,
        'sessions': None,
    }

MIDDLEWARE = [
    "apps.core.utils.middleware.JSONOnlyMiddleware",
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

# DB_MODE toggle: "remote" or "local" - set in .env to switch databases easily
_db_mode = config('DB_MODE', default='remote').lower()

if _force_pg or (not _explicit_sqlite and not _running_pytest and not _force_pg):
    # Postgres path (default)
    if _db_mode == 'local':
        # Local database for debugging
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': config('LOCAL_DATABASE_NAME', default='commerce_expert'),
                'USER': config('LOCAL_DATABASE_USER', default='williamjames'),
                'PASSWORD': config('LOCAL_DATABASE_PASS', default=''),
                'HOST': config('LOCAL_DATABASE_HOST', default='localhost'),
                'PORT': config('LOCAL_DATABASE_PORT', default='5432'),
                'ATOMIC_REQUESTS': False,
            }
        }
        print(f'\n[webClerk3] Data Set: {config("DATA_SET_ID", default="UNKNOWN")} - {config("DATA_SET_NAME", default="Unknown")}')
        print(f'[webClerk3] Database: LOCAL @ {DATABASES["default"]["HOST"]}:{DATABASES["default"]["PORT"]}/{DATABASES["default"]["NAME"]}\n')
    else:
        # Remote database for team collaboration (default)
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': config('REMOTE_DATABASE_NAME', default=config('DATABASE_NAME', default='commerce_expert')),
                'USER': config('REMOTE_DATABASE_USER', default=config('DATABASE_USER', default='postgres')),
                'PASSWORD': config('REMOTE_DATABASE_PASS', default=config('DATABASE_PASS', default='')),
                'HOST': config('REMOTE_DATABASE_HOST', default=config('DATABASE_HOST', default='localhost')),
                'PORT': config('REMOTE_DATABASE_PORT', default=config('DATABASE_PORT', default='5432')),
                'ATOMIC_REQUESTS': False,
            }
        }
        print(f'\n[webClerk3] Data Set: {config("DATA_SET_ID", default="UNKNOWN")} - {config("DATA_SET_NAME", default="Unknown")}')
        print(f'[webClerk3] Database: REMOTE @ {DATABASES["default"]["HOST"]}:{DATABASES["default"]["PORT"]}/{DATABASES["default"]["NAME"]}\n')
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
        "apps.core.auth.RoleValidatingJWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "user": "120/minute",
        "anon": "30/minute",
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# Spectacular (OpenAPI) Configuration
SPECTACULAR_SETTINGS = {
    # === Basic metadata ===
    'TITLE': 'WebClerk3 API',
    'DESCRIPTION': 'REST API for WebClerk3',
    'VERSION': '1.0.0',
    'OPENAPI_VERSION': '3.0.3',
    'SERVE_INCLUDE_SCHEMA': False,
    'SERVE_URLCONF': 'webclerk3_api.urls',
    'SWAGGER_UI_DIST': 'SIDECAR',
    'SWAGGER_UI_FAVICON_HREF': 'SIDECAR',

    # === Generation hooks ===
    # 'PREPROCESSING_HOOKS': ['common.schema_hooks.whitelist_preprocessor'],
    'SERVE_PERMISSIONS': ['rest_framework.permissions.AllowAny'],

    # === Authentication (global) ===
    'SECURITY': [{'BearerAuth': []}, {'CookieAuth': []}],
    'COMPONENTS': {
        'securitySchemes': {
            'BearerAuth': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
                'description': (
                    'JWT authorization header using the Bearer scheme.\n\n'
                    'Example: `Authorization: Bearer <your-jwt-token>`'
                ),
            }
        },
    },
}
CSP_DEFAULT_SRC = ("'self'", "cdn.jsdelivr.net")
CSP_SCRIPT_SRC  = ("'self'", "cdn.jsdelivr.net")
CSP_STYLE_SRC   = ("'self'", "'unsafe-inline'", "cdn.jsdelivr.net")
CSP_IMG_SRC     = ("'self'", "data:", "cdn.jsdelivr.net")


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

# Email Notification Settings
COMPANY_NAME = config('COMPANY_NAME', default='WebClerk3')

# Transaction Email Notifications
# Enable/disable specific email notifications
EMAIL_NOTIFICATIONS_ENABLED = config('EMAIL_NOTIFICATIONS_ENABLED', default=True, cast=bool)
EMAIL_PROPOSAL_SUBMITTED_ENABLED = config('EMAIL_PROPOSAL_SUBMITTED_ENABLED', default=True, cast=bool)
EMAIL_ORDER_CREATED_ENABLED = config('EMAIL_ORDER_CREATED_ENABLED', default=True, cast=bool)
EMAIL_INVOICE_SENT_ENABLED = config('EMAIL_INVOICE_SENT_ENABLED', default=True, cast=bool)
EMAIL_PAYMENT_RECEIVED_ENABLED = config('EMAIL_PAYMENT_RECEIVED_ENABLED', default=True, cast=bool)

# Additional recipient emails for notifications (comma-separated)
EMAIL_ADDITIONAL_RECIPIENTS = config('EMAIL_ADDITIONAL_RECIPIENTS', default='')

# BCC all transaction emails to admin
EMAIL_BCC_ADMIN = config('EMAIL_BCC_ADMIN', default=False, cast=bool)
EMAIL_ADMIN_RECIPIENT = config('EMAIL_ADMIN_RECIPIENT', default='')

LANGUAGE_CODE = 'en-us'
TIME_ZONE = config('TIME_ZONE', default='UTC')
USE_I18N = True
USE_TZ = config('USE_TZ', default=True, cast=bool)

STATIC_URL = 'static/'

STATIC_ROOT = BASE_DIR / 'staticfiles'

# Additional directories for static files (beyond app static folders)
STATICFILES_DIRS = [
    BASE_DIR / 'static',  # Includes /static/images/ for uploaded content
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
        'console': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# JSON-by-default configuration: treat all paths as API (JSON) unless explicitly allowed as HTML.
# You can extend these in environment-specific settings or override in local settings.
API_JSON_DEFAULT = True
HTML_EXEMPT_PATH_PREFIXES = (
    '/admin/', '/admin-django/', '/static/', '/media/', '/api/swagger/', '/api/schema/','/api/redoc/',
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
    # Core models
    "contact": "core.Contact",
    "action": "core.Action",
    "audit": "core.Audit",
    "notification": "core.Notification",
    "pending": "core.Pending",
    "report": "core.Report",
    "setting": "core.Setting",
    "template": "core.Template",

    # Accounts models
    "currency": "accounts.Currency",
    "exchange_rate": "accounts.ExchangeRate",
    "exchange_transaction": "accounts.ExchangeTransaction",
    "gl_account": "accounts.GlAccount",
    "gl_journal": "accounts.GlJournal",
    "ledger": "accounts.Ledger",
    "tax_jurisdiction": "accounts.TaxJurisdiction",
    "term": "accounts.Term",

    # Communications models
    "domain": "communications.Domain",
    "email": "communications.Email",
    "location": "communications.Address",
    "phone": "communications.Phone",

    # Docs models
    "document": "docs.Document",
    "linkage": "docs.Linkage",
    "linkage_index": "docs.LinkageIndex",
    "question_answer": "docs.QuestionAnswer",
    "tag": "docs.Tag",

    # Products models
    "bill_of_material": "products.BillOfMaterial",
    "catalog": "products.Catalog",
    "flow": "products.Flow",
    "inventory_check": "products.InventoryCheck",
    "inventory_layer": "products.InventoryLayer",
    "inventory_reservation": "products.InventoryReservation",
    "item": "products.Item",
    "item_xref": "products.ItemXRef",
    "metrics": "products.InventoryMetricsSnapshot",
    "org_item": "products.OrgItem",
    "processor_runs": "products.InventoryAdjustmentProcessorRun",
    "serial": "products.Serial",
    "service": "products.Service",
    "specification": "products.Specification",
    "usage": "products.ItemUsage",
    "variant": "products.Variant",
    "warehouse": "products.Warehouse",

    # Support models
    "campaign": "support.Campaign",

    # Sync models
    "bundle": "sync.Bundle",
    "connection": "sync.Connection",

    # Orgs models
    "org": "orgs.OrgBase",
    "customer": "orgs.Customer",
    "vendor": "orgs.Vendor",
    "rep": "orgs.Rep",
    "employee": "orgs.Employee",
    "manufacturer": "orgs.Manufacturer",

    # Transaction models
    "payment": "transactions.Payment",
    "payment_method": "transactions.PaymentMethod",
    "payment_term": "transactions.PaymentTerm",
    "payment_application": "transactions.PaymentApplication",
    "transaction": "transactions.Order",
    "order": "transactions.Order",
    "order_line": "transactions.OrderLine",
    "invoice": "transactions.Invoice",
    "invoice_line": "transactions.InvoiceLine",
    "purchase_order": "transactions.PurchaseOrder",
    "purchase_order_line": "transactions.PurchaseOrderLine",
    "purchase_receipt": "transactions.PurchaseReceipt",
    "work_order": "transactions.WorkOrder",
    "work_order_line": "transactions.WorkOrderLine",
    "proposal": "transactions.Proposal",
    "proposal_line": "transactions.ProposalLine",
    "requisition": "transactions.Requisition",
    "requisition_line": "transactions.RequisitionLine",
    "project": "transactions.Project",
    "project_links": "transactions.ProjectLinks",
}

# WCAPI per-model policies (opt-in, safe by default)
# ─────────────────────────────────────────────────────────────────────
# Each entry maps a model key (lowercase) to read/write field lists.
# `by_role` is checked first-match-wins in role order
#   (admin → employee → <group names> → user).
# A value of ["*"] means unrestricted.
# Models not listed here get NO write filtering (unrestricted).
# ─────────────────────────────────────────────────────────────────────

# Shared field lists to avoid repetition
_TX_HEADER_WRITE_EMPLOYEE = [
    "status", "priority", "price_level",
    "customer_id", "manufacturer_id", "vendor_id",
    "contact_id", "attention", "address_full", "email", "phone",
    "terms", "terms_fk_id",
    "conditions_id", "conditions_description",
    "cost", "sell", "totals", "finance", "flow", "source",
    "parent_id", "parent_model",
    "comments",
]

_TX_HEADER_WRITE_USER = [
    "status", "comments",
]

_TX_LINE_WRITE_EMPLOYEE = [
    "status", "price_level",
    "item_fk_id", "item",
    "quantity", "cost", "tax", "physical", "price",
    "comments",
]

_TX_LINE_WRITE_USER = [
    "status", "quantity", "comments",
]

WCAPI_MODEL_POLICIES = {
    # ── Core ──────────────────────────────────────────────────────────
    "contact": {
        "fields": {
            "read": {
                "default": [
                    "id", "email", "name_first", "name_last", "name_middle",
                    "name_prefix", "name_suffix", "company", "title",
                    "department", "customer_id", "vendor_id", "role",
                    "is_active", "dt_joined",
                ],
                "by_role": {
                    "admin": ["*"],
                },
            },
            "write": {
                "default": [
                    "email", "name_first", "name_last", "name_middle",
                    "name_prefix", "name_suffix", "company", "title",
                    "department", "customer_id", "vendor_id", "comment",
                ],
                "by_role": {
                    "admin": ["*"],
                },
            },
        },
    },

    # ── Orgs ──────────────────────────────────────────────────────────
    "orgbase": {
        "fields": {
            "write": {
                "default": [],
                "by_role": {
                    "admin": ["*"],
                    "employee": [
                        "display_name", "org_type", "status",
                        "contact_id", "attention",
                        "address_id", "address_full",
                        "email", "email_id", "phone", "phone_id",
                        "domain", "domain_id",
                        "price_level", "terms", "terms_fk_id",
                        "financial", "data", "gl_accounts",
                        "comments",
                    ],
                },
            },
        },
    },

    # ── Products ──────────────────────────────────────────────────────
    "item": {
        "fields": {
            "write": {
                "default": [],
                "by_role": {
                    "admin": ["*"],
                    "employee": [
                        "name", "sku", "qr_code", "kind", "uom", "base_uom",
                        "description", "gls", "flags",
                        "price", "cost", "tax_code",
                        "specification_id", "catalog", "quantity",
                        "comments",
                    ],
                },
            },
        },
    },

    # ── Transactions — Headers ────────────────────────────────────────
    "order": {
        "fields": {
            "write": {
                "default": _TX_HEADER_WRITE_USER,
                "by_role": {
                    "admin": ["*"],
                    "employee": _TX_HEADER_WRITE_EMPLOYEE,
                },
            },
        },
    },
    "invoice": {
        "fields": {
            "write": {
                "default": _TX_HEADER_WRITE_USER,
                "by_role": {
                    "admin": ["*"],
                    "employee": _TX_HEADER_WRITE_EMPLOYEE,
                },
            },
        },
    },
    "proposal": {
        "fields": {
            "write": {
                "default": _TX_HEADER_WRITE_USER,
                "by_role": {
                    "admin": ["*"],
                    "employee": _TX_HEADER_WRITE_EMPLOYEE,
                },
            },
        },
    },
    "purchase": {
        "fields": {
            "write": {
                "default": _TX_HEADER_WRITE_USER,
                "by_role": {
                    "admin": ["*"],
                    "employee": _TX_HEADER_WRITE_EMPLOYEE,
                },
            },
        },
    },
    "purchaseorder": {
        "fields": {
            "write": {
                "default": _TX_HEADER_WRITE_USER,
                "by_role": {
                    "admin": ["*"],
                    "employee": _TX_HEADER_WRITE_EMPLOYEE,
                },
            },
        },
    },

    # ── Transactions — Lines ──────────────────────────────────────────
    "orderline": {
        "fields": {
            "write": {
                "default": _TX_LINE_WRITE_USER,
                "by_role": {
                    "admin": ["*"],
                    "employee": _TX_LINE_WRITE_EMPLOYEE + ["order_id"],
                },
            },
        },
    },
    "orderline": {
        "fields": {
            "write": {
                "default": _TX_LINE_WRITE_USER,
                "by_role": {
                    "admin": ["*"],
                    "employee": _TX_LINE_WRITE_EMPLOYEE + ["order_id"],
                },
            },
        },
    },
    "invoiceline": {
        "fields": {
            "write": {
                "default": _TX_LINE_WRITE_USER,
                "by_role": {
                    "admin": ["*"],
                    "employee": _TX_LINE_WRITE_EMPLOYEE + ["invoice_id"],
                },
            },
        },
    },
    "proposalline": {
        "fields": {
            "write": {
                "default": _TX_LINE_WRITE_USER,
                "by_role": {
                    "admin": ["*"],
                    "employee": _TX_LINE_WRITE_EMPLOYEE + ["proposal_id"],
                },
            },
        },
    },
    "purchaseline": {
        "fields": {
            "write": {
                "default": _TX_LINE_WRITE_USER,
                "by_role": {
                    "admin": ["*"],
                    "employee": _TX_LINE_WRITE_EMPLOYEE + ["purchase_id"],
                },
            },
        },
    },
    "purchaseorderline": {
        "fields": {
            "write": {
                "default": _TX_LINE_WRITE_USER,
                "by_role": {
                    "admin": ["*"],
                    "employee": _TX_LINE_WRITE_EMPLOYEE + ["purchase_id"],
                },
            },
        },
    },

    # ── Payments ──────────────────────────────────────────────────────
    "payment": {
        "fields": {
            "write": {
                "default": [],
                "by_role": {
                    "admin": ["*"],
                    "employee": [
                        "status", "contact_id", "customer_id",
                        "amount", "payment_method_id", "reference",
                        "comments",
                    ],
                },
            },
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

# --- Test Environment Overrides ---
import os as _os  # local alias to avoid shadowing
if _os.environ.get('PYTEST_CURRENT_TEST'):
    # Relax wcapi gating in tests so any model can be fetched via /<model>/ routes
    WCAPI_OPT_IN_ONLY = False
    # Leave WCAPI_WHITELIST_APPS as-is (from env) instead of redundantly setting None
    # WCAPI_WHITELIST_APPS = None

# Disable test DB serialization to avoid querying unmanaged/legacy tables
try:
    DATABASES["default"].setdefault("TEST", {})
    DATABASES["default"]["TEST"]["SERIALIZE"] = False
    DATABASES["default"]["TEST"]["NAME"] = 'test_commerce_expert_new'
except Exception:
    pass

# Payment Gateway Settings
STRIPE_PUBLISHABLE_KEY = config('STRIPE_PUBLISHABLE_KEY', default='')
STRIPE_SECRET_KEY = config('STRIPE_SECRET_KEY', default='')
STRIPE_WEBHOOK_SECRET = config('STRIPE_WEBHOOK_SECRET', default='')

PAYPAL_CLIENT_ID = config('PAYPAL_CLIENT_ID', default='')
PAYPAL_CLIENT_SECRET = config('PAYPAL_CLIENT_SECRET', default='')
PAYPAL_ENVIRONMENT = config('PAYPAL_ENVIRONMENT', default='sandbox')  # 'sandbox' or 'live'
PAYPAL_WEBHOOK_ID = config('PAYPAL_WEBHOOK_ID', default='')

# Payment Processing Settings
PAYMENT_CURRENCY = config('PAYMENT_CURRENCY', default='USD')
PAYMENT_SUCCESS_URL = config('PAYMENT_SUCCESS_URL', default='http://localhost:5173/payment/success')
PAYMENT_CANCEL_URL = config('PAYMENT_CANCEL_URL', default='http://localhost:5173/payment/cancel')
PAYMENT_WEBHOOK_URL = config('PAYMENT_WEBHOOK_URL', default='http://localhost:8000/api/payments/webhook/')

# =============================================================================
# Celery Configuration  (Redis broker)
# =============================================================================
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')

CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60          # 30 minutes hard limit
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60     # 25 minutes soft limit

# Beat schedule — periodic background tasks
from celery.schedules import crontab  # noqa: E402

CELERY_BEAT_SCHEDULE = {
    # ── Inventory pending drain (adaptive, self-re-scheduling) ──────
    # Runs every 30 s; the task adjusts its own delay based on workload.
    'inventory-pending-drain': {
        'task': 'apps.products.tasks.process_pending_inventory_adaptive_task',
        'schedule': 30.0,                       # seconds between kicks
        'kwargs': {'limit': 200},
    },

    # ── Search keywords refresh ─────────────────────────────────────
    'refresh-keywords-every-15-min': {
        'task': 'apps.support.scheduler.tasks.task_refresh_keywords',
        'schedule': crontab(minute='*/15'),
        'kwargs': {'limit': 500, 'batch_size': 200},
    },

    # ── Relationship counts ─────────────────────────────────────────
    'recompute-relationship-counts-hourly': {
        'task': 'apps.support.scheduler.tasks.task_recompute_relationship_counts',
        'schedule': crontab(minute=0),
        'kwargs': {'limit': 5000, 'batch_size': 500},
    },

    # ── Model defaults (daily 2 AM) ────────────────────────────────
    'ensure-model-defaults-daily': {
        'task': 'apps.support.scheduler.tasks.task_ensure_model_defaults',
        'schedule': crontab(hour=2, minute=0),
    },

    # ── Data backup (daily 3 AM) ────────────────────────────────────
    'export-data-backup-daily': {
        'task': 'apps.support.scheduler.tasks.task_export_data',
        'schedule': crontab(hour=3, minute=0),
    },

    # ── Registry docs (daily 5 AM) ─────────────────────────────────
    'refresh-model-registry-docs-daily': {
        'task': 'apps.support.scheduler.tasks.task_refresh_model_registry_docs',
        'schedule': crontab(hour=5, minute=0),
    },

    # ── Stats normalization (weekly Sun 4 AM) ───────────────────────
    'recompute-basic-stats-weekly': {
        'task': 'apps.support.scheduler.tasks.task_recompute_basic_stats',
        'schedule': crontab(hour=4, minute=0, day_of_week='sunday'),
        'kwargs': {'limit': 50000, 'batch_size': 500},
    },
}

# --- Inventory Pending Processing ---
# Controls how often the background processor checks for unprocessed inventory pending records
INVENTORY_PENDING_PROCESS_DELAY = int(config('INVENTORY_PENDING_PROCESS_DELAY', default=5))  # seconds
INVENTORY_PENDING_BATCH_SIZE = int(config('INVENTORY_PENDING_BATCH_SIZE', default=100))  # records per batch
INVENTORY_PENDING_AUTO_PROCESS = config('INVENTORY_PENDING_AUTO_PROCESS', default=False, cast=bool)  # enable in prod
