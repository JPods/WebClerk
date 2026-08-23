#!/usr/bin/env python3
"""
seed_demo_cast.py — Standard demo/training dataset.

Seeds the "qq" cast: 5 contacts, each with exactly 4 of every child type.
Uses BB (baseball) items for transactions. Rule of 4: if you see 4 records,
the FK works. If you see more, records are leaking.

Run:
  python manage.py shell < tools/seed_demo_cast.py
  # or
  python manage.py shell -c "exec(open('tools/seed_demo_cast.py').read())"

Cast:
  qq_1  Sarah Chen      Riverside Sports        (buyer)
  qq_2  Mike Rodriguez  Metro Baseball Academy  (academy/coach)
  qq_3  Tom Parker      Eastside Little League  (volunteer)
  qq_4  Lisa Wang       Diamond Pro Equipment   (vendor/supplier)
  qq_5  Bill Smith      Riverside Sports        (owner)

Design rules:
  - Exactly 4 of each child type per contact (emails, phones, addresses, domains, documents)
  - Two contacts share the same company (Sarah + Bill → Riverside Sports)
  - qq_4 (Lisa Wang) is a vendor — tests customer vs vendor org relationships
  - ida prefix 'qq_' makes them easy to find and filter
  - BB items are real baseball equipment — realistic for training
"""

import sys
import os

# Ensure Django is set up
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webclerk3_api.settings')
import django
django.setup()

from apps.core.models import Contact
from apps.communications.models import Email, Phone, Address, Domain
from apps.docs.models import Document
from apps.orgs.models import OrgBase

# ── Cast definitions ──────────────────────────────────────────────────────────

CAST = [
    {
        'ida': 'qq_1',
        'name_first': 'Sarah', 'name_last': 'Chen',
        'company': 'Riverside Sports',
        'emails': [
            ('sarah@riversidesports.com', 'Work'),
            ('sarah.chen@gmail.com', 'Personal'),
            ('schen@riverside-purchasing.com', 'Purchasing'),
            ('sarah@tulsa-softball.org', 'League'),
        ],
        'phones': [
            ('(918) 555-1234', 'Mobile'),
            ('(918) 555-1200', 'Office'),
            ('(918) 555-1201', 'Fax'),
            ('(918) 555-1202', 'Warehouse'),
        ],
        'addresses': [
            ('2100 S Yale Ave', '', 'Tulsa', 'OK', '74114', 'Office'),
            ('4521 E 41st St', 'Suite 200', 'Tulsa', 'OK', '74135', 'Warehouse'),
            ('8901 S Memorial Dr', '', 'Tulsa', 'OK', '74133', 'Home'),
            ('PO Box 1234', '', 'Tulsa', 'OK', '74101', 'Billing'),
        ],
        'domains': [
            ('riversidesports.com', 'website'),
            ('linkedin.com/in/sarahchen', 'linkedin'),
            ('instagram.com/riverside_sports', 'social'),
            ('riversidesports.square.site', 'store'),
        ],
        'docs': ['Purchase Order 2026-001', 'Vendor Agreement', 'Tax Exempt Certificate', 'Return Policy Signed'],
    },
    {
        'ida': 'qq_2',
        'name_first': 'Mike', 'name_last': 'Rodriguez',
        'company': 'Metro Baseball Academy',
        'emails': [
            ('mike@metrobaseball.com', 'Work'),
            ('mrodriguez@okstate.edu', 'Alumni'),
            ('mike.r@outlook.com', 'Personal'),
            ('billing@metrobaseball.com', 'Billing'),
        ],
        'phones': [
            ('(405) 555-9876', 'Mobile'),
            ('(405) 555-9800', 'Academy'),
            ('(405) 555-9801', 'Pro Shop'),
            ('(918) 555-0099', 'Home'),
        ],
        'addresses': [
            ('7700 NW Expressway', '', 'Oklahoma City', 'OK', '73132', 'Academy'),
            ('1200 N Walker Ave', '', 'Oklahoma City', 'OK', '73103', 'Downtown Office'),
            ('3301 S Boulevard', 'Bldg C', 'Edmond', 'OK', '73013', 'Warehouse'),
            ('PO Box 5678', '', 'Oklahoma City', 'OK', '73101', 'Billing'),
        ],
        'domains': [
            ('metrobaseball.com', 'website'),
            ('facebook.com/metrobaseballacademy', 'social'),
            ('linkedin.com/in/mikerodriguez', 'linkedin'),
            ('youtube.com/@metrobaseball', 'youtube'),
        ],
        'docs': ['Coaching License', 'Facility Lease Agreement', 'Insurance Certificate', 'Equipment Inventory'],
    },
    {
        'ida': 'qq_3',
        'name_first': 'Tom', 'name_last': 'Parker',
        'company': 'Eastside Little League',
        'emails': [
            ('tom@eastsidell.org', 'League'),
            ('tparker@bankoftulsa.com', 'Day Job'),
            ('tom.parker.tulsa@gmail.com', 'Personal'),
            ('registrar@eastsidell.org', 'Registrar'),
        ],
        'phones': [
            ('(918) 555-7890', 'Mobile'),
            ('(918) 555-7800', 'League Office'),
            ('(918) 555-4400', 'Bank Office'),
            ('(918) 555-7891', 'Field House'),
        ],
        'addresses': [
            ('4800 E 15th St', '', 'Tulsa', 'OK', '74112', 'League Field'),
            ('1901 S Boston Ave', 'Floor 3', 'Tulsa', 'OK', '74119', 'Day Job'),
            ('6234 E 31st St', '', 'Tulsa', 'OK', '74135', 'Home'),
            ('4800 E 15th St', 'Equipment Shed', 'Tulsa', 'OK', '74112', 'Storage'),
        ],
        'domains': [
            ('eastsidell.org', 'website'),
            ('facebook.com/eastsidelittleleague', 'social'),
            ('eastsidell.teamsnap.com', 'scheduling'),
            ('twitter.com/eastsidell', 'social'),
        ],
        'docs': ['League Charter', 'Field Use Permit', 'Sponsorship Agreement', 'Season Schedule 2026'],
    },
    {
        'ida': 'qq_4',
        'name_first': 'Lisa', 'name_last': 'Wang',
        'company': 'Diamond Pro Equipment',
        'emails': [
            ('lisa@diamondpro.com', 'Work'),
            ('sales@diamondpro.com', 'Sales'),
            ('lisa.wang.dfw@gmail.com', 'Personal'),
            ('returns@diamondpro.com', 'Returns'),
        ],
        'phones': [
            ('(214) 555-3456', 'Mobile'),
            ('(214) 555-3400', 'Office'),
            ('(214) 555-3401', 'Showroom'),
            ('(800) 555-3776', 'Toll Free'),
        ],
        'addresses': [
            ('1500 Marilla St', 'Suite 400', 'Dallas', 'TX', '75201', 'Office'),
            ('8200 N Stemmons Fwy', 'Warehouse B', 'Dallas', 'TX', '75247', 'Warehouse'),
            ('3100 McKinney Ave', 'Apt 12B', 'Dallas', 'TX', '75204', 'Home'),
            ('1500 Marilla St', 'Suite 100', 'Dallas', 'TX', '75201', 'Showroom'),
        ],
        'domains': [
            ('diamondpro.com', 'website'),
            ('diamondpro.com/shop', 'store'),
            ('linkedin.com/company/diamond-pro', 'linkedin'),
            ('instagram.com/diamondproequip', 'social'),
        ],
        'docs': ['Product Catalog 2026', 'Distribution Agreement', 'Price List Q3', 'Warranty Terms'],
    },
    {
        'ida': 'qq_5',
        'name_first': 'Bill', 'name_last': 'Smith',
        'company': 'Riverside Sports',
        'emails': [
            ('bsmith@riversidesports.com', 'Work'),
            ('bill.smith@yahoo.com', 'Personal'),
            ('bsmith@tulsa-rotary.org', 'Rotary'),
            ('owner@riversidesports.com', 'Owner'),
        ],
        'phones': [
            ('(918) 555-4567', 'Mobile'),
            ('(918) 555-1200', 'Store'),
            ('(918) 555-4568', 'Home'),
            ('(918) 555-1203', 'Direct'),
        ],
        'addresses': [
            ('2100 S Yale Ave', '', 'Tulsa', 'OK', '74114', 'Store'),
            ('7890 S Lewis Ave', '', 'Tulsa', 'OK', '74136', 'Home'),
            ('2100 S Yale Ave', 'Back Office', 'Tulsa', 'OK', '74114', 'Office'),
            ('PO Box 9999', '', 'Tulsa', 'OK', '74101', 'Billing'),
        ],
        'domains': [
            ('riversidesports.com', 'website'),
            ('linkedin.com/in/billsmith-tulsa', 'linkedin'),
            ('nextdoor.com/riverside-sports', 'community'),
            ('yelp.com/biz/riverside-sports-tulsa', 'review'),
        ],
        'docs': ['Store Lease', 'Business License', 'Vendor Application', 'Credit Terms Agreement'],
    },
]


# ── Seed logic ────────────────────────────────────────────────────────────────

def seed_contact(spec):
    """Create or update a contact and seed exactly 4 of each child type."""
    ida = spec['ida']

    # Find or create contact (DB fields: name_first, name_last, company)
    c = Contact.objects.filter(ida=ida).first()
    if not c:
        c = Contact.objects.filter(
            name_first=spec['name_first'],
            name_last=spec['name_last'],
            company=spec['company'],
        ).first()
    if not c:
        c = Contact.objects.create(
            ida=ida,
            name_first=spec['name_first'],
            name_last=spec['name_last'],
            company=spec['company'],
        )
    else:
        c.ida = ida
        c.name_first = spec['name_first']
        c.name_last = spec['name_last']
        c.company = spec['company']
        c.save(update_fields=['ida', 'name_first', 'name_last', 'company', 'dt_modified'])

    # ── Emails: exactly 4 ──
    existing = set(Email.objects.filter(contact=c).values_list('email', flat=True))
    for email, name in spec['emails']:
        if email not in existing:
            Email.objects.create(contact=c, email=email, name=name)
    # Trim to 4 if over
    for e in Email.objects.filter(contact=c).order_by('id')[4:]:
        e.delete()

    # ── Phones: exactly 4 ──
    existing = set(Phone.objects.filter(contact=c).values_list('number', flat=True))
    for number, name in spec['phones']:
        if number not in existing:
            Phone.objects.create(contact=c, number=number, name=name)
    for p in Phone.objects.filter(contact=c).order_by('id')[4:]:
        p.delete()

    # ── Addresses: exactly 4 ──
    count = Address.objects.filter(contact=c).count()
    for i, (a1, a2, city, state, z, atype) in enumerate(spec['addresses']):
        if i >= count:
            Address.objects.create(
                contact=c, address1=a1, address2=a2,
                city=city, state=state, zip=z, address_type=atype,
            )
    for a in Address.objects.filter(contact=c).order_by('id')[4:]:
        a.delete()

    # ── Domains: exactly 4 ──
    existing = set(Domain.objects.filter(contact=c).values_list('path', flat=True))
    for path, dtype in spec['domains']:
        if path not in existing:
            Domain.objects.create(contact=c, path=path, type=dtype)
    for d in Domain.objects.filter(contact=c).order_by('id')[4:]:
        d.delete()

    # ── Documents: exactly 4, linked via refs ──
    c_refs = c.refs or {}
    c_links = c_refs.setdefault('links', {})
    existing_docs = c_links.get('document', [])

    if len(existing_docs) < 4:
        for doc_name in spec['docs'][len(existing_docs):]:
            doc = Document.objects.create(
                name=f"{spec['company']} — {doc_name}",
                description=f"{doc_name} for {spec['name_first']} {spec['name_last']}",
                status='active', purpose='general',
            )
            doc.refs = {'links': {'contacts': [{'id': c.id, 'model': 'contact'}]}}
            doc.save(update_fields=['refs'])
            existing_docs.append({'id': doc.id, 'name': doc.name})
        c_links['document'] = existing_docs[:4]

    # ── Company org link ──
    org = OrgBase.objects.filter(display_name=spec['company'], org_type='customer').first()
    if not org:
        org = OrgBase.objects.create(display_name=spec['company'], org_type='customer', is_active=True)
    c_links['customer'] = {'id': org.id, 'company': spec['company'], 'model': 'customer'}

    c.refs = c_refs
    c.save(update_fields=['refs'])

    return c


# ── Run ───────────────────────────────────────────────────────────────────────

print("Seeding demo cast (Rule of 4)...")
for spec in CAST:
    c = seed_contact(spec)
    e = Email.objects.filter(contact=c).count()
    p = Phone.objects.filter(contact=c).count()
    a = Address.objects.filter(contact=c).count()
    d = Domain.objects.filter(contact=c).count()
    docs = len((c.refs or {}).get('links', {}).get('document', []))
    print(f"  {c.ida:<6} {c.name_first:<8} {c.name_last:<12} {c.company:<25} e={e} p={p} a={a} d={d} docs={docs}")

print("\nDone. Open any qq_ contact — you should see exactly 4 of each type.")
print("If you see more, a FK is leaking. If you see fewer, seeding was incomplete.")
