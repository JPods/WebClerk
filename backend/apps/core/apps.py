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
        # Lets the sites in INQUIRY_SITES call /wcapi/_inquiry/* cross-origin (and nothing else)
        from .views import inquiry_view  # noqa: F401

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


        # Every installation has a WCHQ connection record. It may be unused, or set
        # to manual transport, but a missing record is a fault — hook review and
        # support escalation both travel that road.
        try:
            from django.core.checks import Warning as CheckWarning, register

            @register('wchq')
            def _wchq_connection_exists(app_configs, **kwargs):
                from django.db import connection as db
                try:
                    if 'connections' not in db.introspection.table_names():
                        return []
                    from apps.sync.models.connection import Connection
                    if Connection.objects.filter(ida='wchq-conn-upstream', is_active=True).exists():
                        return []
                except Exception:
                    return []
                return [CheckWarning(
                    'No wchq-conn-upstream Connection record.',
                    hint='Run: python manage.py seed_connections --only wchq-conn-upstream',
                    id='wchq.W001',
                )]
        except Exception:
            pass
