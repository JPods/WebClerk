"""
Management command: seed_jpods_demo

Creates the demo data needed to run JPods trip booking:
  1. Demo Contact + Customer records (pre-assigned riders)
  2. Item (kind="service") records — one per station pair, with demo/retail/employee pricing
  3. Connection record for Natalie (API token Alice accepts)
  4. Alice action record: encrypt API keys before release (review 2026-05-29)

SKU convention: JPODS-{NETWORK_ID}-{ORIGIN}-{DESTINATION}
  e.g. JPODS-DEFAULT-S001-S003

Price levels map to Item.price keys:
  Customer.price_level="demo"     → Item.price["wholesale"]
  Customer.price_level="retail"   → Item.price["retail"]
  Customer.price_level="employee" → Item.price["sample"]

Usage:
    python manage.py seed_jpods_demo
    python manage.py seed_jpods_demo --reset   (deletes and recreates everything)

Safe to run multiple times without --reset. Skips records that already exist.
"""

import logging
import secrets

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.models import Contact
from apps.orgs.models import OrgBase
from apps.products.models import Item
from apps.sync.models import Connection
from apps.ai_assistant.services.notes import create_note

logger = logging.getLogger(__name__)

DEMO_NETWORK = "default"

DEMO_CONTACTS = [
    # JPods internal demo riders — price_level="demo"
    {"name_first": "Bill",    "name_last": "James",    "email": "bill@jpods-demo.local",   "phone": "555-0001",    "price_level": "demo"},
    {"name_first": "Demo",    "name_last": "One",      "email": "demo1@jpods-demo.local",  "phone": "555-0011",    "price_level": "demo"},
    {"name_first": "Demo",    "name_last": "Two",      "email": "demo2@jpods-demo.local",  "phone": "555-0012",    "price_level": "demo"},
    {"name_first": "Demo",    "name_last": "Three",    "email": "demo3@jpods-demo.local",  "phone": "555-0013",    "price_level": "demo"},
    {"name_first": "Demo",    "name_last": "Four",     "email": "demo4@jpods-demo.local",  "phone": "555-0014",    "price_level": "demo"},
    # Traveler archetypes — price_level set in WC3 to match pricing tiers
    {"name_first": "Child",   "name_last": "Traveler", "email": "child@traveler.com",      "phone": "111.111.1111", "price_level": "retail"},
    {"name_first": "Adult",   "name_last": "Traveler", "email": "adult@traveler.com",      "phone": "222.222.2222", "price_level": "retail"},
    {"name_first": "Elderly", "name_last": "Traveler", "email": "elderly@traveler.com",    "phone": "333.333.3333", "price_level": "retail"},
]

# Station pairs to seed pricing for.
# Add more pairs as the demo network grows.
STATION_PAIRS = [
    # Original demo stations
    ("S001", "S002"),
    ("S001", "S003"),
    ("S002", "S001"),
    ("S002", "S003"),
    ("S003", "S001"),
    ("S003", "S002"),
    # SketchUp model stations
    ("S097", "S098"),
    ("S097", "S099"),
    ("S097", "S100"),
    ("S098", "S097"),
    ("S098", "S099"),
    ("S098", "S100"),
    ("S099", "S097"),
    ("S099", "S098"),
    ("S099", "S100"),
    ("S100", "S097"),
    ("S100", "S098"),
    ("S100", "S099"),
]

# Prices per level stored in Item.price:
#   demo     → wholesale  (demo event rate)
#   retail   → retail     (standard passenger rate)
#   employee → sample     (employee rate)
TRIP_PRICES = {
    "wholesale": "0.50",   # demo
    "retail":    "2.00",   # retail
    "sample":    "0.25",   # employee
}

# Token Natalie uses when calling Alice.
# Matches the webclerk-alice key in /Users/williamjames/Allie/config/allie_api_keys.json
NATALIE_TOKEN = "wq80pbGbKmIHbhT24O9QbkpvWpbnYtMQ2wZASIEGtHY"


class Command(BaseCommand):
    help = "Seed JPods demo contacts, trip Items, and Alice connection record"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing JPods demo data before seeding",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self._reset()

        self._seed_contacts()
        self._seed_trip_items()
        self._seed_connection()
        self._seed_encryption_action()

        self.stdout.write(self.style.SUCCESS("JPods demo seed complete."))

    # ── Reset ────────────────────────────────────────────────────────

    def _reset(self):
        emails = [c["email"] for c in DEMO_CONTACTS]
        deleted, _ = Contact.objects.filter(email__in=emails).delete()
        self.stdout.write(f"  Deleted {deleted} demo contacts")

        skus = [
            f"JPODS-{DEMO_NETWORK}-{o}-{d}".upper()
            for o, d in STATION_PAIRS
        ]
        deleted, _ = Item.objects.filter(sku__in=skus).delete()
        self.stdout.write(f"  Deleted {deleted} trip items")

        deleted, _ = Connection.objects.filter(name="natalie").delete()
        self.stdout.write(f"  Deleted {deleted} natalie connection records")

    # ── Contacts + Customers ─────────────────────────────────────────

    def _seed_contacts(self):
        for spec in DEMO_CONTACTS:
            contact, created = Contact.objects.get_or_create(
                email=spec["email"],
                defaults={
                    "name_first": spec["name_first"],
                    "name_last": spec["name_last"],
                    "phone": spec["phone"],
                    "is_active": True,
                    "role": "user",
                },
            )
            if created:
                # Set unusable password — demo contacts don't log in via password
                contact.set_unusable_password()
                contact.save()

            # Store myCarryOn identity pointer in contact.metadata
            metadata = contact.metadata if isinstance(contact.metadata, dict) else {}
            if "myCarryOn" not in metadata:
                metadata["myCarryOn"] = {
                    "uuid": str(contact.uuid),
                    "token": secrets.token_urlsafe(32),
                    "status": "pending",
                    "note": "sync to mycarryon.io when that WebClerk is ready",
                }
                contact.metadata = metadata
                contact.save(update_fields=["metadata"])

            # Create or find linked Customer org
            if not contact.customer_id:
                customer = OrgBase.objects.create(
                    org_type="customer",
                    display_name=contact.get_full_name(),
                    email=spec["email"],
                    phone=spec["phone"],
                    price_level=spec.get("price_level", "retail"),
                    status="active",
                )
                contact.customer = customer
                contact.save(update_fields=["customer"])

            label = "created" if created else "exists"
            self.stdout.write(
                f"  Contact {label}: {spec['name_first']} {spec['name_last']} ({spec['email']})"
            )

    # ── Trip Items ───────────────────────────────────────────────────

    def _seed_trip_items(self):
        count = 0
        for origin, destination in STATION_PAIRS:
            sku = f"JPODS-{DEMO_NETWORK}-{origin}-{destination}".upper()
            name = f"JPods Trip {origin}→{destination}"

            price_data = {
                "base":        TRIP_PRICES["retail"],   # base = retail for history tracking
                "msrp":        None,
                "retail":      TRIP_PRICES["retail"],   # standard passenger
                "wholesale":   TRIP_PRICES["wholesale"], # demo
                "distributor": None,
                "sample":      TRIP_PRICES["sample"],   # employee
                "qty_breaks":  [],
                "currency":    "USD",
                "history":     [],
            }

            item, created = Item.objects.get_or_create(
                sku=sku,
                defaults={
                    "name":        name,
                    "kind":        Item.KIND_SERVICE,
                    "description": f"JPods automated trip from {origin} to {destination}",
                    "uom":         "trip",
                    "price":       price_data,
                    "flags":       {"not_tracked": True},
                    "is_active":   True,
                },
            )
            if created:
                count += 1

        self.stdout.write(f"  Trip items: {count} created, {len(STATION_PAIRS) - count} already existed")

    # ── Natalie Connection Record ─────────────────────────────────────

    def _seed_connection(self):
        conn, created = Connection.objects.get_or_create(
            name="natalie",
            defaults={
                "type": "api",
                "status": "active",
                "purpose": "inbound",
                "config": {
                    "token": NATALIE_TOKEN,
                    "agent": "natalie",
                    "description": "Token Natalie uses to call Alice price_query and invoice endpoints",
                    "note": "plaintext during development — encrypt before release (see action record)",
                },
                "comment": "Natalie → Alice API connection for JPods trip pricing and invoicing",
            },
        )
        label = "created" if created else "exists"
        self.stdout.write(f"  Natalie connection: {label}")

    # ── Alice Action: Encrypt keys before release ─────────────────────

    def _seed_encryption_action(self):
        from apps.core.models import Setting
        exists = Setting.objects.filter(
            purpose="alice_pending",
            role="action_required",
            name__icontains="Encrypt API keys",
            is_active=True,
        ).exists()

        if exists:
            self.stdout.write("  Encryption action: already exists")
            return

        create_note(
            "pending",
            role="action_required",
            name="Encrypt API keys + blockchain audit trail before release",
            parent_model="connection",
            details={
                "review_date": "2026-05-29",
                "connections": ["natalie"],
                "agent_key_files": [
                    "/Users/williamjames/Allie/config/allie_api_keys.json",
                    "/Users/williamjames/Documents/08_JPods/03_Technology/JPodsSM_RPi/config/natalie-keys.json",
                    "/Users/williamjames/Documents/08_JPods/03_Technology/JPodsSM_RPi/config/noelle-keys.json",
                    "/Users/williamjames/Documents/08_JPods/03_Technology/JPodsSM_RPi/config/nora-keys.json",
                ],
                "note": (
                    "All API keys are plaintext JSON during development. "
                    "Before public release: encrypt Connection.config, add blockchain "
                    "audit trail for every key change (immutable log of who changed what and when). "
                    "Allie flags this at session start if review_date is within 7 days."
                ),
                "created_by": "seed_jpods_demo",
            },
        )
        self.stdout.write(self.style.WARNING(
            "  Encryption action created — review due 2026-05-29"
        ))
