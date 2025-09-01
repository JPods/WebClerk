"""Generic bulk reseed utility.

Purpose:
  Flush (or optionally retain) the database then create a fixed small number
  of synthetic rows (default 5) for EVERY concrete, managed, non‑proxy model
  in the project, avoiding basic id/uuid/unique conflicts.

Usage examples:
  python manage.py reseed_all_models                # flush + 5 per model
  python manage.py reseed_all_models --per-model 3  # flush + 3 per model
  python manage.py reseed_all_models --no-flush     # seed on top of existing
  python manage.py reseed_all_models --apps orgs,products --per-model 2
  python manage.py reseed_all_models --dry-run

Notes / Heuristics:
  - Attempts a topological order based on required FK dependencies so that
    required relations exist before seeding dependants. Residual circular or
    optional dependencies are handled by a small multi‑pass retry loop.
  - Only fills *required* (non-null, no default) simple fields. Optional
    fields are left to their defaults. ManyToMany relations are skipped.
  - Unique Char/Text fields get deterministic base values with an index plus
    a short random suffix if collision occurs.
  - UUIDFields without a default get uuid4 values.
  - Date/DateTime fields get timezone.now(). / .date().
  - Integer/Numeric fields default to the loop index (1..N).
  - Boolean fields alternate True/False.
  - JSONFields default to empty dict.
  - This is intended for DEVELOPMENT ONLY; do not run in production.
"""
from __future__ import annotations

from typing import Iterable, List, Dict, Set
import uuid
import random
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.apps import apps
from django.db import IntegrityError, transaction, models
from django.utils import timezone


class Command(BaseCommand):
    help = "Flush (optional) and create N synthetic rows for every managed model. DEV ONLY."  # noqa: A003

    def add_arguments(self, parser):  # pragma: no cover - CLI plumbing
        parser.add_argument('--per-model', type=int, default=5, help='Rows to create per model (default 5).')
        parser.add_argument('--no-flush', action='store_true', help='Do not flush the database before seeding.')
        parser.add_argument('--apps', type=str, help='Comma separated app labels to restrict (default: all).')
        parser.add_argument('--dry-run', action='store_true', help='Report what would be done without writing.')
        parser.add_argument('--max-passes', type=int, default=3, help='Max dependency resolution passes (default 3).')
        parser.add_argument('--no-relate', action='store_true', help='Skip relationship (FK/M2M/org relations) pass.')
        parser.add_argument('--m2m-max', type=int, default=3, help='Max related objects to attach per M2M field.')
        parser.add_argument('--org-relations', type=int, default=3, help='OrgBase relations parent/child/linked cap.')

    def handle(self, *args, **opts):  # pragma: no cover - orchestration
        per_model = max(1, int(opts['per_model']))
        restrict_apps = {a.strip() for a in opts['apps'].split(',')} if opts.get('apps') else None
        dry_run = opts['dry_run']
        max_passes = max(1, int(opts['max_passes']))

        if not opts['no_flush'] and not dry_run:
            self.stdout.write(self.style.WARNING('Flushing database ...'))
            call_command('flush', interactive=False)

        # Collect candidate models
        # Pass 6: Seed 3-level BOM hierarchy (parent -> mid -> leaf components) -----------------
        if not dry_run:
            try:
                from apps.products.models import Item
                from apps.products.models.bom import BillOfMaterial
                all_item_ids = list(Item.objects.values_list('id', flat=True).order_by('id'))  # type: ignore
            except Exception:
                all_item_ids = []
            if not all_item_ids:
                try:
                    from apps.products.models import Item  # fallback (without order_by)
                    all_item_ids = list(Item.objects.values_list('id', flat=True))
                except Exception:
                    all_item_ids = []
            if len(all_item_ids) >= 3:  # need at least 3 distinct items to form 3 levels
                # Partition items roughly into 3 tiers
                n = len(all_item_ids)
                tier_size = max(1, n // 3)
                tier1 = all_item_ids[:tier_size]              # top-level parents
                tier2 = all_item_ids[tier_size: tier_size*2]   # mid components
                tier3 = all_item_ids[tier_size*2:]             # leaf components
                if not tier2:
                    tier2 = tier1[1:]  # fallback reuse
                if not tier3:
                    tier3 = tier2  # fallback reuse
                created_bom = 0
                touched_parents = set()
                for parent_id in tier1:
                    # choose 1-2 mid components
                    mids = random.sample(tier2, min(len(tier2), random.randint(1, 2)))
                    for mid_id in mids:
                        if mid_id == parent_id:
                            continue
                        try:
                            BillOfMaterial.objects.get_or_create(parent_id=parent_id, component_id=mid_id, defaults={'sequence': 10})
                            created_bom += 1
                            touched_parents.add(parent_id)
                        except Exception:
                            pass
                        # For each mid component, pick 1-2 leaf components
                        leaves = random.sample(tier3, min(len(tier3), random.randint(1, 2)))
                        for leaf_id in leaves:
                            if leaf_id in (parent_id, mid_id):
                                continue
                            # attach leaf to mid component (mid becomes parent in this relation)
                            try:
                                BillOfMaterial.objects.get_or_create(parent_id=mid_id, component_id=leaf_id, defaults={'sequence': 20})
                                created_bom += 1
                                touched_parents.add(mid_id)
                            except Exception:
                                pass
                # Optionally roll-up costs bottom-up (mid-level first, then top-level)
                try:
                    # mid-level parents (those that received leaves)
                    for mid in sorted([p for p in touched_parents if p in tier2]):
                        BillOfMaterial.recalc_parent_cost(mid)
                    # top-level parents
                    for top in sorted([p for p in touched_parents if p in tier1]):
                        BillOfMaterial.recalc_parent_cost(top)
                except Exception:
                    pass
                self.stdout.write(self.style.NOTICE(f"BOM hierarchy seeded: {created_bom} lines (3-level structure)."))
        all_models = [m for m in apps.get_models() if m._meta.managed and not m._meta.proxy]
        if restrict_apps:
            all_models = [m for m in all_models if m._meta.app_label in restrict_apps]

        # Exclude Django internal / migration bookkeeping models
        EXCLUDE_PREFIXES = {'auth.', 'admin.', 'sessions.', 'contenttypes.', 'django_celery_', 'django_'}
        models_list = []
        for m in all_models:
            label = f"{m._meta.app_label}.{m.__name__}"
            if any(label.startswith(p) for p in EXCLUDE_PREFIXES):
                continue
            models_list.append(m)

        # Build dependency graph (required FKs only)
        deps: Dict[models.Model, Set[models.Model]] = {}
        for m in models_list:
            required: Set[models.Model] = set()
            for f in m._meta.get_fields():  # type: ignore[attr-defined]
                if f.many_to_one and f.concrete and not f.null and not f.auto_created:  # required FK
                    rel_model = f.remote_field.model  # type: ignore[attr-defined]
                    if rel_model in models_list and rel_model is not m:
                        required.add(rel_model)
            deps[m] = required

        ordered = self._toposort(models_list, deps)
        if len(ordered) != len(models_list):  # fallback maintain list order
            ordered = models_list

        summary = {}
        remaining = set(ordered)
        passes = 0
        while remaining and passes < max_passes:
            passes += 1
            progressed = set()
            self.stdout.write(self.style.MIGRATE_HEADING(f"Seeding pass {passes} (remaining {len(remaining)})"))
            for model in list(remaining):
                created = self._seed_model(model, per_model, dry_run)
                summary[f"{model._meta.app_label}.{model.__name__}"] = created
                progressed.add(model)
            remaining -= progressed

        # Report
        total_created = sum(summary.values())
        self.stdout.write(self.style.SUCCESS(f"Reseed complete: {total_created} objects across {len(summary)} models."))
        if dry_run:
            self.stdout.write(self.style.WARNING('Dry run: no changes were committed.'))

        # Optional relationship building pass
        if not opts.get('no_relate'):
            self._build_relationships(models_list, dry_run=dry_run, m2m_max=int(opts['m2m_max']), org_rel_cap=int(opts['org_relations']))

    # -------- internals -------------------------------------------------
    def _toposort(self, models_list: List[models.Model], deps: Dict[models.Model, Set[models.Model]]):
        incoming = {m: set(deps.get(m, set())) for m in models_list}
        ready = [m for m, d in incoming.items() if not d]
        ordered: List[models.Model] = []
        while ready:
            m = ready.pop()
            ordered.append(m)
            for other in models_list:
                if m in incoming.get(other, set()):
                    incoming[other].remove(m)
                    if not incoming[other]:
                        ready.append(other)
        return ordered

    def _seed_model(self, model, per_model: int, dry_run: bool) -> int:
        # Skip through tables that already have >= per_model rows if not flushing (avoid bloat)
        existing = 0 if dry_run else model.objects.count()
        to_create = max(0, per_model - existing) if existing else per_model
        if to_create == 0:
            return 0
        created = 0
        for i in range(to_create):
            data = self._build_minimal_instance_kwargs(model, index=i)
            if dry_run:
                created += 1
                continue
            try:
                with transaction.atomic():
                    model.objects.create(**data)
                created += 1
            except IntegrityError:
                # Retry once with randomized unique fields
                try:
                    self._randomize_unique_fields(model, data)
                    with transaction.atomic():
                        model.objects.create(**data)
                    created += 1
                except Exception:  # pragma: no cover - noisy path
                    continue
            except Exception:  # pragma: no cover - catch-all
                continue
        return created

    def _build_minimal_instance_kwargs(self, model, index: int) -> dict:
        kwargs: dict = {}
        for f in model._meta.get_fields():  # type: ignore[attr-defined]
            if not getattr(f, 'concrete', False) or getattr(f, 'auto_created', False):
                continue
            if isinstance(f, (models.AutoField, models.BigAutoField)):
                continue
            if isinstance(f, models.ManyToManyField):
                continue  # handled post-save if desired (out of scope)
            name = f.name
            if getattr(f, 'primary_key', False):
                continue
            if isinstance(f, models.ForeignKey):
                # Required FK? Provide first existing or skip (will retry in later passes)
                if f.null:
                    continue
                rel_qs = f.remote_field.model.objects.order_by('pk')  # type: ignore[attr-defined]
                rel_obj = rel_qs.first()
                if rel_obj:
                    kwargs[name + '_id'] = rel_obj.pk
                else:
                    # leave missing; create will likely fail -> retried later
                    pass
                continue
            if hasattr(f, 'default') and f.default is not models.NOT_PROVIDED:
                continue  # rely on model default
            # Type heuristics
            if isinstance(f, models.UUIDField):
                kwargs[name] = uuid.uuid4()
            elif isinstance(f, models.CharField):
                base = f"{model.__name__.lower()}_{index}"[: f.max_length]
                kwargs[name] = base
            elif isinstance(f, models.TextField):
                kwargs[name] = f"{model.__name__} demo text {index}"[:255]
            elif isinstance(f, (models.IntegerField, models.BigIntegerField, models.SmallIntegerField)):
                kwargs[name] = index + 1
            elif isinstance(f, (models.FloatField, models.DecimalField)):
                kwargs[name] = float(index + 1)
            elif isinstance(f, models.BooleanField):
                kwargs[name] = (index % 2 == 0)
            elif isinstance(f, (models.DateTimeField,)):
                kwargs[name] = timezone.now()
            elif isinstance(f, (models.DateField,)):
                kwargs[name] = timezone.now().date()
            elif isinstance(f, models.JSONField):
                kwargs[name] = {}
            else:
                # Leave others (e.g., EmailField -> CharField subclass handled; FileField skip)
                pass
        return kwargs

    def _randomize_unique_fields(self, model, data: dict):
        for f in model._meta.get_fields():  # type: ignore[attr-defined]
            if getattr(f, 'unique', False) and isinstance(f, models.CharField):
                key = f.name
                if key in data:
                    data[key] = f"{data[key]}_{random.randint(1000,9999)}"[: f.max_length]

    # Relationship builder ------------------------------------------------
    def _build_relationships(self, models_list, dry_run: bool, m2m_max: int, org_rel_cap: int):
        from apps.orgs.models.base_org_model import OrgBase  # local import (optional app)
        self.stdout.write(self.style.MIGRATE_HEADING('Building relationships (FK backfill, M2M, org relations)...'))
        # Pass 1: ManyToMany random links
        for model in models_list:
            for f in model._meta.get_fields():  # type: ignore[attr-defined]
                if isinstance(f, models.ManyToManyField):
                    if dry_run:
                        continue
                    try:
                        all_objs = list(model.objects.all()[:50])
                        if not all_objs:
                            continue
                        target_model = f.remote_field.model  # type: ignore[attr-defined]
                        choices = list(target_model.objects.all()[:100])
                        if not choices:
                            continue
                        for obj in all_objs:
                            subset = random.sample(choices, min(len(choices), m2m_max))
                            getattr(obj, f.name).set(subset)
                    except Exception:
                        continue
        # Pass 2: OrgBase relations JSON linking (parents/children/linked_ids)
        if OrgBase in models_list and not dry_run:
            orgs = list(OrgBase.objects.all())
            ids = [o.pk for o in orgs]
            for o in orgs:
                if not isinstance(o.relations, dict):
                    o.relations = {"parents": [], "children": [], "linked_ids": []}
                peer_ids = [i for i in ids if i != o.pk]
                random.shuffle(peer_ids)
                o.relations['parents'] = peer_ids[: min(org_rel_cap, max(0, len(peer_ids)//3))]
                o.relations['children'] = peer_ids[min(org_rel_cap, max(0, len(peer_ids)//3)) : 2 * min(org_rel_cap, max(0, len(peer_ids)//3))]
                o.relations['linked_ids'] = peer_ids[: org_rel_cap]
                try:
                    o.save(update_fields=['relations'])
                except Exception:
                    continue
        self.stdout.write(self.style.SUCCESS('Relationship build pass complete.'))
