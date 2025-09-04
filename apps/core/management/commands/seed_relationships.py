import random
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models.contact import Contact  # type: ignore
from apps.communications.models.email import Email  # type: ignore
from apps.communications.models.phone import Phone  # type: ignore
from apps.communications.models.location import Location  # type: ignore
from apps.communications.models.domain import Domain  # type: ignore
from apps.orgs.models.base_org_model import OrgBase  # type: ignore
from apps.transactions.models.line_variants import Order, OrderLine  # type: ignore

SAFE_MAX = 5000


ORG_TYPE_BUCKET_MAP = {
    'customer': 'customers',
    'vendor': 'vendors',
    'manufacturer': 'manufacturers',
    'rep': 'reps',
}

def ensure_links_container(refs):
    if not isinstance(refs, dict):
        refs = {}
    links = refs.setdefault('links', {})
    # Base buckets
    for bucket in ('emails', 'phones', 'locations', 'domains', 'contacts', 'orders', 'orgs', 'customers', 'vendors', 'manufacturers', 'reps', 'actions'):
        links.setdefault(bucket, [])
    return refs


def sample_ids(qs, target_count: int):
    if target_count <= 0:
        return []
    ids = list(qs.values_list('id', flat=True)[:SAFE_MAX])
    if not ids:
        return []
    if len(ids) <= target_count:
        return ids
    return random.sample(ids, target_count)


class Command(BaseCommand):
    help = "Enrich seeded data by randomly linking contacts to communication records, orgs, and orders."

    def add_arguments(self, parser):  # pragma: no cover
        parser.add_argument('--contacts', type=int, default=0)
        parser.add_argument('--per-contact-emails', type=int, default=2)
        parser.add_argument('--per-contact-phones', type=int, default=1)
        parser.add_argument('--per-contact-locations', type=int, default=1)
        parser.add_argument('--per-contact-domains', type=int, default=1)
        parser.add_argument('--org-contacts', type=int, default=3)
        parser.add_argument('--order-contact', action='store_true')
        parser.add_argument('--customer-order-links', action='store_true')
        parser.add_argument('--orderline-links', action='store_true')
        parser.add_argument('--refresh', action='store_true')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--auto-create-contacts', type=int, default=0)
        parser.add_argument('--ensure-contact-order-link', action='store_true')
        parser.add_argument('--ensure-contact-org-link', action='store_true')
        parser.add_argument('--prune-invalid-links', action='store_true', help='Remove link IDs that no longer exist.')

    def handle(self, *args, **opts):
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
        auto_create_contacts = max(0, opts.get('auto_create_contacts') or 0)
        ensure_contact_order_link = bool(opts.get('ensure_contact_order_link'))
        ensure_contact_org_link = bool(opts.get('ensure_contact_org_link'))
        prune_invalid_links = bool(opts.get('prune_invalid_links'))
        ensure_comm_fallbacks = True  # implicit for now; could be flag later

        created_contacts = 0
        existing_count = Contact.objects.count()
        if auto_create_contacts and existing_count < auto_create_contacts and not dry_run:
            for i in range(auto_create_contacts - existing_count):
                seq = existing_count + i + 1
                try:
                    Contact.objects.create_user(  # type: ignore[attr-defined]
                        email=f"seed{seq}@example.com",
                        password='1111pass',
                        name_first=f'Seed{seq}',
                        name_last='User',
                    )
                    created_contacts += 1
                except Exception:
                    pass

        contacts_qs = Contact.objects.order_by('id')
        if limit_contacts:
            contacts_qs = contacts_qs[:limit_contacts]
        contacts = list(contacts_qs)

        email_ids = sample_ids(Email.objects.all(), emails_per * max(1, len(contacts)))
        phone_ids = sample_ids(Phone.objects.all(), phones_per * max(1, len(contacts)))
        location_ids = sample_ids(Location.objects.all(), locs_per * max(1, len(contacts)))
        domain_ids = sample_ids(Domain.objects.all(), domains_per * max(1, len(contacts)))

        mut_contact = mut_org = mut_lines = mut_orders = mut_orderlines = mut_order_contact_links = mut_org_order_backlinks = mut_order_contact_aggregations = 0
        mut_contact_order_fallbacks = mut_contact_org_backlinks = mut_contact_org_fallbacks = pruned_links = 0
        mut_comm_fallbacks = 0

        def _model_has_field(obj, field_name: str) -> bool:
            try:
                return any(getattr(f, 'name', None) == field_name for f in obj._meta.get_fields())
            except Exception:
                return False

        def _safe_save_refs(obj, refs_dict: dict):
            if not _model_has_field(obj, 'refs'):
                return False
            try:
                setattr(obj, 'refs', refs_dict)
                obj.save(update_fields=['refs'])
                return True
            except Exception:
                return False

        with transaction.atomic():
            email_backlink_map: dict[int, list[int]] = {}
            phone_backlink_map: dict[int, list[int]] = {}
            location_backlink_map: dict[int, list[int]] = {}
            domain_backlink_map: dict[int, list[int]] = {}

            for c in contacts:
                refs = ensure_links_container(getattr(c, 'refs', {}) or {})
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
                    _safe_save_refs(c, refs)
                mut_contact += 1

            def backlink(model, mapping: dict[int, list[int]]):
                if not mapping:
                    return
                for obj in model.objects.filter(id__in=mapping.keys())[:SAFE_MAX]:
                    r = ensure_links_container(getattr(obj, 'refs', {}) or {})
                    contacts_list = r['links'].setdefault('contacts', [])
                    changed = False
                    oid = getattr(obj, 'id')
                    for cid in mapping.get(oid, []):
                        if cid not in contacts_list:
                            contacts_list.append(cid)
                            changed = True
                    if changed and not dry_run:
                        _safe_save_refs(obj, r)

            backlink(Email, email_backlink_map)
            backlink(Phone, phone_backlink_map)
            backlink(Location, location_backlink_map)
            backlink(Domain, domain_backlink_map)

            contact_org_map: dict[int, set[int]] = {}
            if org_contacts_n:
                pool_ids = [getattr(c, 'id') for c in contacts]
                for org in OrgBase.objects.all()[:SAFE_MAX]:
                    if not pool_ids:
                        break
                    existing_ids = set()
                    org_contacts = getattr(org, 'contacts', None)
                    if isinstance(org_contacts, list):
                        existing_ids = {e.get('id') for e in org_contacts if isinstance(e, dict)}
                    else:
                        org_contacts = []
                        setattr(org, 'contacts', org_contacts)
                    add_ids = random.sample(pool_ids, min(org_contacts_n, len(pool_ids)))
                    for cid in add_ids:
                        if cid in existing_ids:
                            continue
                        org_contacts.append({"id": cid, "name": "", "role": None})
                        contact_org_map.setdefault(cid, set()).add(getattr(org, 'id'))
                    if not dry_run:
                        try:
                            org.save(update_fields=['contacts', 'modified_dt', 'version'])
                        except Exception:
                            pass
                    mut_org += 1

            if contact_org_map:
                by_id = {getattr(c, 'id'): c for c in contacts}
                for cid, org_ids in contact_org_map.items():
                    c = by_id.get(cid)
                    if not c:
                        continue
                    refs = ensure_links_container(getattr(c, 'refs', {}) or {})
                    bucket_generic = refs['links'].setdefault('orgs', [])
                    changed = False
                    for oid in org_ids:
                        if oid not in bucket_generic:
                            bucket_generic.append(oid)
                            changed = True
                        # Also populate type-specific bucket
                        try:
                            org_type = OrgBase.objects.filter(id=oid).values_list('org_type', flat=True).first()
                        except Exception:
                            org_type = None
                        if org_type:
                            bucket_name = ORG_TYPE_BUCKET_MAP.get(str(org_type))
                        else:
                            bucket_name = None
                        if bucket_name:
                            tbucket = refs['links'].setdefault(bucket_name, [])
                            if oid not in tbucket:
                                tbucket.append(oid)
                                changed = True
                    if changed and not dry_run and _safe_save_refs(c, refs):
                        mut_contact_org_backlinks += 1

            if order_contact and contacts:
                pool_ids = [getattr(c, 'id') for c in contacts]
                for line in OrderLine.objects.select_related('parent').all()[:SAFE_MAX]:
                    source = getattr(line, 'source', None)
                    if not isinstance(source, dict):
                        continue
                    if refresh:
                        source.pop('contact_id', None)
                    if 'contact_id' not in source:
                        source['contact_id'] = random.choice(pool_ids)
                        if not dry_run:
                            try:
                                setattr(line, 'source', source)
                                line.save(update_fields=['source'])
                            except Exception:
                                pass
                        mut_lines += 1

            if customer_order_links:
                customer_org_ids = list(OrgBase.objects.filter(org_type='customer').values_list('id', flat=True)[:SAFE_MAX])
                if customer_org_ids:
                    for order in Order.objects.all()[:SAFE_MAX]:
                        refs = ensure_links_container(getattr(order, 'refs', {}) or {})
                        links = refs['links']
                        if refresh:
                            links.setdefault('orgs', [])
                            links['orgs'].clear()
                            links.setdefault('customers', [])
                            links['customers'].clear()
                        if not links.get('orgs'):
                            chosen_org = random.choice(customer_org_ids)
                            links.setdefault('orgs', []).append(chosen_org)
                            # also add to customers bucket
                            links.setdefault('customers', []).append(chosen_org)
                            try:
                                org_obj = OrgBase.objects.filter(id=chosen_org).only('refs').first()
                                if org_obj:
                                    orefs = ensure_links_container(getattr(org_obj, 'refs', {}) or {})
                                    olinks = orefs['links']
                                    if getattr(order, 'id') not in olinks.setdefault('orders', []):
                                        olinks['orders'].append(getattr(order, 'id'))
                                        if not dry_run:
                                            _safe_save_refs(org_obj, orefs)
                                        mut_org_order_backlinks += 1
                            except Exception:
                                pass
                            if not dry_run:
                                _safe_save_refs(order, refs)
                            mut_orders += 1

            if orderline_links:
                for line in OrderLine.objects.select_related('parent').all()[:SAFE_MAX]:
                    refs = ensure_links_container(getattr(line, 'refs', {}) or {})
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
                                crefs = ensure_links_container(getattr(contact_obj, 'refs', {}) or {})
                                clinks = crefs['links']
                                if parent_id and parent_id not in clinks.setdefault('orders', []):
                                    clinks['orders'].append(parent_id)
                                    if not dry_run:
                                        _safe_save_refs(contact_obj, crefs)
                                    mut_order_contact_links += 1
                        except Exception:
                            pass
                    if parent_id and cid:
                        try:
                            order_obj = Order.objects.filter(id=parent_id).only('refs').first()
                            if order_obj:
                                orefs = ensure_links_container(getattr(order_obj, 'refs', {}) or {})
                                olinks = orefs['links']
                                if cid not in olinks.setdefault('contacts', []):
                                    olinks['contacts'].append(cid)
                                    if not dry_run:
                                        _safe_save_refs(order_obj, orefs)
                                    mut_order_contact_aggregations += 1
                        except Exception:
                            pass
                    if (parent_id or cid) and not dry_run and _model_has_field(line, 'refs'):
                        _safe_save_refs(line, refs)
                    mut_orderlines += 1

            if dry_run:
                transaction.set_rollback(True)

            # Communication/action fallback now inside transaction for atomicity
            if not dry_run and ensure_comm_fallbacks:
                from apps.core.models.action import Action
                def ensure_min(model, create_kwargs):
                    if model.objects.count() == 0:
                        try:
                            model.objects.create(**create_kwargs)
                        except Exception:
                            pass
                    return list(model.objects.values_list('id', flat=True)[:SAFE_MAX])
                email_pool = ensure_min(Email, {'email': 'seed@example.com'})
                phone_pool = ensure_min(Phone, {'phone': '555-0000'})
                location_pool = ensure_min(Location, {'address': '100 Seed St'})
                domain_pool = ensure_min(Domain, {'domain': 'example.com'})
                action_pool = ensure_min(Action, {'action': 'Seed Action'})
                import random as _r
                for c in contacts:
                    refs = ensure_links_container(getattr(c, 'refs', {}) or {})
                    links = refs['links']
                    changed = False
                    if not links.get('emails') and email_pool:
                        links['emails'].append(_r.choice(email_pool)); changed = True
                    if not links.get('phones') and phone_pool:
                        links['phones'].append(_r.choice(phone_pool)); changed = True
                    if not links.get('locations') and location_pool:
                        links['locations'].append(_r.choice(location_pool)); changed = True
                    if not links.get('domains') and domain_pool:
                        links['domains'].append(_r.choice(domain_pool)); changed = True
                    if not links.get('actions') and action_pool:
                        links.setdefault('actions', []).append(_r.choice(action_pool)); changed = True
                    if changed:
                        if _safe_save_refs(c, refs):
                            mut_comm_fallbacks += 1

        if ensure_contact_order_link and not dry_run:
            try:
                order_ids = list(Order.objects.values_list('id', flat=True)[:SAFE_MAX])
                if order_ids:
                    for c in contacts:
                        refs = ensure_links_container(getattr(c, 'refs', {}) or {})
                        if not refs['links'].get('orders'):
                            refs['links']['orders'].append(random.choice(order_ids))
                            if _safe_save_refs(c, refs):
                                mut_contact_order_fallbacks += 1
            except Exception:
                pass

        if ensure_contact_org_link and not dry_run:
            try:
                org_ids = list(OrgBase.objects.values_list('id', flat=True)[:SAFE_MAX])
                if org_ids:
                    for c in contacts:
                        refs = ensure_links_container(getattr(c, 'refs', {}) or {})
                        if not refs['links'].get('orgs'):
                            chosen = random.choice(org_ids)
                            refs['links']['orgs'].append(chosen)
                            # type-specific bucket
                            org_type = OrgBase.objects.filter(id=chosen).values_list('org_type', flat=True).first()
                            bucket_name = ORG_TYPE_BUCKET_MAP.get(str(org_type)) if org_type else None
                            if bucket_name:
                                refs['links'].setdefault(bucket_name, []).append(chosen)
                            if _safe_save_refs(c, refs):
                                mut_contact_org_fallbacks += 1
            except Exception:
                pass

        if prune_invalid_links and not dry_run:
            try:
                existing = {
                    'orders': set(Order.objects.values_list('id', flat=True)),
                    'orgs': set(OrgBase.objects.values_list('id', flat=True)),
                    'emails': set(Email.objects.values_list('id', flat=True)),
                    'phones': set(Phone.objects.values_list('id', flat=True)),
                    'domains': set(Domain.objects.values_list('id', flat=True)),
                    'locations': set(Location.objects.values_list('id', flat=True)),
                    'contacts': set(Contact.objects.values_list('id', flat=True)),
                    'customers': set(OrgBase.objects.filter(org_type='customer').values_list('id', flat=True)),
                    'vendors': set(OrgBase.objects.filter(org_type='vendor').values_list('id', flat=True)),
                    'manufacturers': set(OrgBase.objects.filter(org_type='manufacturer').values_list('id', flat=True)),
                    'reps': set(OrgBase.objects.filter(org_type='rep').values_list('id', flat=True)),
                    'actions': set(),  # optional until we add reverse backlinks
                }
                for c in contacts:
                    refs = ensure_links_container(getattr(c, 'refs', {}) or {})
                    links = refs['links']
                    changed = False
                    for bucket, id_list in links.items():
                        if bucket not in existing or not isinstance(id_list, list):
                            continue
                        before = len(id_list)
                        id_list[:] = [i for i in id_list if i in existing[bucket]]
                        after = len(id_list)
                        if after < before:
                            pruned_links += (before - after)
                            changed = True
                    if changed:
                        _safe_save_refs(c, refs)
            except Exception:
                pass

        self.stdout.write(self.style.SUCCESS(
            "seed_relationships: "
            f"contacts={mut_contact}, orgs={mut_org}, order_line_contacts={mut_lines}, "
            f"orders_linked={mut_orders}, orderlines_enriched={mut_orderlines}, "
            f"order_contact_backlinks={mut_order_contact_links}, org_order_backlinks={mut_org_order_backlinks}, "
            f"contact_org_backlinks={mut_contact_org_backlinks}, order_contact_aggregations={mut_order_contact_aggregations}, "
            f"created_contacts={created_contacts}, contact_order_fallbacks={mut_contact_order_fallbacks}, contact_org_fallbacks={mut_contact_org_fallbacks}, comm_fallbacks={mut_comm_fallbacks}, pruned_links={pruned_links} (dry_run={dry_run})"
        ))
