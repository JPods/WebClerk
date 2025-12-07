import random
import uuid
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.transactions.models import (
    Proposal, ProposalLine,
    SalesOrder, SalesOrderLine,
    Invoice, InvoiceLine,
    WorkOrder, WorkOrderLine,
    PurchaseOrder, PurchaseOrderLine,
)
from apps.orgs.models import OrgBase
from apps.products.models import Item


class Command(BaseCommand):
    help = 'Rework transaction data: drop existing records and create new ones with proper relationships'

    def handle(self, *args, **options):
        self.stdout.write('Starting data rework...')

        # Drop existing records
        self.drop_existing_records()

        # Get random orgs
        customers = list(OrgBase.objects.filter(org_type='customer'))
        vendors = list(OrgBase.objects.filter(org_type='vendor'))

        if not customers or not vendors:
            self.stdout.write(self.style.ERROR('No customers or vendors found. Please seed org data first.'))
            return

        # Get random items
        items = list(Item.objects.all())
        if not items:
            self.stdout.write(self.style.ERROR('No items found. Please seed product data first.'))
            return

        # Create transactions
        transaction_types = [
            (Proposal, ProposalLine),
            (SalesOrder, SalesOrderLine),
            (Invoice, InvoiceLine),
            (WorkOrder, WorkOrderLine),
            (PurchaseOrder, PurchaseOrderLine),
        ]

        for trans_model, line_model in transaction_types:
            self.create_transactions(trans_model, line_model, customers, vendors, items)

        self.stdout.write(self.style.SUCCESS('Data rework completed successfully.'))

    def drop_existing_records(self):
        """Drop all existing records from specified models."""
        models_to_drop = [
            Proposal, ProposalLine,
            SalesOrder, SalesOrderLine,
            Invoice, InvoiceLine,
            WorkOrder, WorkOrderLine,
            PurchaseOrder, PurchaseOrderLine,
        ]

        for model in models_to_drop:
            count = model.objects.count()
            model.objects.all().delete()
            self.stdout.write(f'Dropped {count} records from {model.__name__}')

    def create_transactions(self, trans_model, line_model, customers, vendors, items):
        """Create 9 records for the transaction type."""
        # Map line model to parent field name
        parent_fields = {
            'ProposalLine': 'proposal_id',
            'SalesOrderLine': 'salesorder_id',
            'InvoiceLine': 'invoice_id',
            'WorkOrderLine': 'workorder_id',
            'PurchaseOrderLine': 'purchaseorder_id',
            'RequisitionLine': 'requisition_id',
        }
        parent_field = parent_fields.get(line_model.__name__)

        for i in range(9):
            with transaction.atomic():
                # Create transaction
                customer = random.choice(customers)
                vendor = random.choice(vendors)

                trans = trans_model.objects.create(
                    customer_id=customer.id,
                    vendor_id=vendor.id,
                    status='planned',
                )

                # Set UUID and ida
                trans.uuid = uuid.uuid4()
                trans.ida = f"ida-{trans.id}"
                trans.save()

                # Get linked communication records from customer and vendor orgs
                customer_org = OrgBase.objects.get(id=customer.id)
                vendor_org = OrgBase.objects.get(id=vendor.id)

                links = {
                    'contact': [],
                    'email': [],
                    'location': [],
                    'phone': [],
                    'domain': [],
                }

                for org in [customer_org, vendor_org]:
                    # Collect contact ids
                    if isinstance(org.contacts, list):
                        for contact in org.contacts:
                            if 'id' in contact:
                                links['contact'].append(contact['id'])
                    # Collect email ids
                    if isinstance(org.emails, list):
                        for email in org.emails:
                            if 'id' in email:
                                links['email'].append(email['id'])
                    # Collect location ids
                    if isinstance(org.locations, list):
                        for location in org.locations:
                            if 'id' in location:
                                links['location'].append(location['id'])
                    # Collect phone ids
                    if isinstance(org.phones, list):
                        for phone in org.phones:
                            if 'id' in phone:
                                links['phone'].append(phone['id'])
                    # Collect domain ids
                    if isinstance(org.domains, list):
                        for domain in org.domains:
                            if 'id' in domain:
                                links['domain'].append(domain['id'])

                # Store links in refs JSON field
                if hasattr(trans, 'refs'):
                    trans.refs = {'links': links}
                    trans.save()

                # Create 3-8 line records
                num_lines = random.randint(3, 8)
                selected_items = random.sample(items, num_lines)

                for idx, item in enumerate(selected_items):
                    line = line_model.objects.create(
                        **{parent_field: trans}
                    )

                    # Set line details
                    line.quantity = {'placed': random.randint(1, 10), 'precision': 2}
                    line.price = {'unit': random.uniform(10, 100), 'extended': 0.0, 'precision': 2}
                    line.cost = {'unit': random.uniform(5, 50), 'extended': 0.0, 'precision': 2}
                    line.item = {
                        'item_id': item.id,
                        'ida_item': item.ida,
                        'uuid_item': str(item.uuid),
                        'description': item.name,
                        'unit_measure': item.uom or 'EA',
                        'line_number': idx + 1,
                    }
                    line.save()

                self.stdout.write(f'Created {trans_model.__name__} #{trans.id} with {num_lines} lines')