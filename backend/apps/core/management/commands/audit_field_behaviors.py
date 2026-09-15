"""
audit_field_behaviors — review computed field behaviors across all models.

Runs the field_behaviors service against every model in MODEL_REGISTRY,
compares computed behaviors with stored overrides in wc:model Settings,
and flags problems.

Flags:
  UNTYPED     — field fell through all detection rules (no behavior assigned)
  OVERRIDE    — stored behavior differs from computed (intentional? or stale?)
  EMPTY_OPTS  — select field with no options
  BAD_LOOKUP  — lookup field pointing at a model not in MODEL_REGISTRY
  PHONE_NAME  — field named 'number' auto-detected as phone (often wrong)
  ORPHAN_OVR  — override exists for a field that no longer exists on the model

Usage:
    python manage.py audit_field_behaviors                # summary
    python manage.py audit_field_behaviors --detail       # show every flag
    python manage.py audit_field_behaviors --model order  # one model
    python manage.py audit_field_behaviors --json         # JSON output for Alice
"""
import json as json_mod

from django.core.management.base import BaseCommand

from apps.core.constants.model_registry import MODEL_REGISTRY, get_model_meta
from apps.core.models.setting import Setting
from apps.core.services.field_behaviors import (
    get_field_behaviors, get_field_groups, get_model_field_map,
)


# Fields where PHONE_NAME detection is confirmed correct — don't flag
PHONE_NAME_CONFIRMED = {
    ('phone', 'number'),  # phone.number IS a phone number field
}


class Command(BaseCommand):
    help = 'Audit field behaviors — flag misdetections, stale overrides, missing types'

    def add_arguments(self, parser):
        parser.add_argument('--model', type=str, default=None, help='Audit one model only')
        parser.add_argument('--detail', action='store_true', help='Show every flag')
        parser.add_argument('--json', action='store_true', help='JSON output for Alice')
        parser.add_argument('--cross-check', action='store_true',
                            help='Verify select field heuristics match actual data semantics')

    def handle(self, *args, **options):
        target = options.get('model')
        detail = options.get('detail', False)
        as_json = options.get('json', False)

        models = (
            {target: MODEL_REGISTRY[target]}
            if target and target in MODEL_REGISTRY
            else MODEL_REGISTRY
        )

        all_flags = []
        summary = {
            'models_audited': 0,
            'models_clean': 0,
            'total_fields': 0,
            'total_flags': 0,
            'by_type': {},
        }

        for model_key in sorted(models.keys()):
            meta = get_model_meta(model_key)
            if not meta:
                continue

            field_map = get_model_field_map(model_key)
            if not field_map:
                continue

            # Compute behaviors without overrides
            computed = get_field_behaviors(model_key, field_map)

            # Load stored overrides from wc:model Setting
            stored_overrides = {}
            model_setting = Setting.objects.filter(
                purpose='wc:model', parent_model=meta.key,
                is_active=True, scope='system',
            ).first()
            if model_setting and isinstance(model_setting.config, dict):
                stored_overrides = model_setting.config.get('behaviors', {})

            flags = []
            summary['models_audited'] += 1
            summary['total_fields'] += len(field_map)

            for field_name in field_map:
                behavior = computed.get(field_name)

                # UNTYPED — no behavior assigned
                if not behavior:
                    flags.append({
                        'model': model_key, 'field': field_name,
                        'flag': 'UNTYPED',
                        'detail': f'Django type: {field_map[field_name].__class__.__name__}',
                    })
                    continue

                btype = behavior.get('type', '')

                # PHONE_NAME — 'number' field detected as phone
                if field_name == 'number' and btype == 'phone':
                    if (model_key, field_name) not in PHONE_NAME_CONFIRMED:
                        flags.append({
                            'model': model_key, 'field': field_name,
                            'flag': 'PHONE_NAME',
                            'detail': f'Auto-detected as phone — verify this is actually a phone number field',
                        })

                # EMPTY_OPTS — select with no options
                if btype == 'select':
                    opts = behavior.get('options', [])
                    if not opts:
                        flags.append({
                            'model': model_key, 'field': field_name,
                            'flag': 'EMPTY_OPTS',
                            'detail': 'Select field with no options defined',
                        })

                # BAD_LOOKUP — lookup pointing at unknown model
                if btype == 'lookup':
                    lookup_model = behavior.get('model', '')
                    if lookup_model and lookup_model not in MODEL_REGISTRY:
                        # Check by meta.key too
                        found = any(
                            get_model_meta(k) and get_model_meta(k).key == lookup_model
                            for k in MODEL_REGISTRY
                        )
                        if not found:
                            flags.append({
                                'model': model_key, 'field': field_name,
                                'flag': 'BAD_LOOKUP',
                                'detail': f'Lookup target "{lookup_model}" not in MODEL_REGISTRY',
                            })

            # OVERRIDE — stored differs from computed
            for field_name, stored_beh in stored_overrides.items():
                if not isinstance(stored_beh, dict):
                    continue
                computed_beh = computed.get(field_name, {})
                if field_name not in field_map and '.' not in field_name:
                    # ORPHAN_OVR — override for field that doesn't exist
                    flags.append({
                        'model': model_key, 'field': field_name,
                        'flag': 'ORPHAN_OVR',
                        'detail': f'Override exists but field not on model. Stored: {stored_beh}',
                    })
                elif stored_beh != computed_beh and stored_beh.get('type') != computed_beh.get('type'):
                    flags.append({
                        'model': model_key, 'field': field_name,
                        'flag': 'OVERRIDE',
                        'detail': f'computed={computed_beh.get("type")} stored={stored_beh.get("type")}',
                    })

            if not flags:
                summary['models_clean'] += 1

            for f in flags:
                ftype = f['flag']
                summary['by_type'][ftype] = summary['by_type'].get(ftype, 0) + 1

            summary['total_flags'] += len(flags)
            all_flags.extend(flags)

        # Output
        if as_json:
            output = {
                'summary': summary,
                'flags': all_flags,
            }
            self.stdout.write(json_mod.dumps(output, indent=2))
            return

        # Summary
        self.stdout.write(self.style.SUCCESS(
            f"\nAudit complete: {summary['models_audited']} models, "
            f"{summary['total_fields']} fields, "
            f"{summary['total_flags']} flags"
        ))
        self.stdout.write(
            f"  Clean models: {summary['models_clean']}/{summary['models_audited']}"
        )
        if summary['by_type']:
            self.stdout.write("  Flags by type:")
            for ftype, count in sorted(summary['by_type'].items()):
                self.stdout.write(f"    {ftype}: {count}")

        # Detail
        if detail and all_flags:
            self.stdout.write("\n  ── Detail ──")
            current_model = None
            for f in all_flags:
                if f['model'] != current_model:
                    current_model = f['model']
                    self.stdout.write(f"\n  {current_model}:")
                marker = '!' if f['flag'] in ('UNTYPED', 'BAD_LOOKUP', 'ORPHAN_OVR') else '?'
                self.stdout.write(
                    f"    {marker} [{f['flag']}] {f['field']} — {f['detail']}"
                )

        # ── Cross-check: verify select heuristics match actual data ──
        if options.get('cross_check'):
            self.stdout.write(self.style.MIGRATE_HEADING(
                "\n\n── Cross-check: select field heuristics vs actual data ──"
            ))
            xcheck_flags = []
            for model_key in sorted(models.keys()):
                meta = get_model_meta(model_key)
                if not meta:
                    continue
                field_map = get_model_field_map(model_key)
                if not field_map:
                    continue
                computed = get_field_behaviors(model_key, field_map)

                try:
                    model_cls = meta.import_model()
                except Exception:
                    continue

                for field_name, behavior in computed.items():
                    if behavior.get('type') != 'select' or '.' in field_name:
                        continue
                    opts = behavior.get('options', [])
                    if not opts:
                        continue

                    try:
                        model_cls._meta.get_field(field_name)
                    except Exception:
                        continue

                    defined_values = {o['value'] for o in opts if o.get('value')}

                    try:
                        actual = set(
                            model_cls.objects.filter(is_active=True)
                            .exclude(**{field_name: ''})
                            .exclude(**{f'{field_name}__isnull': True})
                            .values_list(field_name, flat=True)
                            .distinct()
                        )
                    except Exception:
                        continue

                    if not actual:
                        continue

                    # What fraction of actual values match defined options?
                    matching = actual & defined_values
                    match_pct = len(matching) / len(actual) * 100 if actual else 100

                    if match_pct < 50:
                        xcheck_flags.append({
                            'model': model_key,
                            'field': field_name,
                            'match_pct': round(match_pct, 1),
                            'actual_sample': sorted(actual)[:5],
                            'defined_sample': sorted(defined_values)[:5],
                        })

            if xcheck_flags:
                self.stdout.write(self.style.WARNING(
                    f"\n  {len(xcheck_flags)} fields where >50% of actual values "
                    f"don't match defined options (possible wrong heuristic):"
                ))
                for xf in xcheck_flags:
                    self.stdout.write(
                        f"\n  ! {xf['model']}.{xf['field']} — "
                        f"{xf['match_pct']}% match"
                    )
                    self.stdout.write(f"      actual:  {xf['actual_sample']}")
                    self.stdout.write(f"      defined: {xf['defined_sample']}")
            else:
                self.stdout.write(self.style.SUCCESS(
                    "\n  All select fields: >50% of actual values match defined options."
                ))
