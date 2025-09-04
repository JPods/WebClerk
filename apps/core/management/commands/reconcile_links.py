import random
from django.core.management.base import BaseCommand
from django.db import transaction
from django.apps import apps

Contact = apps.get_model('core', 'Contact')
Email = apps.get_model('communications', 'Email')
Phone = apps.get_model('communications', 'Phone')
Location = apps.get_model('communications', 'Location')
Domain = apps.get_model('communications', 'Domain')

COMM_MAP = {
    'emails': Email,
    'phones': Phone,
    'locations': Location,
    'domains': Domain,
}

class Command(BaseCommand):
    help = "Reconcile reciprocal refs.links.* between contacts and communication objects (contacts authoritative)."

    def add_arguments(self, parser):  # pragma: no cover
        parser.add_argument('--batch', type=int, default=500, help='Batch size for contact iteration.')
        parser.add_argument('--limit', type=int, default=0, help='Process at most N contacts (0 = all).')
        parser.add_argument('--prune', action='store_true', help='Remove orphan contact ids from communication objects.')
        parser.add_argument('--dry-run', action='store_true', help='Do not persist changes.')

    def handle(self, *args, **opts):
        batch = max(1, opts['batch'])
        limit = max(0, opts['limit'])
        prune = opts['prune']
        dry = opts['dry_run']

        contacts_qs = Contact.objects.all().order_by('id')
        if limit:
            contacts_qs = contacts_qs[:limit]

        processed = 0
        comm_updates = 0
        pruned = 0

        # Build inverse index for pruning (optional heavy) only if prune requested
        # We'll lazily gather contact->ids first; then for prune phase we scan comm objects touched.
        with transaction.atomic():
            for start in range(0, contacts_qs.count(), batch):
                chunk = list(contacts_qs[start:start+batch])
                if not chunk:
                    break
                processed += len(chunk)
                # Map of model -> {id: set(contact_ids)} to update after pass
                pending: dict[str, dict[int, set[int]]] = {k: {} for k in COMM_MAP.keys()}
                for c in chunk:
                    refs = getattr(c, 'refs', {}) or {}
                    links = refs.get('links', {}) if isinstance(refs, dict) else {}
                    for bucket, model in COMM_MAP.items():
                        ids = links.get(bucket) or []
                        if not isinstance(ids, list):
                            continue
                        for obj_id in ids:
                            pending[bucket].setdefault(obj_id, set()).add(getattr(c, 'id'))
                # Apply reciprocal additions
                for bucket, model in COMM_MAP.items():
                    if not pending[bucket]:
                        continue
                    objs = list(model.objects.filter(id__in=pending[bucket].keys()))
                    for obj in objs:
                        obj_refs = getattr(obj, 'refs', {}) or {}
                        obj_links = obj_refs.setdefault('links', {}) if isinstance(obj_refs, dict) else {}
                        if not isinstance(obj_links, dict):
                            obj_links = {}
                            obj_refs['links'] = obj_links
                        contact_list = obj_links.setdefault('contacts', [])
                        changed = False
                        for cid in pending[bucket][getattr(obj, 'id')]:
                            if cid not in contact_list:
                                contact_list.append(cid)
                                changed = True
                        if changed and not dry:
                            setattr(obj, 'refs', obj_refs)
                            obj.save(update_fields=['refs'])
                            comm_updates += 1
                # Optional prune: remove contacts that no longer reference the object
                if prune:
                    for bucket, model in COMM_MAP.items():
                        if not pending[bucket]:
                            continue
                        objs = list(model.objects.filter(id__in=pending[bucket].keys()))
                        for obj in objs:
                            obj_refs = getattr(obj, 'refs', {}) or {}
                            obj_links = obj_refs.get('links', {}) if isinstance(obj_refs, dict) else {}
                            contact_list = obj_links.get('contacts', []) if isinstance(obj_links, dict) else []
                            if not isinstance(contact_list, list):
                                continue
                            before = len(contact_list)
                            # Keep only cids that still list this object in their bucket
                            keep = []
                            for cid in contact_list:
                                # cheap existence check (skip full load if large):
                                try:
                                    cref = Contact.objects.only('id','refs').get(id=cid)
                                except Contact.DoesNotExist:
                                    continue  # drop silently
                                c_refs = getattr(cref, 'refs', {}) or {}
                                c_links = c_refs.get('links', {}) if isinstance(c_refs, dict) else {}
                                ids_list = c_links.get(bucket) or []
                                if isinstance(ids_list, list) and getattr(obj, 'id') in ids_list:
                                    keep.append(cid)
                            if len(keep) != before:
                                if not dry:
                                    obj_links['contacts'] = keep
                                    setattr(obj, 'refs', obj_refs)
                                    obj.save(update_fields=['refs'])
                                pruned += (before - len(keep))
            if dry:
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(
            f"reconcile_links: contacts={processed} comm_updates={comm_updates} pruned={pruned} dry_run={dry}"))
