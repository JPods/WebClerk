"""
Populate rich JSON aspect data (addresses, emails, phones) on all demo
transactions and orgs for training videos.

- Orgs: prime/bill_to/ship_to from existing scalar fields + fake addresses
- Transactions: bill_to/ship_to resolved from customer/vendor org
- Contacts: home/work/primary/mobile/office from existing scalar fields

Usage:
    python manage.py populate_demo_aspects
    python manage.py populate_demo_aspects --dry-run
"""
import random
from django.core.management.base import BaseCommand

from apps.transactions.models import (
    Proposal, Order, Invoice, Purchase,
)
from apps.orgs.models import OrgBase
from apps.core.models import Contact


# ── Fake address data for demo variety ────────────────────────────

FAKE_STREETS = [
    "123 Main St", "456 Oak Ave", "789 Industrial Blvd",
    "1010 Commerce Dr", "222 Maple Ln", "555 Park Row",
    "888 River Rd", "321 Cedar Ct", "650 Market St", "42 Elm Way",
]

FAKE_CITIES = [
    ("Springfield", "IL", "62701"), ("Portland", "OR", "97201"),
    ("Austin", "TX", "78701"), ("Denver", "CO", "80201"),
    ("Nashville", "TN", "37201"), ("Charlotte", "NC", "28201"),
    ("Raleigh", "NC", "27601"), ("Boise", "ID", "83701"),
]

FAKE_PHONES = [
    "5551234567", "5559876543", "5554567890", "5550001111",
    "5552223333", "5554445555", "5556667777", "5558889999",
]


def _fake_address(seed=0):
    street = FAKE_STREETS[seed % len(FAKE_STREETS)]
    city, state, zip_code = FAKE_CITIES[seed % len(FAKE_CITIES)]
    return f"{street}, {city} {state} {zip_code}"


def _fake_phone(seed=0):
    return FAKE_PHONES[seed % len(FAKE_PHONES)]


class Command(BaseCommand):
    help = 'Populate rich JSON aspect data on demo orgs, transactions, and contacts'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        self._populate_orgs(dry_run)
        self._populate_transactions(dry_run)
        self._populate_contacts(dry_run)

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no changes saved'))
        else:
            self.stdout.write(self.style.SUCCESS('Done'))

    def _populate_orgs(self, dry_run):
        """Fill org aspects: addresses, emails, phones as party-keyed dicts."""
        orgs = OrgBase.objects.all()
        self.stdout.write(f'\nOrgs: {orgs.count()} records')
        updated = 0

        for i, org in enumerate(orgs):
            email = org.email or ''
            company = org.display_name or ''
            attention = org.attention or company
            contact_id = org.contact_id

            prime_addr = _fake_address(i)
            bill_addr = _fake_address(i + 3)
            ship_addr = _fake_address(i + 7)
            prime_phone = _fake_phone(i)
            bill_phone = _fake_phone(i + 2)
            ship_phone = _fake_phone(i + 5)

            bill_email = email
            ship_email = email.replace('@', '+shipping@') if email else ''

            org.addresses = {
                "prime": {
                    "contact_id": contact_id, "company": company, "attention": attention,
                    "full_address": prime_addr, "instructions": "",
                },
                "bill_to": {
                    "contact_id": contact_id, "company": company, "attention": attention,
                    "full_address": bill_addr, "instructions": "Attn: Accounts Payable",
                },
                "ship_to": {
                    "contact_id": contact_id, "company": company, "attention": attention,
                    "full_address": ship_addr, "instructions": "Dock 3, call before delivery",
                },
            }
            org.emails = {
                "prime": {"email_id": None, "email": email},
                "bill_to": {"email_id": None, "email": bill_email},
                "ship_to": {"email_id": None, "email": ship_email},
            }
            org.phones = {
                "prime": {"phone_id": None, "number": prime_phone},
                "bill_to": {"phone_id": None, "number": bill_phone},
                "ship_to": {"phone_id": None, "number": ship_phone},
            }

            updated += 1
            if dry_run:
                self.stdout.write(f'  Org #{org.id} {org.display_name}: addresses/emails/phones set')
            else:
                org.save(update_fields=['addresses', 'emails', 'phones'])

        self.stdout.write(f'  {updated}/{orgs.count()} updated')

    def _populate_transactions(self, dry_run):
        """Fill transaction aspects from customer/vendor org data."""
        sell_models = [Proposal, Order, Invoice]
        for model in sell_models:
            self._fill_trans(model, 'customer', dry_run)
        self._fill_trans(Purchase, 'vendor', dry_run)

    def _fill_trans(self, model, org_field, dry_run):
        name = model.__name__
        qs = model.objects.select_related(org_field).all()
        self.stdout.write(f'\n{name}: {qs.count()} records')
        updated = 0

        for h in qs:
            org = getattr(h, org_field, None)
            if not org:
                continue

            org_addrs = org.addresses if isinstance(org.addresses, dict) else {}
            org_emails = org.emails if isinstance(org.emails, dict) else {}
            org_phones = org.phones if isinstance(org.phones, dict) else {}

            # Snapshot org's bill_to/ship_to onto the transaction
            h.addresses = {
                "bill_to": org_addrs.get("bill_to", {}),
                "ship_to": org_addrs.get("ship_to", {}),
            }
            h.emails = {
                "bill_to": org_emails.get("bill_to", {}),
                "ship_to": org_emails.get("ship_to", {}),
            }
            h.phones = {
                "bill_to": org_phones.get("bill_to", {}),
                "ship_to": org_phones.get("ship_to", {}),
            }

            updated += 1
            if dry_run:
                self.stdout.write(f'  {name} #{h.id}: aspects set from {org.display_name}')
            else:
                h.save(update_fields=['addresses', 'emails', 'phones'])

        self.stdout.write(f'  {updated}/{qs.count()} updated')

    def _populate_contacts(self, dry_run):
        """Fill contact aspects with personal keys from existing scalar data."""
        # Only populate contacts that are linked to demo orgs (qq ida prefix)
        demo_org_ids = list(OrgBase.objects.filter(
            ida__startswith='qq'
        ).values_list('contact_id', flat=True))
        contacts = Contact.objects.filter(id__in=[x for x in demo_org_ids if x])
        self.stdout.write(f'\nContacts (demo-linked): {contacts.count()} records')
        updated = 0

        for i, c in enumerate(contacts):
            email = c.email or ''
            home_addr = _fake_address(i + 10)
            work_addr = _fake_address(i + 15)
            mobile = _fake_phone(i + 1)
            office = _fake_phone(i + 4)

            c.addr_aspect = {
                "home": {"full_address": home_addr},
                "work": {"full_address": work_addr},
            }
            c.email_aspect = {
                "primary": {"email": email},
                "work": {"email": email},
            }
            c.phone_aspect = {
                "mobile": {"number": mobile},
                "office": {"number": office},
            }

            updated += 1
            if dry_run:
                self.stdout.write(f'  Contact #{c.id} {c.attention or email}: aspects set')
            else:
                c.save(update_fields=['addr_aspect', 'email_aspect', 'phone_aspect'])

        self.stdout.write(f'  {updated}/{contacts.count()} updated')
