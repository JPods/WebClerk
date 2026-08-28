"""
audit_select_lists — export and review all select lists organized by use.

Shows every select-type field across all models: where the options come from
(hardcoded in service, Setting override, or config.select_lists), how many
options, and the actual values. Flags inconsistencies.

Flags:
  EMPTY       — select field with no options
  DUPLICATE   — identical options defined in multiple places for same field
  DRIFT       — same field name on different models has different option sets
  ORPHAN      — select_lists entry for a field that isn't typed as select

Usage:
    python manage.py audit_select_lists                # summary
    python manage.py audit_select_lists --detail       # show options
    python manage.py audit_select_lists --model order  # one model
    python manage.py audit_select_lists --json         # JSON for Alice
    python manage.py audit_select_lists --export       # full CSV export
"""
import csv
import io
import json as json_mod

from django.core.management.base import BaseCommand

from apps.core.constants.model_registry import MODEL_REGISTRY, get_model_meta
from apps.core.models.setting import Setting
from apps.core.services.field_behaviors import (
    get_field_behaviors, get_model_field_map,
)


def _options_key(options):
    """Canonical string for comparing option sets."""
    if not options:
        return ''
    return '|'.join(f'{o.get("value", "")}={o.get("label", "")}' for o in sorted(options, key=lambda o: o.get('value', '')))


# Fields where different option sets per model are by design, not accident.
# status: org status (4 opts) ≠ transaction status (6 opts) ≠ item status (4 opts)
# type: GL account type (5 opts) ≠ payment type (2 opts) ≠ connection type (5 opts)
# category: GL category (8 opts) ≠ project category (5 opts) ≠ report category (6 opts)
# purpose: address purpose (5 opts) ≠ document purpose (5 opts) ≠ general purpose (4 opts)
# direction: bundle direction (3 opts) ≠ touch direction (2 opts)
DRIFT_EXPECTED = {'status', 'type', 'category', 'purpose', 'direction'}


class Command(BaseCommand):
    help = 'Audit select lists — export all select-type fields organized by model, field, and source'

    def add_arguments(self, parser):
        parser.add_argument('--model', type=str, default=None, help='Audit one model only')
        parser.add_argument('--detail', action='store_true', help='Show option values')
        parser.add_argument('--json', action='store_true', help='JSON output for Alice')
        parser.add_argument('--export', action='store_true', help='CSV export')
        parser.add_argument('--reality', action='store_true',
                            help='Compare defined options against actual DB values — detect hallucinated or unused options')

    def _run_reality_check(self, all_selects, target=None):
        """Compare defined select options against actual DB values.

        For each select field, queries distinct values from real records
        and reports:
          UNUSED   — defined option never appears in any record
          UNLISTED — value in DB has no matching option
          COVERAGE — % of defined options actually used
        """
        from apps.core.constants.model_registry import get_model_meta

        reality_flags = []
        reality_stats = []

        for entry in all_selects:
            model_key = entry['model']
            field_name = entry['field']
            defined_opts = entry.get('options', [])

            if not defined_opts:
                continue

            # Skip JSON leaf fields (dot-path) — they live inside JSON columns
            # and need different query patterns
            if '.' in field_name:
                continue

            meta = get_model_meta(model_key)
            if not meta:
                continue

            try:
                model_cls = meta.import_model()
            except Exception:
                continue

            # Check field exists on model as a column
            try:
                model_cls._meta.get_field(field_name)
            except Exception:
                continue

            # Query distinct values
            try:
                actual_values = set(
                    model_cls.objects.filter(is_active=True)
                    .exclude(**{field_name: ''})
                    .exclude(**{f'{field_name}__isnull': True})
                    .values_list(field_name, flat=True)
                    .distinct()
                )
            except Exception:
                continue

            defined_values = {o.get('value', '') for o in defined_opts if o.get('value')}
            total_records = model_cls.objects.filter(is_active=True).count()

            unused = defined_values - actual_values
            unlisted = actual_values - defined_values
            used = defined_values & actual_values
            coverage = (len(used) / len(defined_values) * 100) if defined_values else 0

            stat = {
                'model': model_key,
                'field': field_name,
                'defined': len(defined_values),
                'used': len(used),
                'unused': len(unused),
                'unlisted': len(unlisted),
                'coverage': round(coverage, 1),
                'total_records': total_records,
                'unused_values': sorted(unused),
                'unlisted_values': sorted(unlisted),
            }
            reality_stats.append(stat)

            for v in unused:
                reality_flags.append({
                    'model': model_key, 'field': field_name,
                    'flag': 'UNUSED',
                    'detail': f'Option "{v}" defined but never used ({total_records} records)',
                })
            for v in unlisted:
                reality_flags.append({
                    'model': model_key, 'field': field_name,
                    'flag': 'UNLISTED',
                    'detail': f'Value "{v}" in DB but not in select options',
                })

        return reality_stats, reality_flags

    def handle(self, *args, **options):
        target = options.get('model')
        detail = options.get('detail', False)
        as_json = options.get('json', False)
        as_csv = options.get('export', False)

        models = (
            {target: MODEL_REGISTRY[target]}
            if target and target in MODEL_REGISTRY
            else MODEL_REGISTRY
        )

        all_selects = []  # {model, field, source, count, options, options_key}
        all_flags = []
        # Track options by field name across models for drift detection
        field_options_map = {}  # field_name -> {options_key: [model, ...]}

        for model_key in sorted(models.keys()):
            meta = get_model_meta(model_key)
            if not meta:
                continue

            field_map = get_model_field_map(model_key)
            if not field_map:
                continue

            # Compute behaviors (without overrides — raw detection)
            computed = get_field_behaviors(model_key, field_map)

            # Load stored overrides
            stored_behaviors = {}
            stored_select_lists = {}
            model_setting = Setting.objects.filter(
                purpose='wc:model', parent_model=meta.key,
                is_active=True, scope='system',
            ).first()
            if model_setting and isinstance(model_setting.config, dict):
                stored_behaviors = model_setting.config.get('behaviors', {})
                stored_select_lists = model_setting.config.get('select_lists', {})

            # Find all select-type fields
            for field_name, behavior in computed.items():
                if behavior.get('type') != 'select':
                    continue

                opts = behavior.get('options', [])
                source = 'service'

                # Check if override exists
                stored_beh = stored_behaviors.get(field_name, {})
                if stored_beh.get('type') == 'select' and stored_beh.get('options'):
                    stored_opts = stored_beh['options']
                    if _options_key(stored_opts) != _options_key(opts):
                        source = 'override'
                        opts = stored_opts

                # Check config.select_lists
                sl_entry = stored_select_lists.get(field_name)
                if sl_entry and isinstance(sl_entry, dict):
                    sl_choices = sl_entry.get('choices', [])
                    if sl_choices:
                        source = 'select_lists'

                ok = _options_key(opts)
                entry = {
                    'model': model_key,
                    'field': field_name,
                    'source': source,
                    'count': len(opts),
                    'options': opts,
                    'options_key': ok,
                }
                all_selects.append(entry)

                # Track for drift detection
                if field_name not in field_options_map:
                    field_options_map[field_name] = {}
                if ok not in field_options_map[field_name]:
                    field_options_map[field_name][ok] = []
                field_options_map[field_name][ok].append(model_key)

                # EMPTY flag
                if not opts:
                    all_flags.append({
                        'model': model_key, 'field': field_name,
                        'flag': 'EMPTY',
                        'detail': 'Select field with no options',
                    })

            # ORPHAN flag — select_lists entry for non-select field
            for sl_field in stored_select_lists:
                computed_beh = computed.get(sl_field, {})
                if computed_beh.get('type') != 'select':
                    all_flags.append({
                        'model': model_key, 'field': sl_field,
                        'flag': 'ORPHAN',
                        'detail': f'select_lists entry exists but field type is {computed_beh.get("type", "unknown")}',
                    })

        # DRIFT detection — same field name, different options across models
        for field_name, variants in field_options_map.items():
            if len(variants) > 1:
                expected = field_name in DRIFT_EXPECTED
                flag = 'DRIFT_OK' if expected else 'DRIFT'
                for ok, model_list in variants.items():
                    count = len([o for o in ok.split('|') if o]) if ok else 0
                    for m in model_list:
                        all_flags.append({
                            'model': m, 'field': field_name,
                            'flag': flag,
                            'detail': f'{count} options — {len(variants)} different option sets exist for this field name across models',
                        })

        # ── Output ──

        if as_json:
            # Group by field name
            by_field = {}
            for s in all_selects:
                fn = s['field']
                if fn not in by_field:
                    by_field[fn] = {'field': fn, 'models': [], 'option_sets': {}}
                by_field[fn]['models'].append(s['model'])
                ok = s['options_key']
                if ok not in by_field[fn]['option_sets']:
                    by_field[fn]['option_sets'][ok] = {
                        'options': s['options'],
                        'models': [],
                    }
                by_field[fn]['option_sets'][ok]['models'].append(s['model'])

            output = {
                'summary': {
                    'total_select_fields': len(all_selects),
                    'unique_field_names': len(by_field),
                    'total_flags': len(all_flags),
                    'flags_by_type': {},
                },
                'by_field': by_field,
                'flags': all_flags,
            }
            for f in all_flags:
                ft = f['flag']
                output['summary']['flags_by_type'][ft] = output['summary']['flags_by_type'].get(ft, 0) + 1
            self.stdout.write(json_mod.dumps(output, indent=2))
            return

        if as_csv:
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(['model', 'field', 'source', 'option_count', 'values'])
            for s in all_selects:
                values = ', '.join(o.get('value', '') for o in s['options'])
                writer.writerow([s['model'], s['field'], s['source'], s['count'], values])
            self.stdout.write(buf.getvalue())
            return

        # ── Summary ──

        # Group by field name
        by_field = {}
        for s in all_selects:
            fn = s['field']
            if fn not in by_field:
                by_field[fn] = []
            by_field[fn].append(s)

        actionable_flags = [f for f in all_flags if f['flag'] != 'DRIFT_OK']
        info_flags = [f for f in all_flags if f['flag'] == 'DRIFT_OK']

        self.stdout.write(self.style.SUCCESS(
            f"\nSelect list audit: {len(all_selects)} select fields across "
            f"{len(set(s['model'] for s in all_selects))} models, "
            f"{len(by_field)} unique field names, "
            f"{len(actionable_flags)} flags"
            + (f" ({len(info_flags)} expected drift)" if info_flags else "")
        ))

        if actionable_flags:
            flag_counts = {}
            for f in actionable_flags:
                flag_counts[f['flag']] = flag_counts.get(f['flag'], 0) + 1
            self.stdout.write("  Flags:")
            for ft, count in sorted(flag_counts.items()):
                self.stdout.write(f"    {ft}: {count}")

        # Show fields grouped by name
        self.stdout.write("\n  ── Select Fields by Name ──\n")
        for field_name in sorted(by_field.keys()):
            entries = by_field[field_name]
            models = [e['model'] for e in entries]
            sources = set(e['source'] for e in entries)
            counts = set(e['count'] for e in entries)
            option_keys = set(e['options_key'] for e in entries)

            drift_marker = ' !' if len(option_keys) > 1 else ''
            count_str = str(counts.pop()) if len(counts) == 1 else f"{min(counts)}-{max(counts)}"

            self.stdout.write(
                f"  {field_name:<25} {count_str:>3} opts  "
                f"src={','.join(sorted(sources)):<12}  "
                f"models={len(models)}{drift_marker}"
            )

            if detail:
                # Show models
                self.stdout.write(f"    models: {', '.join(sorted(models))}")
                # Show options (from first entry)
                opts = entries[0]['options']
                for o in opts:
                    self.stdout.write(f"      {o.get('value', '')}: {o.get('label', '')}")
                if len(option_keys) > 1:
                    self.stdout.write(f"    ⚠ DRIFT: {len(option_keys)} different option sets")

        # Show flags detail
        if detail and all_flags:
            self.stdout.write("\n  ── Flags ──\n")
            for f in all_flags:
                marker = '!' if f['flag'] in ('EMPTY', 'ORPHAN') else '?'
                self.stdout.write(f"  {marker} [{f['flag']}] {f['model']}.{f['field']} — {f['detail']}")

        # ── Reality check ──
        if options.get('reality'):
            reality_stats, reality_flags = self._run_reality_check(all_selects, target)

            self.stdout.write(self.style.MIGRATE_HEADING(
                f"\n\n── Reality Check: {len(reality_stats)} fields scanned ──"
            ))

            unused_count = sum(1 for f in reality_flags if f['flag'] == 'UNUSED')
            unlisted_count = sum(1 for f in reality_flags if f['flag'] == 'UNLISTED')

            self.stdout.write(f"  UNUSED options (defined but never in DB): {unused_count}")
            self.stdout.write(f"  UNLISTED values (in DB but no matching option): {unlisted_count}")

            # Coverage summary — group by coverage bracket
            brackets = {'100%': 0, '50-99%': 0, '1-49%': 0, '0%': 0}
            for s in reality_stats:
                cov = s['coverage']
                if cov == 100:
                    brackets['100%'] += 1
                elif cov >= 50:
                    brackets['50-99%'] += 1
                elif cov > 0:
                    brackets['1-49%'] += 1
                else:
                    brackets['0%'] += 1
            self.stdout.write("\n  Coverage distribution:")
            for bracket, count in brackets.items():
                bar = '█' * count
                self.stdout.write(f"    {bracket:>8}: {count:>3} fields  {bar}")

            # Show fields with issues
            problem_stats = [s for s in reality_stats if s['unused'] or s['unlisted']]
            if problem_stats:
                self.stdout.write("\n  ── Fields with mismatches ──\n")
                for s in sorted(problem_stats, key=lambda x: x['coverage']):
                    self.stdout.write(
                        f"  {s['model']}.{s['field']}  "
                        f"coverage={s['coverage']}%  "
                        f"used={s['used']}/{s['defined']}  "
                        f"records={s['total_records']}"
                    )
                    if s['unused_values']:
                        self.stdout.write(
                            f"    UNUSED: {', '.join(s['unused_values'])}"
                        )
                    if s['unlisted_values']:
                        self.stdout.write(
                            f"    UNLISTED: {', '.join(s['unlisted_values'])}"
                        )

            # 0% coverage fields — these are pure hallucination candidates
            zero_cov = [s for s in reality_stats if s['coverage'] == 0 and s['total_records'] > 0]
            if zero_cov:
                self.stdout.write(self.style.WARNING(
                    f"\n  ⚠ {len(zero_cov)} fields at 0% coverage (no records use any defined option):"
                ))
                for s in zero_cov:
                    self.stdout.write(
                        f"    {s['model']}.{s['field']} — "
                        f"{s['defined']} options defined, "
                        f"{s['total_records']} records, none match"
                    )
