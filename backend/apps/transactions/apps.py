from django.apps import AppConfig

class TransactionsConfig(AppConfig):
    name = "apps.transactions"
    label = "transactions"

    def ready(self):
        # Import signal handlers only after apps are loaded
        from . import signals  # noqa: F401
        from .models import hard_delete
        hard_delete.connect()