"""Seed a retail hardware store demo with items, contacts, orgs, and a multi-level BOM.

All demo records use ida = 'qq' + str(id) to distinguish from real data.
Safe to run multiple times (idempotent via get_or_create).

NOTE: Uses queryset.update() for ida assignment instead of model.save() to avoid
triggering cascading post-save signals (denorm, keyword rebuild, etc.) that hang
when iterated across 40+ records in a single transaction.
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.orgs.models import OrgBase
from apps.orgs.models.constants import OrgType
from apps.products.models import Item, BillOfMaterial
from apps.core.models.contact import Contact


def _make_price(base, cost):
    """Build price and cost dicts with realistic detail numbers."""
    return (
        {
            "base": str(base), "msrp": str(round(base * 1.15, 2)),
            "retail": str(base), "wholesale": str(round(base * 0.85, 2)),
            "distributor": str(round(base * 0.75, 2)),
            "currency": "USD", "qty_breaks": [], "history": [],
        },
        {
            "standard": str(cost), "last": str(cost), "avg": str(cost),
            "landed": str(round(cost * 1.05, 2)),
            "currency": "USD", "components": {}, "qty_breaks": [], "history": [],
        },
    )


# -- Retail hardware store product catalog --
ITEMS = [
    # (sku, name, description, kind, uom, price_base, cost_std, category)
    # Power Tools
    ("HW-DRL-001", "DeWalt 20V Cordless Drill", "20V MAX lithium-ion cordless drill/driver kit", "physical", "EA", 129.99, 78.00, "Power Tools"),
    ("HW-DRL-002", "Makita Impact Driver", "18V LXT brushless impact driver", "physical", "EA", 149.99, 89.00, "Power Tools"),
    ("HW-SAW-001", "Milwaukee Circular Saw 7-1/4\"", "15 Amp circular saw with blade", "physical", "EA", 119.99, 72.00, "Power Tools"),
    ("HW-SND-001", "Bosch Random Orbit Sander", "5\" variable speed random orbit sander", "physical", "EA", 69.99, 42.00, "Power Tools"),
    # Hand Tools
    ("HW-HMR-001", "Estwing 16oz Claw Hammer", "Steel shaft, leather grip claw hammer", "physical", "EA", 29.99, 14.50, "Hand Tools"),
    ("HW-WRN-001", "Craftsman 10pc Wrench Set", "SAE combination wrench set", "physical", "SET", 34.99, 18.00, "Hand Tools"),
    ("HW-SCR-001", "Stanley Screwdriver Set 20pc", "Phillips and flathead assortment", "physical", "SET", 24.99, 12.00, "Hand Tools"),
    ("HW-TPM-001", "Stanley 25ft Tape Measure", "PowerLock 25ft tape measure", "physical", "EA", 12.99, 5.50, "Hand Tools"),
    ("HW-LVL-001", "Empire 48\" Box Level", "Aluminum box beam level", "physical", "EA", 39.99, 19.00, "Hand Tools"),
    ("HW-PLR-001", "Channellock Pliers Set 4pc", "Tongue and groove pliers assortment", "physical", "SET", 44.99, 22.00, "Hand Tools"),
    # Fasteners
    ("HW-SCW-001", "Deck Screws #8 x 2-1/2\" 1lb", "Coated exterior deck screws", "physical", "LB", 8.99, 3.80, "Fasteners"),
    ("HW-SCW-002", "Drywall Screws #6 x 1-5/8\" 1lb", "Fine thread drywall screws", "physical", "LB", 6.99, 2.90, "Fasteners"),
    ("HW-NL-001", "16d Common Nails 5lb", "Bright common nails", "physical", "BX", 12.99, 5.20, "Fasteners"),
    ("HW-BLT-001", "Hex Bolts 3/8 x 3\" 25pk", "Grade 5 zinc plated hex bolts", "physical", "PK", 9.99, 4.10, "Fasteners"),
    ("HW-ANR-001", "Concrete Anchors 3/8\" 10pk", "Wedge anchors for concrete", "physical", "PK", 14.99, 6.50, "Fasteners"),
    # Lumber & Building
    ("HW-LBR-001", "2x4x8 SPF Stud", "Kiln dried spruce-pine-fir stud", "physical", "EA", 4.99, 2.80, "Lumber"),
    ("HW-LBR-002", "2x6x10 Treated", "Ground contact pressure treated lumber", "physical", "EA", 12.49, 7.20, "Lumber"),
    ("HW-PLY-001", "3/4\" CDX Plywood 4x8", "Exterior grade CDX plywood", "physical", "SHT", 52.99, 34.00, "Lumber"),
    ("HW-PLY-002", "1/2\" Drywall 4x8", "Standard gypsum drywall sheet", "physical", "SHT", 14.99, 8.50, "Lumber"),
    # Paint
    ("HW-PNT-001", "Behr Interior Flat Gallon", "Premium plus interior flat paint, white", "physical", "GAL", 34.99, 18.00, "Paint"),
    ("HW-PNT-002", "Behr Exterior Satin Gallon", "Premium plus exterior satin paint, white", "physical", "GAL", 42.99, 22.00, "Paint"),
    ("HW-PNT-003", "Painter's Tape 1.88\" x 60yd", "Blue multi-surface painter's tape", "physical", "RL", 7.99, 3.20, "Paint"),
    ("HW-BRS-001", "Purdy 2\" Angle Brush", "XL angular trim brush", "physical", "EA", 14.99, 7.00, "Paint"),
    ("HW-RLR-001", "Roller Cover 9\" 3/8nap 3pk", "Microfiber roller covers", "physical", "PK", 12.99, 5.50, "Paint"),
    # Plumbing
    ("HW-PLB-001", "1/2\" Copper Pipe 10ft", "Type M copper tubing", "physical", "EA", 18.99, 11.00, "Plumbing"),
    ("HW-PLB-002", "PVC Cement 8oz", "Regular clear PVC cement", "physical", "EA", 6.99, 2.80, "Plumbing"),
    ("HW-PLB-003", "Toilet Repair Kit", "Universal fill valve and flapper kit", "physical", "EA", 19.99, 9.50, "Plumbing"),
    ("HW-PLB-004", "Kitchen Faucet Chrome", "Single handle pull-down kitchen faucet", "physical", "EA", 129.99, 65.00, "Plumbing"),
    # Electrical
    ("HW-ELC-001", "Romex 14/2 NM-B 250ft", "Non-metallic sheathed cable", "physical", "RL", 89.99, 52.00, "Electrical"),
    ("HW-ELC-002", "Outlet Receptacle 15A", "Tamper resistant duplex receptacle", "physical", "EA", 1.49, 0.55, "Electrical"),
    ("HW-ELC-003", "LED Bulb 60W Equiv 4pk", "A19 soft white LED bulbs", "physical", "PK", 9.99, 4.20, "Electrical"),
    ("HW-ELC-004", "Wire Nuts Assorted 100pk", "Twist-on wire connectors", "physical", "PK", 8.99, 3.50, "Electrical"),
    # Safety
    ("HW-SAF-001", "Safety Glasses Clear", "Impact resistant safety glasses", "physical", "EA", 4.99, 1.80, "Safety"),
    ("HW-SAF-002", "Work Gloves Leather XL", "Premium cowhide work gloves", "physical", "PR", 14.99, 6.50, "Safety"),
    ("HW-SAF-003", "Ear Plugs 200pr Dispenser", "Foam ear plug dispenser", "physical", "BX", 29.99, 12.00, "Safety"),
    ("HW-SAF-004", "First Aid Kit 100pc", "OSHA-compliant first aid kit", "physical", "EA", 24.99, 11.00, "Safety"),
    # Services
    ("HW-SVC-001", "Key Cutting", "Standard key duplication", "service", "EA", 3.99, 0.50, "Services"),
    ("HW-SVC-002", "Paint Color Match", "Custom color matching service", "service", "EA", 5.99, 1.00, "Services"),
    ("HW-SVC-003", "Blade Sharpening", "Mower blade or tool sharpening", "service", "EA", 8.99, 2.00, "Services"),
    ("HW-SVC-004", "Delivery - Local", "Local delivery within 15 miles", "service", "EA", 49.99, 25.00, "Services"),
]

CONTACTS = [
    ("dale@demo-hardware.com", "Dale", "Cooper", "employee", "Sales Manager"),
    ("maria@demo-hardware.com", "Maria", "Santos", "employee", "Counter Sales"),
    ("joe@contractor.com", "Joe", "Builder", "user", "General Contractor"),
    ("sarah@homeowner.com", "Sarah", "Mitchell", "user", "Homeowner"),
]

ORGS = [
    ("Oakdale Hardware & Supply", "customer"),
    ("ProBuild Contractors Inc", "customer"),
    ("Mitchell Residence", "customer"),
    ("Stanley Tools", "vendor"),
    ("Behr Paint Co", "vendor"),
    ("Southern Pine Lumber", "vendor"),
]


class Command(BaseCommand):
    help = "Seed a retail hardware store demo. All ida = qq + str(id). Idempotent."

    def _set_ida(self, model_class, pk):
        """Set ida via queryset.update() — avoids triggering post-save signals."""
        ida = f"qq{pk}"
        model_class.objects.filter(pk=pk, ida="").update(ida=ida)
        return ida

    def _create_bom_line(self, parent, child_sku, qty, seq):
        """Create a single BOM line. Returns True if created."""
        try:
            child = Item.objects.get(sku=child_sku)
            _, created = BillOfMaterial.objects.get_or_create(
                parent_item=parent,
                child_item=child,
                defaults={
                    "parent_ida": parent.ida or f"qq{parent.pk}",
                    "child_ida": child.ida or f"qq{child.pk}",
                    "child_description": child.name,
                    "quantity": Decimal(str(qty)),
                    "sequence": seq,
                },
            )
            return created
        except Item.DoesNotExist:
            self.stdout.write(self.style.WARNING(f"  BOM child {child_sku} not found"))
            return False

    def handle(self, *args, **options):
        # Temporarily disconnect the post_save signal that pushes to Alice's
        # denormalize stack — it deadlocks when many records are created in
        # a single transaction (all compete for the same Pending row).
        from django.db.models.signals import post_save
        from common.signals import basemodel_change_logger
        post_save.disconnect(basemodel_change_logger)
        self.stdout.write("  (post_save signal disconnected for bulk seed)")

        created_items = 0
        created_contacts = 0
        created_orgs = 0

        with transaction.atomic():
            # -- Orgs (use update for ida, not save) --
            org_map = {}
            for company, org_type_str in ORGS:
                ot = OrgType.VENDOR if org_type_str == "vendor" else OrgType.CUSTOMER
                org, created = OrgBase.objects.get_or_create(
                    display_name=company,
                    defaults={"org_type": ot},
                )
                if created:
                    self._set_ida(OrgBase, org.pk)
                    created_orgs += 1
                org_map[company] = org
            self.stdout.write(f"  Orgs: {created_orgs} created, {len(org_map)} total")

            # -- Contacts --
            for email, first, last, role, title in CONTACTS:
                contact, created = Contact.objects.get_or_create(
                    email=email,
                    defaults={
                        "name_first": first,
                        "name_last": last,
                        "role": role,
                        "title": title,
                        "is_active": True,
                    },
                )
                if created:
                    contact.set_password("demo1234")
                    # save password hash, then set ida via update
                    Contact.objects.filter(pk=contact.pk).update(password=contact.password)
                    self._set_ida(Contact, contact.pk)
                    created_contacts += 1
            self.stdout.write(f"  Contacts: {created_contacts} created")

            # -- Items (leaf items first) --
            vendor_map = {
                "Power Tools": org_map.get("Stanley Tools"),
                "Hand Tools": org_map.get("Stanley Tools"),
                "Paint": org_map.get("Behr Paint Co"),
                "Lumber": org_map.get("Southern Pine Lumber"),
            }

            for sku, name, desc, kind, uom, price_base, cost_std, category in ITEMS:
                price, cost = _make_price(price_base, cost_std)
                item, created = Item.objects.get_or_create(
                    sku=sku,
                    defaults={
                        "name": name, "description": desc, "kind": kind, "uom": uom,
                        "price": price, "cost": cost,
                        "catalog": {
                            "categories": [category], "attributes": {},
                            "web": {"slug": sku.lower()}, "flags": {},
                        },
                        "quantity": {
                            "on_hand": 50 if kind == "physical" else 0,
                            "allocated": 0,
                            "available": 50 if kind == "physical" else 0,
                            "on_so": 0, "on_po": 0,
                        },
                        "vendor": vendor_map.get(category),
                    },
                )
                if created:
                    self._set_ida(Item, item.pk)
                    created_items += 1
            self.stdout.write(f"  Leaf items: {created_items} created")

            # -- Level 1 bundle: Contractor Job Init Kit --
            job_kit = self._create_bundle(
                sku="HW-KIT-001",
                name="Contractor Job Init Kit",
                desc="Starter bundle for new construction job sites: drill, saw, fasteners, safety gear, lumber basics, and delivery",
                price_base=499.99,
                category="Kits",
            )

            job_kit_bom = [
                ("HW-DRL-001", 1, 10),    # drill
                ("HW-SAW-001", 1, 20),     # circular saw
                ("HW-TPM-001", 2, 30),     # 2 tape measures
                ("HW-LVL-001", 1, 40),     # box level
                ("HW-SCW-001", 5, 50),     # 5 lbs deck screws
                ("HW-NL-001", 2, 60),      # 2 boxes nails
                ("HW-LBR-001", 20, 70),    # 20 studs
                ("HW-PLY-001", 4, 80),     # 4 sheets plywood
                ("HW-SAF-001", 4, 90),     # 4 safety glasses
                ("HW-SAF-002", 4, 100),    # 4 pairs gloves
                ("HW-ELC-003", 2, 110),    # 2 LED bulb packs
                ("HW-SVC-004", 1, 120),    # delivery
            ]
            kit_bom_count = sum(
                self._create_bom_line(job_kit, sku, qty, seq)
                for sku, qty, seq in job_kit_bom
            )
            self.stdout.write(f"  Job Init Kit BOM: {kit_bom_count} lines")

            # -- Level 2 bundle: 4ft Square Deck Kit (contains Job Init Kit + more) --
            deck_kit = self._create_bundle(
                sku="HW-KIT-002",
                name="4ft Square Deck Kit",
                desc="Complete 4x4 deck: framing lumber, decking screws, concrete anchors, joist hangers, and a Job Init Kit with tools and delivery",
                price_base=899.99,
                category="Kits",
            )

            deck_bom = [
                ("HW-KIT-001", 1, 10),    # Job Init Kit (multi-level!)
                ("HW-LBR-002", 6, 20),    # 6x 2x6x10 treated joists
                ("HW-LBR-001", 12, 30),   # 12x 2x4 for railing/framing
                ("HW-SCW-001", 10, 40),   # 10 lbs deck screws
                ("HW-ANR-001", 2, 50),    # 2 packs concrete anchors
                ("HW-BLT-001", 4, 60),    # 4 packs hex bolts for ledger
                ("HW-PNT-002", 2, 70),    # 2 gallons exterior paint
            ]
            deck_bom_count = sum(
                self._create_bom_line(deck_kit, sku, qty, seq)
                for sku, qty, seq in deck_bom
            )
            self.stdout.write(f"  Deck Kit BOM: {deck_bom_count} lines")

        # Reconnect the signal
        post_save.connect(basemodel_change_logger)
        self.stdout.write("  (post_save signal reconnected)")

        # -- Summary (outside transaction) --
        self.stdout.write(self.style.SUCCESS(
            f"\nRetail demo seeded: {created_items + 2} items, {created_contacts} contacts, {created_orgs} orgs"
        ))
        self.stdout.write(f"  Multi-level BOM: Deck Kit -> Job Init Kit -> leaf items (3 levels)")
        self.stdout.write(f"  Total HW-* items: {Item.objects.filter(sku__startswith='HW-').count()}")

    def _create_bundle(self, sku, name, desc, price_base, category):
        """Create a bundle item, set ida via update. Returns the item."""
        price, cost = _make_price(price_base, 0)
        item, created = Item.objects.get_or_create(
            sku=sku,
            defaults={
                "name": name, "description": desc, "kind": "bundle", "uom": "EA",
                "price": price, "cost": cost,
                "catalog": {
                    "categories": [category],
                    "attributes": {},
                    "web": {"slug": sku.lower()},
                    "flags": {"featured": True},
                },
                "quantity": {
                    "on_hand": 10, "allocated": 0, "available": 10,
                    "on_so": 0, "on_po": 0,
                },
            },
        )
        if created:
            self._set_ida(Item, item.pk)
        return item
