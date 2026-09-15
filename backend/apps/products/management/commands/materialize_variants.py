from __future__ import annotations

from django.core.management.base import BaseCommand
from apps.products.models import Item, Variant
from apps.products.variant_utils import derive_variant_uuid


class Command(BaseCommand):
    help = "Materialize Variant rows from Item.refs/metadata variants scaffolding"

    def handle(self, *args, **options):
        created = 0
        updated = 0
        skipped = 0
        for it in Item.objects.all():
            vrefs = (it.refs or {}).get('variants') if isinstance(getattr(it, 'refs', None), dict) else None
            vmeta = (it.metadata or {}).get('variants') if isinstance(getattr(it, 'metadata', None), dict) else None
            if not isinstance(vrefs, dict) or not isinstance(vmeta, dict):
                skipped += 1
                continue
            parent_id = vrefs.get('parent_id')
            key = vrefs.get('key') or ''
            attrs = vrefs.get('attrs') or {}
            set_uuid = vmeta.get('set_uuid')
            if not parent_id or not key or not set_uuid:
                skipped += 1
                continue
            try:
                v_uuid = derive_variant_uuid(set_uuid, attrs)
            except Exception:
                skipped += 1
                continue
            obj, created_flag = Variant.objects.update_or_create(
                item_id=it.id,
                defaults={
                    'parent_item_id': parent_id,
                    'canonical_key': key,
                    'attrs': attrs,
                    'set_uuid': set_uuid,
                    'variant_uuid': str(v_uuid),
                }
            )
            if created_flag:
                created += 1
            else:
                updated += 1
        self.stdout.write(f"Materialize variants: created={created} updated={updated} skipped={skipped}")
