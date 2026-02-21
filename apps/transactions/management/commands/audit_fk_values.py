"""Audit FK fields on transaction records for invalid values."""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Audit FK fields on transaction records for zero/negative values"

    def handle(self, *args, **options):
        from apps.transactions.models import Order, Invoice, Proposal, Purchase
        from apps.orgs.models import OrgBase

        for Model in [Order, Invoice, Proposal, Purchase]:
            t = Model._meta.db_table
            name = Model.__name__
            c = connection.cursor()
            c.execute(f"SELECT count(*) FROM {t}")
            total = c.fetchone()[0]
            for col in ["customer_id", "vendor_id", "manufacturer_id", "contact_id"]:
                c.execute(f"SELECT count(*) FROM {t} WHERE {col} = 0")
                zeros = c.fetchone()[0]
                c.execute(f"SELECT count(*) FROM {t} WHERE {col} < 0")
                negs = c.fetchone()[0]
                if zeros or negs:
                    self.stdout.write(f"  BAD {name}.{col}: {zeros} zeros, {negs} negatives")
                    c.execute(f"SELECT id, {col} FROM {t} WHERE {col} <= 0 LIMIT 5")
                    for row in c.fetchall():
                        self.stdout.write(f"    id={row[0]} {col}={row[1]}")
            self.stdout.write(f"{name}({t}): {total} total records")

        # Order #7 details
        self.stdout.write("\n--- Order #7 ---")
        try:
            o = Order.objects.get(id=7)
            self.stdout.write(f"customer_id: {o.customer_id}")
            self.stdout.write(f"customer __str__: {str(o.customer) if o.customer else 'None'}")
            self.stdout.write(f"vendor_id: {o.vendor_id}")
            self.stdout.write(f"manufacturer_id: {o.manufacturer_id}")
            self.stdout.write(f"contact_id: {o.contact_id}")
            links = o.refs.get("links") if o.refs else None
            self.stdout.write(f"refs.links: {links}")
        except Order.DoesNotExist:
            self.stdout.write("Order #7 not found")

        # OrgBase #82 display_name vs __str__
        self.stdout.write("\n--- OrgBase #82 ---")
        try:
            org = OrgBase.objects.get(id=82)
            self.stdout.write(f"display_name: {org.display_name}")
            self.stdout.write(f"__str__: {str(org)}")
            self.stdout.write(f"name attr: {getattr(org, 'name', 'N/A')}")
            self.stdout.write(f"email: {org.email}")
        except OrgBase.DoesNotExist:
            self.stdout.write("OrgBase #82 not found")
