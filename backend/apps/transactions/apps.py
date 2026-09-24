from django.apps import AppConfig

class TransactionsConfig(AppConfig):
    name = "apps.transactions"
    label = "transactions"

    def ready(self):
        # Import signal handlers only after apps are loaded
        from . import signals  # noqa: F401

        # The documents' code hooks on every verb (behaviours.py).
        from .behaviours import register_documents
        register_documents()

        # The cash commands: pay, refund, receive (services/cash/cash_commands.py).
        from .services.cash import cash_commands
        cash_commands.register()

        # Hard delete only: a journalized or reconciled record refuses deletion.
        # Connected first, so it refuses before the cash door reverses anything.
        from .models import hard_delete
        hard_delete.connect()

        # The cash door: a delete reverses its applications, and a cash Pending is
        # permanent (services/cash/cash_door.py).
        from .services.cash import cash_door
        cash_door.connect()
