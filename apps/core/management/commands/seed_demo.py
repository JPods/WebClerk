"""
seed_demo — Seed curated demo data for training and demonstration.

Usage:
    python manage.py seed_demo
    python manage.py seed_demo --force   # delete demo data and re-seed

Creates realistic demo data showing the full commerce cycle:
  - 5 customers (different types: retail, wholesale, team, online, school)
  - 1 vendor (baseball equipment supplier)
  - 12 items (bats, balls, gloves, bags, kit with BOM)
  - 3 complete transaction cycles (proposal → order → invoice → payment)

All demo records use ida prefix 'qqdemo-' for easy identification and cleanup.
Prerequisites: seed_freshstart must have run first (GL accounts, terms required).
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.products.models import Item
from apps.products.models.bill_of_material import BillOfMaterial
from apps.core.models.contact import Contact
from apps.orgs.models import OrgBase


DEMO_PREFIX = 'qqdemo-'

# ─── GL defaults for all demo items ─────────────────────────────────────
ITEM_GLS = {
    'revenue': '4000-Sales',
    'cogs': '5000-COGS',
    'inventory': '1200-Inventory',
}

# ─── Items ───────────────────────────────────────────────────────────────
ITEMS = [
    # Bats
    {'ida': 'qqdemo-BAT-01', 'name': 'Louisville Slugger Omaha XS Adult Bat (-3)',
     'description': 'BBCOR certified, 33/30, aluminum alloy',
     'price': {'base': '199.95', 'A': '179.95', 'B': '169.95', 'C': '159.95'},
     'cost': {'standard': '89.00', 'avg': '89.00', 'currency': 'USD'},
     'kind': 'sale'},
    {'ida': 'qqdemo-BAT-02', 'name': 'Rawlings Plasma Gold Adult Bat (-3)',
     'description': 'Composite barrel, 34/31, BBCOR',
     'price': {'base': '229.95', 'A': '206.95', 'B': '195.95', 'C': '183.95'},
     'cost': {'standard': '102.00', 'avg': '102.00', 'currency': 'USD'},
     'kind': 'sale'},
    {'ida': 'qqdemo-BAT-03', 'name': 'Louisville Fungo Bat 36"',
     'description': 'Practice fungo bat, ash wood',
     'price': {'base': '44.00', 'A': '39.60', 'B': '37.40', 'C': '35.20'},
     'cost': {'standard': '18.50', 'avg': '18.50', 'currency': 'USD'},
     'kind': 'sale'},

    # Balls
    {'ida': 'qqdemo-BALL-01', 'name': 'Dz. Official League Baseballs',
     'description': 'Dozen regulation baseballs, full-grain leather, raised seams',
     'price': {'base': '29.00', 'A': '26.10', 'B': '24.65', 'C': '23.20'},
     'cost': {'standard': '12.50', 'avg': '12.50', 'currency': 'USD'},
     'kind': 'sale'},
    {'ida': 'qqdemo-BALL-02', 'name': 'Dz. Little League Baseballs',
     'description': 'Dozen Little League approved baseballs',
     'price': {'base': '8.00', 'A': '7.20', 'B': '6.80', 'C': '6.40'},
     'cost': {'standard': '4.00', 'avg': '4.00', 'currency': 'USD'},
     'kind': 'sale'},
    {'ida': 'qqdemo-BALL-03', 'name': 'Dz. Foam Practice Baseballs',
     'description': 'Dozen foam baseballs for indoor/youth practice',
     'price': {'base': '19.00', 'A': '17.10', 'B': '16.15', 'C': '15.20'},
     'cost': {'standard': '7.00', 'avg': '7.00', 'currency': 'USD'},
     'kind': 'sale'},

    # Gloves & gear
    {'ida': 'qqdemo-GLOVE-01', 'name': 'Wilson Fielders Glove 12"',
     'description': 'Full-grain leather, right-hand throw',
     'price': {'base': '43.99', 'A': '39.59', 'B': '37.39', 'C': '35.19'},
     'cost': {'standard': '11.00', 'avg': '11.00', 'currency': 'USD'},
     'kind': 'sale'},
    {'ida': 'qqdemo-GLOVE-02', 'name': 'Batting Gloves, Pair',
     'description': 'Synthetic leather batting gloves, adult sizes',
     'price': {'base': '15.99', 'A': '14.39', 'B': '13.59', 'C': '12.79'},
     'cost': {'standard': '5.00', 'avg': '5.00', 'currency': 'USD'},
     'kind': 'sale'},

    # Bags
    {'ida': 'qqdemo-BAG-01', 'name': 'Team Equipment Bag',
     'description': 'Oversized wheeled team equipment bag, holds 6 bats',
     'price': {'base': '79.00', 'A': '71.10', 'B': '67.15', 'C': '63.20'},
     'cost': {'standard': '32.00', 'avg': '32.00', 'currency': 'USD'},
     'kind': 'sale'},

    # Training
    {'ida': 'qqdemo-TRAIN-01', 'name': 'Spin-Right Spinner Pitching Aid',
     'description': 'Pitching training tool — teaches proper spin',
     'price': {'base': '21.95', 'A': '19.75', 'B': '18.65', 'C': '17.56'},
     'cost': {'standard': '9.00', 'avg': '9.00', 'currency': 'USD'},
     'kind': 'sale'},
    {'ida': 'qqdemo-SCREEN-01', 'name': '7x7 Baseball L-Screen with Net',
     'description': 'Protective L-screen, #36 pillowcase net, 8 bungees',
     'price': {'base': '200.00', 'A': '180.00', 'B': '170.00', 'C': '160.00'},
     'cost': {'standard': '85.00', 'avg': '85.00', 'currency': 'USD'},
     'kind': 'sale'},

    # Kit (BOM parent)
    {'ida': 'qqdemo-KIT-01', 'name': 'Little League Starter Kit',
     'description': 'Complete starter kit: bat, glove, batting gloves, dozen balls',
     'price': {'base': '69.99', 'A': '62.99', 'B': '59.49', 'C': '55.99'},
     'cost': {'standard': '26.78', 'avg': '26.78', 'currency': 'USD'},
     'kind': 'build'},
]

# BOM for the kit — references item idas
BOM_ENTRIES = [
    # parent_ida, child_ida, quantity
    ('qqdemo-KIT-01', 'qqdemo-BAT-03',   1),
    ('qqdemo-KIT-01', 'qqdemo-GLOVE-01', 1),
    ('qqdemo-KIT-01', 'qqdemo-GLOVE-02', 1),
    ('qqdemo-KIT-01', 'qqdemo-BALL-02',  1),
]

# ─── Customers ───────────────────────────────────────────────────────────
CUSTOMERS = [
    {'ida': 'qqdemo-CUST-01', 'display_name': 'Riverside Sports',
     'org_type': 'customer', 'price_level': 'B', 'terms': 'N30'},
    {'ida': 'qqdemo-CUST-02', 'display_name': 'Metro Baseball Academy',
     'org_type': 'customer', 'price_level': 'A', 'terms': 'N30'},
    {'ida': 'qqdemo-CUST-03', 'display_name': 'Eastside Little League',
     'org_type': 'customer', 'price_level': 'C', 'terms': 'N10'},
    {'ida': 'qqdemo-CUST-04', 'display_name': 'Diamond Pro Equipment',
     'org_type': 'customer', 'price_level': 'A', 'terms': '2pct10N30'},
    {'ida': 'qqdemo-CUST-05', 'display_name': 'Lincoln High School Athletics',
     'org_type': 'customer', 'price_level': 'B', 'terms': 'N30'},
]

# ─── Contacts (one per customer + 2 at vendor) ──────────────────────────
CONTACTS = [
    {'ida': 'qqdemo-CON-01', 'attention': 'Sarah Chen', 'email': 'sarah@qqdemo-riverside.example',
     'title': 'Buyer — Riverside Sports'},
    {'ida': 'qqdemo-CON-02', 'attention': 'Mike Rodriguez', 'email': 'mike@qqdemo-metroacademy.example',
     'title': 'Head Coach — Metro Baseball Academy'},
    {'ida': 'qqdemo-CON-03', 'attention': 'Karen Williams', 'email': 'karen@qqdemo-eastside-ll.example',
     'title': 'League President — Eastside Little League'},
    {'ida': 'qqdemo-CON-04', 'attention': 'Tom Baker', 'email': 'tom@qqdemo-diamondpro.example',
     'title': 'Purchasing — Diamond Pro Equipment'},
    {'ida': 'qqdemo-CON-05', 'attention': 'Pat Johnson', 'email': 'pat@qqdemo-lincolnhs.example',
     'title': 'Athletic Director — Lincoln High'},
    {'ida': 'qqdemo-CON-06', 'attention': 'Jim Douglas', 'email': 'jim@qqdemo-nbs.example',
     'title': 'Sales Rep — National Baseball Supply'},
    {'ida': 'qqdemo-CON-07', 'attention': 'Lisa Park', 'email': 'lisa@qqdemo-nbs.example',
     'title': 'Account Manager — National Baseball Supply'},
]

# ─── Vendor ──────────────────────────────────────────────────────────────
VENDOR = {
    'ida': 'qqdemo-VEND-01', 'display_name': 'National Baseball Supply',
    'org_type': 'vendor', 'terms': 'N30',
}


class Command(BaseCommand):
    help = 'Seed curated demo data: 12 items (with BOM), 5 customers, 1 vendor, 7 contacts'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true',
                            help='Delete existing demo data and re-seed')

    def handle(self, *args, **options):
        if options.get('force'):
            self._delete_demo()

        items_created = self._seed_items()
        bom_created = self._seed_bom()
        orgs_created = self._seed_orgs()
        contacts_created = self._seed_contacts()

        self.stdout.write(self.style.SUCCESS(
            f'\nDemo data: {items_created} items, {bom_created} BOM entries, '
            f'{orgs_created} orgs, {contacts_created} contacts'))

    def _delete_demo(self):
        from apps.products.models.bill_of_material import BillOfMaterial
        BillOfMaterial.objects.filter(parent_item__ida__startswith=DEMO_PREFIX).delete()
        Item.objects.filter(ida__startswith=DEMO_PREFIX).delete()
        OrgBase.objects.filter(ida__startswith=DEMO_PREFIX).delete()
        Contact.objects.filter(ida__startswith=DEMO_PREFIX).delete()
        self.stdout.write('Deleted existing demo data')

    def _seed_items(self):
        created = 0
        for it in ITEMS:
            if Item.objects.filter(ida=it['ida']).exists():
                continue
            Item.objects.create(
                ida=it['ida'],
                name=it['name'],
                description=it.get('description', ''),
                price=it.get('price', {}),
                cost=it.get('cost', {}),
                gls=ITEM_GLS,
                kind=it.get('kind', 'sale'),
                is_active=True,
            )
            created += 1
        self.stdout.write(f'  Items: {created} created, {len(ITEMS) - created} already exist')
        return created

    def _seed_bom(self):
        created = 0
        for parent_ida, child_ida, qty in BOM_ENTRIES:
            parent = Item.objects.filter(ida=parent_ida).first()
            child = Item.objects.filter(ida=child_ida).first()
            if not parent or not child:
                self.stdout.write(self.style.WARNING(
                    f'  BOM skip: {parent_ida} <- {child_ida} (item not found)'))
                continue
            if BillOfMaterial.objects.filter(parent_item=parent, child_item=child).exists():
                continue
            BillOfMaterial.objects.create(
                parent_item=parent,
                child_item=child,
                parent_ida=parent.ida,
                child_ida=child.ida,
                parent_description=parent.name,
                child_description=child.name,
                quantity=Decimal(str(qty)),
                sequence=created + 1,
                is_active=True,
            )
            created += 1
        self.stdout.write(f'  BOM: {created} entries created')
        return created

    def _seed_orgs(self):
        created = 0
        # Vendor
        if not OrgBase.objects.filter(ida=VENDOR['ida']).exists():
            OrgBase.objects.create(**VENDOR, is_active=True)
            created += 1
        # Customers
        for c in CUSTOMERS:
            if not OrgBase.objects.filter(ida=c['ida']).exists():
                OrgBase.objects.create(**c, is_active=True)
                created += 1
        self.stdout.write(f'  Orgs: {created} created (1 vendor + {len(CUSTOMERS)} customers)')
        return created

    def _seed_contacts(self):
        created = 0
        for c in CONTACTS:
            if not Contact.objects.filter(ida=c['ida']).exists():
                Contact.objects.create(**c, is_active=True)
                created += 1
        self.stdout.write(f'  Contacts: {created} created')
        return created
