"""Refresh Alice's aggregate collections from the database.

Corrects any drift from delta accumulation. Run nightly or on-demand.

Usage:
    python manage.py refresh_aggregates          # all models
    python manage.py refresh_aggregates invoice   # one model
"""
from django.core.management.base import BaseCommand
from apps.ai_assistant.services.aggregate_tracker import (
    refresh_aggregates, refresh_all, TRANSACTION_MODELS,
)


class Command(BaseCommand):
    help = 'Refresh Alice aggregate collections for dashboard Sum() queries'

    def add_arguments(self, parser):
        parser.add_argument(
            'model_name', nargs='?', default=None,
            help=f'Model to refresh ({", ".join(TRANSACTION_MODELS)}). Omit for all.',
        )

    def handle(self, *args, **options):
        model_name = options['model_name']

        if model_name:
            if model_name not in TRANSACTION_MODELS:
                self.stderr.write(f"Unknown model: {model_name}. Choose from: {', '.join(TRANSACTION_MODELS)}")
                return
            result = refresh_aggregates(model_name)
            self.stdout.write(
                f"{model_name}: total_sum={result['total_sum']:.2f} "
                f"balance_sum={result['balance_sum']:.2f} count={result['count']}"
            )
        else:
            results = refresh_all()
            for name, result in results.items():
                self.stdout.write(
                    f"{name}: total_sum={result['total_sum']:.2f} "
                    f"balance_sum={result['balance_sum']:.2f} count={result['count']}"
                )
            self.stdout.write(self.style.SUCCESS(f'Refreshed {len(results)} models'))
