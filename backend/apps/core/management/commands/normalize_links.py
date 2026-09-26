"""Rewrite every refs.links list to link_entry's shape, rebuilt from its source records.

Fable #4 + Bill, 2026-09-26: a link is a rich {} built by one writer (common.denorm_registry
.link_entry). Stored lists had drifted into mixed shapes — bare ints beside {"id": n} (the
broken every-save denormalizer), {contact_id, display_name} beside {id, name} (a second writer
and a renamed field), snapshots of fields that no longer exist. This rebuilds each element from
its source record. A snapshot is derived data, so this repair is allowed on any data set
(Bill: derived repairs everywhere). Relationship keys that are not copies of the source
(purpose, model, role) are kept. An element whose source is gone is removed and counted
(Bill: a link to nothing shows nothing). History records (audit) are never touched: a
snapshot there is a fact about that moment, not a copy to refresh (Bill).

    manage.py normalize_links            # report what would change
    manage.py normalize_links --apply    # write it
"""
from django.apps import apps
from django.db import DEFAULT_DB_ALIAS, router
from django.core.management.base import BaseCommand

from common.denorm_registry import ORG_ROLE_KEYS, link_entry

#: Keys on a link element that describe the relationship, not the linked record: kept as is.
RELATIONSHIP_KEYS = ('purpose', 'model', 'role')
#: History: its snapshots are what was true then; normalize leaves them exactly as written.
HISTORY_MODELS = ('audit',)


def _source_model(bucket: str):
    from apps.core.utils import registry
    from apps.orgs.models import OrgBase
    if bucket in ORG_ROLE_KEYS or bucket == 'orgbase':
        return OrgBase
    for key in (bucket, bucket.rstrip('s'), bucket.replace('_', '')):
        resolved = registry.resolve(key)
        if resolved is None:
            continue
        model = resolved if hasattr(resolved, '_meta') else resolved.import_model()
        if model is not None:
            return model
    return None


def _element_id(element):
    if isinstance(element, dict):
        return element.get('id') or element.get('contact_id')
    return element if isinstance(element, int) else None


class Command(BaseCommand):
    help = "Rewrite refs.links elements to link_entry's shape from their source records."

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Write the changes (default: report).')

    def handle(self, *args, **opts):
        apply = opts['apply']
        from collections import Counter
        changed = records = gone = 0
        by_list, gone_by = Counter(), Counter()
        unresolved = set()
        for Model in apps.get_models():
            if not any(f.name == 'refs' for f in Model._meta.concrete_fields):
                continue
            if Model._meta.model_name in HISTORY_MODELS:
                continue
            if not router.allow_migrate_model(DEFAULT_DB_ALIAS, Model):
                continue                         # lives in another database (webserving)
            for pk, refs in Model.objects.exclude(refs={}).values_list('pk', 'refs'):
                links = (refs or {}).get('links') if isinstance(refs, dict) else None
                if not isinstance(links, dict) or not links:
                    continue
                new_links = {}
                for bucket, elements in links.items():
                    if not isinstance(elements, list):
                        new_links[bucket] = elements
                        continue
                    source = _source_model(bucket)
                    if source is None:
                        unresolved.add(bucket)
                        new_links[bucket] = elements
                        continue
                    ids = [_element_id(e) for e in elements]
                    found = source.objects.in_bulk([i for i in ids if i])
                    rebuilt, seen = [], set()
                    for element, i in zip(elements, ids):
                        if not i or i in seen:
                            continue                     # an unreadable or repeated element
                        seen.add(i)
                        obj = found.get(i)
                        if obj is None:
                            gone += 1
                            gone_by[f'{Model._meta.model_name}.{bucket}'] += 1
                            continue                     # a link to nothing is dropped
                        entry = link_entry(obj, bucket)
                        if isinstance(element, dict):
                            entry.update({k: element[k] for k in RELATIONSHIP_KEYS if k in element})
                        rebuilt.append(entry)
                    new_links[bucket] = rebuilt
                if new_links != links:
                    records += 1
                    for b in new_links:
                        if new_links[b] != links.get(b):
                            changed += 1
                            by_list[f'{Model._meta.model_name}.{b}'] += 1
                    if apply:
                        Model.objects.filter(pk=pk).update(refs={**refs, 'links': new_links})
        verb = 'Rewrote' if apply else 'Would rewrite'
        self.stdout.write(f'{verb} {changed} link lists on {records} records; '
                          f'{gone} elements pointed at records that are gone (dropped).')
        for name, n in by_list.most_common():
            self.stdout.write(f'  {n:5d} lists  {name}' + (f'   ({gone_by[name]} gone)' if gone_by[name] else ''))
        if unresolved:
            self.stdout.write(f'Buckets with no source model (left as they are): {sorted(unresolved)}')
