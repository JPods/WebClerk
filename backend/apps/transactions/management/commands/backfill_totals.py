"""
Management command to recalculate totals for transaction records with empty or
missing totals JSON envelopes.

Usage:
    python manage.py backfill_totals
    python manage.py backfill_totals --dry-run
    python manage.py backfill_totals --model invoice
    python manage.py backfill_totals --all
    python manage.py backfill_totals --all --model purchase --dry-run
"""
from django.core.management.base import BaseCommand
from django.db.models import Q
from apps.transactions.models import (
    Invoice, Order, Proposal, Purchase, WorkOrder
)


MODEL_MAP = {
    'invoice': Invoice,
    'order': Order,
    'proposal': Proposal,
    'purchase': Purchase,
    'workorder': WorkOrder,
}


class Command(BaseCommand):
    help = 'Recalculate totals for transactions with empty or missing totals envelopes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without saving',
        )
        parser.add_argument(
            '--model',
            type=str,
            choices=list(MODEL_MAP.keys()),
            help='Limit to a specific model (e.g. --model invoice)',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Recompute ALL records, not just ones with empty totals',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        process_all = options['all']

        if options['model']:
            models = [MODEL_MAP[options['model']]]
        else:
            models = [Invoice, Order, Proposal, Purchase, WorkOrder]

        total_backfilled = 0

        for model in models:
            model_name = model.__name__
            self.stdout.write(f"\nProcessing {model_name}...")

            if process_all:
                qs = model.objects.all()
            else:
                qs = model.objects.filter(
                    Q(totals__isnull=True)
                    | Q(totals={})
                    | Q(totals__total=0)
                )

            count = 0
            for record in qs:
                record.update_sell_cost_totals(persist=not dry_run)
                # Re-read totals after recompute (persist=False still updates in memory)
                total_val = (record.totals or {}).get('total', 0)
                prefix = "Would backfill" if dry_run else "Backfilled"
                self.stdout.write(f"  {prefix} {model_name} #{record.id} -- total={total_val}")
                count += 1

            total_backfilled += count
            if count == 0:
                self.stdout.write(f"  No records to process for {model_name}")

        self.stdout.write("")
        model_label = options['model'] or 'all models'
        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"DRY RUN: {total_backfilled} records would be backfilled across {model_label}"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"{total_backfilled} records backfilled across {model_label}"
            ))
