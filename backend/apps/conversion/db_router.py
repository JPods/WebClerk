"""
Database router — all conversion models go to alice_conversion database.

Every table Alice creates during data conversion lives here. The noise
stays out of commerce_expert. WC3 only sees the clean bundle that arrives
at /sync/receive/ after conversion is complete.
"""

CONVERSION_APP = 'conversion'


class ConversionRouter:
    """Route apps.conversion models to the alice_conversion database."""

    def db_for_read(self, model, **hints):
        if model._meta.app_label == CONVERSION_APP:
            return 'alice_conversion'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == CONVERSION_APP:
            return 'alice_conversion'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        # Conversion models can relate to each other but not to commerce_expert
        if obj1._meta.app_label == CONVERSION_APP or obj2._meta.app_label == CONVERSION_APP:
            return obj1._meta.app_label == obj2._meta.app_label
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == CONVERSION_APP:
            return db == 'alice_conversion'
        if db == 'alice_conversion':
            return False
        return None
