import random
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import QuerySet

from django.apps import apps

# We dynamically load models to avoid tight coupling and circular imports
Contact = apps.get_model('core', 'Contact')
Email = apps.get_model('communications', 'Email')
Phone = apps.get_model('communications', 'Phone')
Location = apps.get_model('communications', 'Location')
Domain = apps.get_model('communications', 'Domain')
OrgBase = apps.get_model('orgs', 'OrgBase')
Order = apps.get_model('transactions', 'Order')
OrderLine = apps.get_model('transactions', 'OrderLine')

SAFE_MAX = 5000  # safety cap for bulk iteration


def sample_ids(qs: QuerySet, limit: int) -> list[int]:
    ids = list(qs.values_list('id', flat=True)[:SAFE_MAX])
    if not ids:
        return []
    random.shuffle(ids)
    return ids[:limit]


def ensure_links_container(refs: dict) -> dict:
    if refs is None:
        refs = {}
    links = refs.setdefault('links', {})
    # Standard buckets + newer ones used here
    for key in ('contacts', 'emails', 'phones', 'locations', 'domains', 'orders', 'orgs'):
        links.setdefault(key, [])
    refs.setdefault('related_ids', refs.get('related_ids', []))
    refs.setdefault('keywords', refs.get('keywords', []))
    refs.setdefault('tags', refs.get('tags', []))
    return refs


class Command(BaseCommand):
    help = "Enrich seeded data by randomly linking contacts to communication records, orgs, and orders."

    def add_arguments(self, parser):  # pragma: no cover - CLI wiring
        parser.add_argument('--contacts', type=int, default=0, help='Limit number of contacts processed (0=all).')
        parser.add_argument('--per-contact-emails', type=int, default=2)
        parser.add_argument('--per-contact-phones', type=int, default=1)
        parser.add_argument('--per-contact-locations', type=int, default=1)
        parser.add_argument('--per-contact-domains', type=int, default=1)
        parser.add_argument('--org-contacts', type=int, default=3, help='Contacts to inject into each org (sampled).')
        parser.add_argument('--order-contact', action='store_true', help='Attach a random contact id to order lines (source.contact_id).')
        parser.add_argument('--customer-order-links', action='store_true', help='Link orders to a random customer org (refs.links.orgs) and backfill org refs.links.orders.')
        parser.add_argument('--orderline-links', action='store_true', help='Ensure orderlines get refs.links.orders and contact link propagation.')
        parser.add_argument('--refresh', action='store_true', help='Clear existing link arrays before adding.')
        parser.add_argument('--dry-run', action='store_true', help='Report actions without saving.')

    def handle(self, *args, **opts):
        # --- Parse options ---
        limit_contacts = max(0, opts['contacts'])
        emails_per = max(0, opts['per_contact_emails'])
        phones_per = max(0, opts['per_contact_phones'])
        locs_per = max(0, opts['per_contact_locations'])
        domains_per = max(0, opts['per_contact_domains'])
        org_contacts_n = max(0, opts['org_contacts'])
        order_contact = bool(opts['order_contact'])
        customer_order_links = bool(opts['customer_order_links'])
        orderline_links = bool(opts['orderline_links'])
        refresh = bool(opts['refresh'])
        dry_run = bool(opts['dry_run'])

        # --- Collect primary objects ---
        contacts_qs = Contact.objects.order_by('id')
        if limit_contacts:
            contacts_qs = contacts_qs[:limit_contacts]
        contacts = list(contacts_qs)

        email_ids = sample_ids(Email.objects.all(), emails_per * max(1, len(contacts)))
        phone_ids = sample_ids(Phone.objects.all(), phones_per * max(1, len(contacts)))
        location_ids = sample_ids(Location.objects.all(), locs_per * max(1, len(contacts)))
        domain_ids = sample_ids(Domain.objects.all(), domains_per * max(1, len(contacts)))

        mut_contact = mut_org = mut_lines = mut_orders = mut_orderlines = mut_order_contact_links = mut_org_order_backlinks = 0

        with transaction.atomic():
            # --- Enrich contacts and capture backlink maps ---
            email_backlink_map: dict[int, list[int]] = {}
            phone_backlink_map: dict[int, list[int]] = {}
            location_backlink_map: dict[int, list[int]] = {}
            domain_backlink_map: dict[int, list[int]] = {}

            for c in contacts:
                refs = ensure_links_container(getattr(c, 'refs', {}) or {})  # type: ignore[attr-defined]
                links = refs['links']
                if refresh:
                    for arr in links.values():
                        arr.clear()

                def add_some(bucket: str, pool: list[int], take: int):
                    if not pool or take <= 0:
                        return []
                    chosen = random.sample(pool, min(take, len(pool)))
                    for pk in chosen:
                        if pk not in links[bucket]:
                            links[bucket].append(pk)
                    return chosen

                chosen_emails = add_some('emails', email_ids, emails_per)
                chosen_phones = add_some('phones', phone_ids, phones_per)
                chosen_locations = add_some('locations', location_ids, locs_per)
                chosen_domains = add_some('domains', domain_ids, domains_per)

                cid = getattr(c, 'id')
                for eid in chosen_emails:
                    email_backlink_map.setdefault(eid, []).append(cid)
                for pid in chosen_phones:
                    phone_backlink_map.setdefault(pid, []).append(cid)
                for lid in chosen_locations:
                    location_backlink_map.setdefault(lid, []).append(cid)
                for did in chosen_domains:
                    domain_backlink_map.setdefault(did, []).append(cid)

                if not dry_run:
                    setattr(c, 'refs', refs)  # type: ignore[attr-defined]
                    c.save(update_fields=['refs'])  # type: ignore[arg-type]
                mut_contact += 1

            # --- Backlink communications to contacts ---
            def backlink(model, mapping: dict[int, list[int]]):
                if not mapping:
                    return
                objs = list(model.objects.filter(id__in=mapping.keys())[:SAFE_MAX])
                for obj in objs:
                    r = ensure_links_container(getattr(obj, 'refs', {}) or {})  # type: ignore[attr-defined]
                    contacts_list = r['links'].setdefault('contacts', [])
                    changed = False
                    oid = getattr(obj, 'id')
                    for cid in mapping.get(oid, []):
                        if cid not in contacts_list:
                            contacts_list.append(cid)
                            changed = True
                    if changed and not dry_run:
                        setattr(obj, 'refs', r)  # type: ignore[attr-defined]
                        obj.save(update_fields=['refs'])  # type: ignore[arg-type]

            backlink(Email, email_backlink_map)
            backlink(Phone, phone_backlink_map)
            backlink(Location, location_backlink_map)
            backlink(Domain, domain_backlink_map)

            # --- Org contact list enrichment ---
            if org_contacts_n:
                contact_ids_pool = [getattr(c, 'id') for c in contacts]
                for org in OrgBase.objects.all()[:SAFE_MAX]:
                    if not contact_ids_pool:
                        break
                    existing_ids = set()
                    org_contacts = getattr(org, 'contacts', None)  # type: ignore[attr-defined]
                    if isinstance(org_contacts, list):
                        existing_ids = {e.get('id') for e in org_contacts if isinstance(e, dict)}
                    else:
                        org_contacts = []
                        setattr(org, 'contacts', org_contacts)  # type: ignore[attr-defined]
                    add_ids = random.sample(contact_ids_pool, min(org_contacts_n, len(contact_ids_pool)))
                    for cid in add_ids:
                        if cid in existing_ids:
                            continue
                        org_contacts.append({"id": cid, "name": "", "role": None})  # type: ignore[attr-defined]
                    if not dry_run:
                        org.save(update_fields=['contacts', 'modified_dt', 'version'])  # type: ignore[arg-type]
                    mut_org += 1

            # --- Order line: attach contact_id into source ---
            if order_contact and contacts:
                contact_ids_pool = [getattr(c, 'id') for c in contacts]
                for line in OrderLine.objects.select_related('parent').all()[:SAFE_MAX]:  # type: ignore[attr-defined]
                    source = getattr(line, 'source', None)
                    if not isinstance(source, dict):
                        continue
                    if refresh:
                        source.pop('contact_id', None)
                    if 'contact_id' not in source:
                        source['contact_id'] = random.choice(contact_ids_pool)
                        if not dry_run:
                            setattr(line, 'source', source)
                            line.save(update_fields=['source'])  # type: ignore[arg-type]
                        mut_lines += 1

            # --- Orders -> customer orgs & backlinks ---
            if customer_order_links:
                customer_org_ids = list(OrgBase.objects.filter(org_type='customer').values_list('id', flat=True)[:SAFE_MAX])
                if customer_org_ids:
                    for order in Order.objects.all()[:SAFE_MAX]:  # type: ignore[attr-defined]
                        refs = ensure_links_container(getattr(order, 'refs', {}) or {})  # type: ignore[attr-defined]
                        links = refs['links']
                        if refresh:
                            links.setdefault('orgs', [])
                            links['orgs'].clear()
                        if not links.get('orgs'):
                            chosen_org = random.choice(customer_org_ids)
                            links.setdefault('orgs', []).append(chosen_org)
                            try:
                                org_obj = OrgBase.objects.filter(id=chosen_org).only('refs').first()
                                if org_obj:
                                    orefs = ensure_links_container(getattr(org_obj, 'refs', {}) or {})  # type: ignore[attr-defined]
                                    olinks = orefs['links']
                                    if getattr(order, 'id') not in olinks.setdefault('orders', []):
                                        olinks['orders'].append(getattr(order, 'id'))
                                        if not dry_run:
                                            setattr(org_obj, 'refs', orefs)  # type: ignore[attr-defined]
                                            org_obj.save(update_fields=['refs'])  # type: ignore[arg-type]
                                        mut_org_order_backlinks += 1
                            except Exception:
                                pass
                            if not dry_run:
                                setattr(order, 'refs', refs)  # type: ignore[attr-defined]
                                order.save(update_fields=['refs'])  # type: ignore[arg-type]
                            mut_orders += 1

            # --- OrderLine propagation (orders & contacts) ---
            if orderline_links:
                for line in OrderLine.objects.select_related('parent').all()[:SAFE_MAX]:  # type: ignore[attr-defined]
                    refs = ensure_links_container(getattr(line, 'refs', {}) or {})  # type: ignore[attr-defined]
                    links = refs['links']
                    if refresh:
                        links.setdefault('orders', [])
                        links['orders'].clear()
                    parent_id = getattr(getattr(line, 'parent', None), 'id', None)
                    if parent_id and parent_id not in links.setdefault('orders', []):
                        links['orders'].append(parent_id)
                    source = getattr(line, 'source', None)
                    cid = source.get('contact_id') if isinstance(source, dict) else None
                    if cid and cid not in links.setdefault('contacts', []):
                        links['contacts'].append(cid)
                        try:
                            contact_obj = Contact.objects.filter(id=cid).only('refs').first()
                            if contact_obj:
                                crefs = ensure_links_container(getattr(contact_obj, 'refs', {}) or {})  # type: ignore[attr-defined]
                                clinks = crefs['links']
                                if parent_id and parent_id not in clinks.setdefault('orders', []):
                                    clinks['orders'].append(parent_id)
                                    if not dry_run:
                                        setattr(contact_obj, 'refs', crefs)  # type: ignore[attr-defined]
                                        contact_obj.save(update_fields=['refs'])  # type: ignore[arg-type]
                                    mut_order_contact_links += 1
                        except Exception:
                            pass
                    if (parent_id or cid) and not dry_run:
                        setattr(line, 'refs', refs)  # type: ignore[attr-defined]
                        line.save(update_fields=['refs'])  # type: ignore[arg-type]
                        mut_orderlines += 1

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(
            "seed_relationships: "
            f"contacts={mut_contact}, orgs={mut_org}, order_line_contacts={mut_lines}, "
            f"orders_linked={mut_orders}, orderlines_enriched={mut_orderlines}, "
            f"order_contact_backlinks={mut_order_contact_links}, org_order_backlinks={mut_org_order_backlinks} "
            f"(dry_run={dry_run})"
        ))
