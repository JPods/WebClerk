from django.core.management.base import BaseCommand

from apps.orgs.services.customer_transaction_maintenance import maintain_customer_transaction_links


class Command(BaseCommand):
    help = "Reconcile customer links between transaction records and refs.links, with optional random assignment for missing customer_id."

    def add_arguments(self, parser):
        parser.add_argument(
            "--target-customers",
            type=int,
            nargs="+",
            default=[82, 84, 86],
            help="Customer ids used for random assignment when customer_id is missing.",
        )
        parser.add_argument(
            "--no-assign-missing",
            action="store_true",
            help="Do not assign random customer_id for records missing customer links.",
        )
        parser.add_argument("--dry-run", action="store_true", help="Compute changes without saving.")

    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))
        assign_missing = not bool(options.get("no_assign_missing"))
        target_customers = list(options.get("target_customers") or [82, 84, 86])

        summary = maintain_customer_transaction_links(
            target_customer_ids=target_customers,
            assign_missing=assign_missing,
            dry_run=dry_run,
        )

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - no updates saved"))

        self.stdout.write(self.style.SUCCESS("customer_transaction_maintenance complete"))
        self.stdout.write(f"  models_scanned: {summary['models_scanned']}")
        self.stdout.write(f"  rows_missing_assigned: {summary['rows_missing_assigned']}")
        self.stdout.write(f"  rows_existing_customer: {summary['rows_existing_customer']}")
        self.stdout.write(f"  tx_refs_updated: {summary['tx_refs_updated']}")
        self.stdout.write(f"  customer_refs_updated: {summary['customer_refs_updated']}")

        for model_name, model_stats in summary.get("per_model", {}).items():
            self.stdout.write(
                f"  model={model_name} assigned_missing={model_stats['assigned_missing']} "
                f"existing_customer={model_stats['existing_customer']} "
                f"tx_refs_updated={model_stats['tx_refs_updated']} "
                f"customer_refs_updated={model_stats['customer_refs_updated']}"
            )
