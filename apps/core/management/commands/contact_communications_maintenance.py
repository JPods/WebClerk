from django.core.management.base import BaseCommand

from apps.core.services.contact_communications_maintenance import maintain_contact_communications


class Command(BaseCommand):
    help = "Repair/create contact communication links across FK and refs for contact/email/phone/domain/address."

    def add_arguments(self, parser):
        parser.add_argument("--contact-id", type=int, help="Run against one contact by primary key.")
        parser.add_argument("--limit", type=int, help="Maximum contacts to process.")
        parser.add_argument("--dry-run", action="store_true", help="Compute changes without writing updates.")
        parser.add_argument(
            "--allow-reassign-owned",
            action="store_true",
            help="Allow claiming communication rows currently owned by a different contact.",
        )
        parser.add_argument(
            "--no-repair-dangling",
            action="store_true",
            help="Skip repair of communication records that have no contact FK at all.",
        )
        parser.add_argument(
            "--no-alice",
            action="store_true",
            help="Skip emitting Alice pattern-watch and summary notes.",
        )

    def handle(self, *args, **options):
        summary = maintain_contact_communications(
            contact_id=options.get("contact_id"),
            limit=options.get("limit"),
            dry_run=bool(options.get("dry_run")),
            allow_reassign_owned=bool(options.get("allow_reassign_owned")),
            repair_dangling=not bool(options.get("no_repair_dangling")),
            emit_alice=not bool(options.get("no_alice")),
        )

        if options.get("dry_run"):
            self.stdout.write(self.style.WARNING("DRY RUN - no data changed"))

        self.stdout.write(self.style.SUCCESS("contact_communications_maintenance complete"))
        for key, value in summary.items():
            self.stdout.write(f"  {key}: {value}")
