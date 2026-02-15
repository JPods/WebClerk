"""Populate FK relationships between Contacts and OrgBase records.

Matches contacts to orgs by:
  1. Exact display_name match to contact's company field
  2. Exact display_name match to contact's "name_first name_last"
  3. Existing contacts JSONB aspect entries with contact IDs

For each match, sets:
  - Contact.<org_type> FK → OrgBase (e.g. contact.customer = org)
  - OrgBase.contact_id FK → Contact (primary contact for the org)

Usage:
  python manage.py populate_org_contacts             # dry-run (default)
  python manage.py populate_org_contacts --apply      # actually write to DB
  python manage.py populate_org_contacts --clear      # clear all FK links first
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import Contact
from apps.orgs.models import OrgBase


class Command(BaseCommand):
    help = "Populate FK relationships between Contact and OrgBase records by name matching."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            default=False,
            help="Actually write changes to the database (default is dry-run).",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            default=False,
            help="Clear all existing Contact↔Org FK links before populating.",
        )

    def handle(self, *args, **options):
        apply = options["apply"]
        clear = options["clear"]
        mode = "APPLY" if apply else "DRY-RUN"
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"  populate_org_contacts  [{mode}]")
        self.stdout.write(f"{'='*60}\n")

        if clear and apply:
            self._clear_links()

        contacts = list(Contact.objects.all())
        orgs = list(OrgBase.objects.all())

        # Build lookup indexes
        # org display_name → org (case-insensitive, first match per org_type)
        org_by_name: dict[str, list[OrgBase]] = {}
        for org in orgs:
            key = org.display_name.strip().lower()
            org_by_name.setdefault(key, []).append(org)

        contact_updates = []  # (contact, field_name, org)
        org_updates = []      # (org, contact)

        matched_orgs = set()  # track which orgs got a contact

        for contact in contacts:
            full_name = f"{contact.name_first} {contact.name_last}".strip().lower()
            company = (contact.company or "").strip().lower()

            # Try matching by company, then by full name
            candidates = []
            if company and company in org_by_name:
                candidates.extend(org_by_name[company])
            if full_name and full_name in org_by_name:
                for org in org_by_name[full_name]:
                    if org not in candidates:
                        candidates.append(org)

            for org in candidates:
                org_type = org.org_type
                if not org_type:
                    continue

                # Map org_type to contact FK field name
                field_map = {
                    "customer": "customer",
                    "vendor": "vendor",
                    "manufacturer": "manufacturer",
                    "rep": "rep",
                    "employee": "employee",
                }
                field_name = field_map.get(org_type)
                if not field_name:
                    continue

                # Check if this FK is already set
                current_val = getattr(contact, f"{field_name}_id", None)
                if current_val is not None and current_val == org.id:
                    continue  # already correct

                contact_updates.append((contact, field_name, org))

                # Also set org.contact_id if not already set
                if org.id not in matched_orgs:
                    matched_orgs.add(org.id)
                    if org.contact_id_id != contact.id:
                        org_updates.append((org, contact))

        # Report
        self.stdout.write(f"Contacts: {len(contacts)}")
        self.stdout.write(f"Orgs:     {len(orgs)}")
        self.stdout.write(f"\nContact FK updates ({len(contact_updates)}):")
        for contact, field_name, org in contact_updates:
            self.stdout.write(
                f"  Contact {contact.id} ({contact.name_first} {contact.name_last}) "
                f".{field_name} → Org {org.id} ({org.display_name} [{org.org_type}])"
            )

        self.stdout.write(f"\nOrg contact_id updates ({len(org_updates)}):")
        for org, contact in org_updates:
            self.stdout.write(
                f"  Org {org.id} ({org.display_name} [{org.org_type}]) "
                f".contact_id → Contact {contact.id} ({contact.name_first} {contact.name_last})"
            )

        if not apply:
            self.stdout.write(self.style.WARNING(
                f"\nDry run complete. Use --apply to write {len(contact_updates) + len(org_updates)} changes."
            ))
            return

        # Apply
        with transaction.atomic():
            for contact, field_name, org in contact_updates:
                setattr(contact, field_name, org)
                contact.save(update_fields=[f"{field_name}_id"])

            for org, contact in org_updates:
                org.contact_id = contact
                org.save(update_fields=["contact_id"])

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. Applied {len(contact_updates)} contact FK updates "
            f"and {len(org_updates)} org contact_id updates."
        ))

    def _clear_links(self):
        """Clear all Contact↔Org FK links."""
        self.stdout.write("Clearing existing FK links...")
        fk_fields = ["customer", "vendor", "manufacturer", "rep", "employee"]
        count = 0
        for field in fk_fields:
            updated = Contact.objects.filter(**{f"{field}__isnull": False}).update(**{field: None})
            count += updated
        org_count = OrgBase.objects.filter(contact_id__isnull=False).update(contact_id=None)
        self.stdout.write(f"  Cleared {count} contact FK values, {org_count} org contact_id values.")
