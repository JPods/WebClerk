from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "apps.core"
    label = "core"

    def ready(self):
        # Initialize WCAPI registry (safe, no database calls)
        try:
            from apps.core.utils import registry
            registry.refresh_from_settings()
        except Exception:
            pass

        # Import signal handlers to auto-populate cache after Django is ready
        # This avoids the Django warning about database access during app initialization
        try:
            from . import init_handlers  # noqa: F401
        except Exception:
            pass

        # Auto-wire AuditLog to capture field-level changes on save
        try:
            from apps.core.signals.audit_signals import register_audit_signals
            register_audit_signals()
        except Exception:
            pass

