from django.apps import AppConfig


class ProductsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.products'
    def ready(self):  # pragma: no cover
        # Import signals to wire up unlock processing
        try:
            from . import signals  # noqa: F401
        except Exception:
            pass
        # Ensure reservation model imported so admin/auto-discovery picks it up (no side-effects)
        try:  # pragma: no cover
            from .models import inventory_reservation  # noqa: F401
        except Exception:
            pass
