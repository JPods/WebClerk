from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from django.core.management import call_command
from apps.orgs.models import OrgBase, OrgType
from apps.products.models import Catalog, Item, OrgItem, CatalogLine


class Command(BaseCommand):
    help = "Create a tiny sample vendor/customer, catalog, items, and org_items then print them. Safe to run multiple times (idempotent)."

    def handle(self, *args, **options):
        # Ensure migrations applied if using in-memory SQLite (new process each run)
        db_conf = settings.DATABASES['default']
        if db_conf['ENGINE'].endswith('sqlite3') and db_conf['NAME'] == ':memory:':
            call_command('migrate', interactive=False, verbosity=0)

        with transaction.atomic():
            vendor, _ = OrgBase.objects.get_or_create(company="Sample Vendor", org_type=OrgType.VENDOR)
            customer, _ = OrgBase.objects.get_or_create(company="Sample Customer", org_type=OrgType.CUSTOMER)

            now_ms = int(timezone.now().timestamp() * 1000)
            catalog, _ = Catalog.objects.get_or_create(
                code="SAMPLE-CAT",
                vendor_org=vendor,
                defaults={
                    "customer_org": customer,
                    "effective_dt_start": now_ms,
                    "name": "Sample Catalog",
                },
            )

            items = []
            for sku, desc in [
                ("SKU-APPLE", "Apples 10lb"),
                ("SKU-BANANA", "Bananas 10lb"),
                ("SKU-CARROT", "Carrots 25lb"),
            ]:
                item, _ = Item.objects.get_or_create(sku=sku, defaults={"description": desc, "name": desc})
                items.append(item)
                CatalogLine.objects.get_or_create(catalog=catalog, item=item, defaults={})

            created_links = []
            for item in items:
                oi, created = OrgItem.objects.get_or_create(
                    org=customer,
                    item=item,
                    catalog=catalog,
                    defaults={
                        "quantity_minimum": 5,
                        "quantity_maximum": 50,
                        "availability_state": OrgItem.STATE_ENABLED,
                    },
                )
                if created:
                    created_links.append(oi)

        self.stdout.write(self.style.SUCCESS("Sample data ensured."))

        self.stdout.write("\nCatalog:")
        vendor_id = getattr(catalog, 'vendor_org_id', None)
        customer_id = getattr(catalog, 'customer_org_id', None)
        self.stdout.write(f"  id={catalog.id} code={catalog.code} vendor={vendor_id} customer={customer_id}")
        self.stdout.write("\nItems:")
        for it in items:
            self.stdout.write(f"  id={it.id} sku={it.sku} name={it.name}")
        self.stdout.write("\nOrgItems (customer view):")
        qs = OrgItem.objects.filter(org=customer, catalog=catalog).select_related("item")
        for oi in qs:
            self.stdout.write(
                f"  org_item={oi.id} item_sku={oi.item.sku} min={oi.quantity_minimum} max={oi.quantity_maximum} state={oi.availability_state} next_check={oi.dt_next_check}"
            )
        if created_links:
            self.stdout.write(self.style.SUCCESS(f"\nCreated {len(created_links)} new OrgItem links."))
        else:
            self.stdout.write("\n(No new OrgItems created; already present.)")
