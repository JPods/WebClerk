"""Clean up contact data: placeholder emails → NULL, ida → str(id).

Reports data health: counts of contacts with null email and null phone.
"""
from django.db.models import F, CharField, Value
from django.db.models.functions import Cast
from django.core.management.base import BaseCommand
from apps.core.models import Contact


class Command(BaseCommand):
    help = "Clean contact data (placeholder emails, ida) and report health"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Show what would change without changing it")
        parser.add_argument("--health", action="store_true", help="Only report data health counts")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        health_only = options["health"]

        if not health_only:
            # --- Placeholder emails ---
            placeholders = Contact.objects.filter(email__contains="placeholder.local")
            count = placeholders.count()
            if count == 0:
                self.stdout.write("No placeholder emails found.")
            elif dry_run:
                self.stdout.write(f"Would null out {count} placeholder emails")
            else:
                updated = placeholders.update(email=None, domain=None)
                self.stdout.write(f"Cleaned {updated} placeholder emails → NULL")

            # --- ida = str(id) ---
            mismatched = Contact.objects.annotate(
                id_str=Cast('id', CharField())
            ).exclude(ida=F('id_str'))
            ida_count = mismatched.count()
            if ida_count == 0:
                self.stdout.write("All ida values already match str(id).")
            elif dry_run:
                self.stdout.write(f"Would set ida=str(id) on {ida_count} contacts")
                for c in mismatched[:10]:
                    self.stdout.write(f"  id={c.id}  ida={c.ida} → {c.id}")
                if ida_count > 10:
                    self.stdout.write(f"  ... and {ida_count - 10} more")
            else:
                updated = Contact.objects.annotate(
                    id_str=Cast('id', CharField())
                ).exclude(ida=F('id_str')).update(ida=Cast('id', CharField()))
                self.stdout.write(f"Set ida=str(id) on {updated} contacts")

        # Data health report
        total = Contact.objects.count()
        null_email = Contact.objects.filter(email__isnull=True).count()
        null_phone = Contact.objects.filter(phone__isnull=True).count()
        null_both = Contact.objects.filter(email__isnull=True, phone__isnull=True).count()
        has_email_fk = Contact.objects.filter(email_id__isnull=False).count()
        has_phone_fk = Contact.objects.filter(phone_id__isnull=False).count()
        ida_aligned = Contact.objects.annotate(
            id_str=Cast('id', CharField())
        ).filter(ida=F('id_str')).count()

        self.stdout.write(f"\n--- Contact Data Health ---")
        self.stdout.write(f"Total contacts:        {total}")
        self.stdout.write(f"Email NULL:            {null_email}  ({self._pct(null_email, total)})")
        self.stdout.write(f"Phone NULL:            {null_phone}  ({self._pct(null_phone, total)})")
        self.stdout.write(f"Both NULL:             {null_both}  ({self._pct(null_both, total)})")
        self.stdout.write(f"Email FK linked:       {has_email_fk}")
        self.stdout.write(f"Phone FK linked:       {has_phone_fk}")
        self.stdout.write(f"ida = str(id):         {ida_aligned}  ({self._pct(ida_aligned, total)})")

    @staticmethod
    def _pct(n, total):
        return f"{n / total * 100:.1f}%" if total else "0%"
