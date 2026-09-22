from django.apps import AppConfig

class TransactionsConfig(AppConfig):
    name = "apps.transactions"
    label = "transactions"

    def ready(self):
        # Import signal handlers only after apps are loaded
        from . import signals  # noqa: F401

        # Hard delete only: a journalized or reconciled record refuses deletion.
        # Connected first, so it refuses before the cash door reverses anything.
        from .models import hard_delete
        hard_delete.connect()

        # The cash door: a delete reverses its applications, and a cash Pending is
        # permanent (services/cash/cash_door.py).
        from .services.cash import cash_door
        cash_door.connect()
