from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.models import Contact
from apps.orgs.models import OrgBase
from apps.orgs.services.contact_linking import resolve_contact_ids_for_customer_org


class Command(BaseCommand):
    help = "Sync Contact.company to customer OrgBase.display_name for linked customer contacts."

    def add_arguments(self, parser):
        parser.add_argument("--customer-id", type=int, help="Limit sync to one customer org id.")
        parser.add_argument("--dry-run", action="store_true", help="Show what would change without saving.")

    def handle(self, *args, **options):
        customer_id = options.get("customer_id")
        dry_run = bool(options.get("dry_run"))

        orgs = OrgBase.objects.filter(org_type="customer")
        if customer_id:
            orgs = orgs.filter(pk=customer_id)

        total_updates = 0
        now_ms = int(timezone.now().timestamp() * 1000)

        for org in orgs.iterator():
            if not org.display_name:
                continue
            linked_contact_ids = resolve_contact_ids_for_customer_org(org)
            if not linked_contact_ids:
                continue

            qs = Contact.objects.filter(id__in=linked_contact_ids).exclude(company=org.display_name)
            count = qs.count()
            if not count:
                continue

            if dry_run:
                self.stdout.write(
                    f"Would sync {count} contact(s) for customer {org.pk} to company={org.display_name!r}"
                )
            else:
                qs.update(company=org.display_name, dt_modified=now_ms)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Synced {count} contact(s) for customer {org.pk} to company={org.display_name!r}"
                    )
                )
            total_updates += count

        mode = "DRY RUN" if dry_run else "APPLIED"
        self.stdout.write(f"{mode}: total contact updates={total_updates}")
