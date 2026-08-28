"""
load_demo_data — Import a demo bundle (Settings + sample data) into this database.

Usage:
    python manage.py load_demo_data                          # from demo-bundle.json
    python manage.py load_demo_data --input /tmp/db.json     # custom path
    python manage.py load_demo_data --dry-run                # show what would change
    python manage.py load_demo_data --data-only              # skip settings, load data only
    python manage.py load_demo_data --settings-only          # load settings only, skip data

All non-Setting records are tagged refs.source="demo-baseline" so they
can be cleanly removed later via remove_demo_data.

FK resolution: every record in the bundle carries its uuid and the original
source-database PK (id). As each model is imported, we build a uuid→new_pk
array. When importing a record with an FK (e.g. customer_id), we find the
uuid that had that old PK in the bundle and look up its new PK.

Settings are never removed — they are system infrastructure.
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand


# Import order matters — dependencies first
MODEL_REGISTRY = [
    ('contact', 'apps.core.models.contact', 'Contact'),
    ('org', 'apps.orgs.models', 'OrgBase'),
    ('item', 'apps.products.models', 'Item'),
    ('bill_of_material', 'apps.products.models.bill_of_material', 'BillOfMaterial'),
    ('proposal', 'apps.transactions.models', 'Proposal'),
    ('proposal_line', 'apps.transactions.models', 'ProposalLine'),
    ('order', 'apps.transactions.models', 'Order'),
    ('order_line', 'apps.transactions.models', 'OrderLine'),
    ('invoice', 'apps.transactions.models', 'Invoice'),
    ('invoice_line', 'apps.transactions.models', 'InvoiceLine'),
    ('payment', 'apps.transactions.models', 'Payment'),
    ('gl_journal', 'apps.accounts.models', 'GlJournal'),
]

# Fields that are auto-generated or not portable — skip on import
SKIP_ON_IMPORT = {'id', '_state', '_pydantic_cache'}

# FK fields that reference other demo records.
# Maps (model_key, fk_field) → model_key of the referenced table.
# During import, old PKs are remapped to new PKs via the uuid array.
FK_FIELDS = {
    ('proposal', 'customer_id'): 'org',
    ('proposal', 'vendor_id'): 'org',
    ('proposal', 'manufacturer_id'): 'org',
    ('proposal', 'contact_id'): 'contact',
    ('order', 'customer_id'): 'org',
    ('order', 'vendor_id'): 'org',
    ('order', 'manufacturer_id'): 'org',
    ('order', 'contact_id'): 'contact',
    ('order', 'parent_id'): 'proposal',
    ('invoice', 'customer_id'): 'org',
    ('invoice', 'vendor_id'): 'org',
    ('invoice', 'manufacturer_id'): 'org',
    ('invoice', 'contact_id'): 'contact',
    ('invoice', 'parent_id'): 'order',
    ('payment', 'customer_id'): 'org',
    ('payment', 'vendor_id'): 'org',
    ('payment', 'contact_id'): 'contact',
    ('payment', 'invoice_id'): 'invoice',
    ('proposal_line', 'proposal_id'): 'proposal',
    ('proposal_line', 'item_fk_id'): 'item',
    ('order_line', 'order_id'): 'order',
    ('order_line', 'item_fk_id'): 'item',
    ('invoice_line', 'invoice_id'): 'invoice',
    ('invoice_line', 'item_fk_id'): 'item',
    ('bill_of_material', 'parent_item_id'): 'item',
    ('bill_of_material', 'child_item_id'): 'item',
}


class Command(BaseCommand):
    help = 'Load a demo bundle (Settings + sample data) into the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--input', type=str, default='demo-bundle.json',
            help='Input file path (default: demo-bundle.json)',
        )
        parser.add_argument('--dry-run', action='store_true',
                            help='Show what would be imported without writing')
        parser.add_argument('--data-only', action='store_true',
                            help='Skip settings, load data only')
        parser.add_argument('--settings-only', action='store_true',
                            help='Load settings only, skip data')

    def handle(self, *args, **options):
        input_path = Path(options['input'])
        if not input_path.exists():
            self.stderr.write(self.style.ERROR(f"File not found: {input_path}"))
            return

        with open(input_path) as f:
            bundle = json.load(f)

        demo_source = bundle.get('demo_source_tag', 'demo-baseline')
        self.stdout.write(f"\nBundle: {bundle.get('source', '?')}")
        self.stdout.write(f"Exported: {bundle.get('dt_exported', '?')}")
        self.stdout.write(f"Demo source tag: {demo_source}")

        # ── Settings ───────────────────────────────────────────────────
        if not options.get('data_only'):
            settings_records = bundle.get('settings', [])
            if options['dry_run']:
                self.stdout.write(f"\nSettings: {len(settings_records)} would be imported")
            else:
                from apps.core.services.setting_bootstrap import import_settings_bundle
                result = import_settings_bundle({'settings': settings_records})
                self.stdout.write(
                    f"\nSettings: {result['created']} created, "
                    f"{result['updated']} updated"
                )
                if result['errors']:
                    for e in result['errors']:
                        self.stderr.write(self.style.ERROR(f"  {e}"))

        # ── Data ───────────────────────────────────────────────────────
        if not options.get('settings_only'):
            data = bundle.get('data', {})
            self._load_data(data, demo_source, dry_run=options['dry_run'])

    def _load_data(self, data, demo_source, dry_run=False):
        """Load demo data records, tagging each with refs.source.

        Builds a uuid→new_pk array per model as records are imported.
        FK fields on later models are remapped using this array.
        """
        from importlib import import_module

        total_created = 0
        total_skipped = 0

        # The array: model_key → {old_pk: new_pk}
        # Built from uuid: old record has uuid+old_id, new record gets uuid+new_id
        pk_map = {}

        # Also build old_pk→uuid from bundle data so we can look up by old FK value
        # model_key → {old_pk: uuid}
        old_pk_to_uuid = {}
        for key, _, _ in MODEL_REGISTRY:
            records = data.get(key, [])
            mapping = {}
            for rec in records:
                old_id = rec.get('id')
                uuid_val = rec.get('uuid')
                if old_id and uuid_val:
                    mapping[int(old_id)] = str(uuid_val)
            old_pk_to_uuid[key] = mapping

        for key, module_path, class_name in MODEL_REGISTRY:
            records = data.get(key, [])
            if not records:
                continue

            mod = import_module(module_path)
            Model = getattr(mod, class_name)

            if dry_run:
                self.stdout.write(f"  {key}: {len(records)} would be loaded")
                continue

            created, skipped = self._import_model_records(
                Model, records, demo_source, key, pk_map, old_pk_to_uuid,
            )
            total_created += created
            total_skipped += skipped
            self.stdout.write(f"  {key}: {created} created, {skipped} skipped")

        if not dry_run:
            self.stdout.write(self.style.SUCCESS(
                f"\nData: {total_created} created, {total_skipped} skipped"
            ))

    def _remap_fk(self, key, field_name, old_value, pk_map, old_pk_to_uuid):
        """Resolve an FK field from old PK to new PK via uuid array.

        Returns the new PK, or None if not resolvable.
        """
        ref_model = FK_FIELDS.get((key, field_name))
        if not ref_model or not old_value:
            return old_value

        old_pk = int(old_value)

        # Step 1: find the uuid that had this old PK in the bundle
        uuid_val = old_pk_to_uuid.get(ref_model, {}).get(old_pk)
        if not uuid_val:
            return None  # referenced record wasn't in the bundle

        # Step 2: find the new PK for that uuid in the receiving database
        new_pk = pk_map.get(ref_model, {}).get(uuid_val)
        if not new_pk:
            return None  # referenced record wasn't imported (or failed)

        return new_pk

    def _import_model_records(self, Model, records, demo_source, key,
                              pk_map, old_pk_to_uuid):
        """Import records for a single model using bulk_create.

        Uses bulk_create to bypass post_save signals (inventory pending,
        contact linking, Alice LLM calls) that can hang or fail on demo data.

        After import, populates pk_map[key] = {uuid: new_pk} for FK resolution.
        """
        import uuid as _uuid
        from django.utils import timezone

        now_ms = int(timezone.now().timestamp() * 1000)
        objects_to_create = []
        uuid_list = []  # track uuids in creation order
        skipped = 0

        # Get concrete field names (skip M2M, reverse FK, auto PK)
        model_field_names = {f.attname for f in Model._meta.get_fields()
                             if hasattr(f, 'attname')
                             and not getattr(f, 'many_to_many', False)}

        # Which FK fields on this model need remapping?
        fk_fields_for_model = {
            field_name for (mk, field_name) in FK_FIELDS if mk == key
        }

        for rec in records:
            uuid_val = rec.get('uuid')
            if not uuid_val:
                skipped += 1
                continue

            # Skip if already exists
            if Model.objects.filter(uuid=uuid_val).exists():
                skipped += 1
                continue

            # Build field dict
            fields = {}
            for field_name, value in rec.items():
                if field_name in SKIP_ON_IMPORT:
                    continue
                if field_name not in model_field_names:
                    continue

                # Remap FK fields to new PKs
                if field_name in fk_fields_for_model and value:
                    new_pk = self._remap_fk(
                        key, field_name, value, pk_map, old_pk_to_uuid,
                    )
                    fields[field_name] = new_pk
                else:
                    fields[field_name] = value

            # Ensure uuid and timestamps
            fields['uuid'] = uuid_val
            fields.setdefault('dt_created', now_ms)
            fields.setdefault('dt_modified', now_ms)

            # Tag with demo source for clean removal
            if 'refs' in model_field_names:
                refs = fields.get('refs') or {}
                if not isinstance(refs, dict):
                    refs = {}
                refs['source'] = demo_source
                fields['refs'] = refs

            try:
                objects_to_create.append(Model(**fields))
                uuid_list.append(str(uuid_val))
            except Exception as e:
                self.stderr.write(self.style.ERROR(
                    f"  ERROR {key} uuid={uuid_val}: {e}"
                ))

        created = 0
        if objects_to_create:
            try:
                Model.objects.bulk_create(objects_to_create)
                created = len(objects_to_create)
            except Exception as e:
                self.stderr.write(self.style.ERROR(
                    f"  BULK ERROR {key}: {e}"
                ))
                # Fall back to one-at-a-time
                for obj in objects_to_create:
                    try:
                        Model.objects.bulk_create([obj])
                        created += 1
                    except Exception as e2:
                        self.stderr.write(self.style.ERROR(
                            f"  ERROR {key} ida={getattr(obj, 'ida', '?')}: {e2}"
                        ))

        # Build pk_map for this model: uuid → new PK
        # Query the DB for all records we just created by uuid
        if uuid_list:
            pk_map[key] = {}
            for uuid_val, new_pk in (
                Model.objects.filter(uuid__in=uuid_list)
                .values_list('uuid', 'pk')
            ):
                pk_map[key][str(uuid_val)] = new_pk

        return created, skipped
