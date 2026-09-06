"""
audit_layouts — Layout Parade audit: which models have all five layout types?

Scans every model in MODEL_REGISTRY, checks for a wc:model Setting with
config.layout populated, and reports coverage for five layout types:

  1. list   — config.layout.list.default.columns   (list view columns)
  2. detail — config.layout.detail                  (detail form layout)
  3. panel  — config.db.panel / wc:workbench_fields (embedded panel columns)
  4. card   — config.layout.card                    (card-based detail layout)
  5. form   — config.layout.form                    (form definitions)

Usage:
    python manage.py audit_layouts               # human-readable table
    python manage.py audit_layouts --json         # JSON output (Alice-consumable)
    python manage.py audit_layouts --gaps-only    # only models missing layouts
"""
import json
from django.core.management.base import BaseCommand
from apps.core.models.setting import Setting
from apps.core.constants.model_registry import MODEL_REGISTRY, get_model_meta


def audit_all_layouts():
    """Return a list of dicts, one per registered model, with layout coverage info."""
    results = []

    for model_key in sorted(MODEL_REGISTRY.keys()):
        meta = get_model_meta(model_key)
        if not meta:
            continue

        canonical_key = meta.key
        entry = {
            'model': model_key,
            'singular': meta.singular,
            'kind': meta.kind,
            'has_wc_model_setting': False,
            'has_list_layout': False,
            'has_detail_layout': False,
            'has_panel_layout': False,
            'has_card_layout': False,
            'has_form_layout': False,
            'list_column_count': 0,
            'detail_field_count': 0,
            'panel_column_count': 0,
            'card_count': 0,
            'form_tab_count': 0,
            'needs_attention': False,
            'gaps': [],
        }

        # Check for wc:model Setting (the consolidated model definition)
        wc_model = Setting.objects.filter(
            parent_model=canonical_key,
            purpose='wc:model',
            is_active=True,
        ).first()

        if wc_model:
            entry['has_wc_model_setting'] = True
            cfg = wc_model.config if isinstance(wc_model.config, dict) else {}
            layout = cfg.get('layout', {})

            # List layout: layout.list.default.columns
            list_section = layout.get('list', {})
            if isinstance(list_section, dict):
                default_list = list_section.get('default', {})
                if isinstance(default_list, dict):
                    cols = default_list.get('columns', [])
                    if isinstance(cols, list) and len(cols) > 0:
                        entry['has_list_layout'] = True
                        entry['list_column_count'] = len(cols)

            # Detail layout: layout.detail.default.fields
            detail_section = layout.get('detail', {})
            if isinstance(detail_section, dict):
                default_detail = detail_section.get('default', {})
                if isinstance(default_detail, dict):
                    fields = default_detail.get('fields', [])
                    if isinstance(fields, list) and len(fields) > 0:
                        entry['has_detail_layout'] = True
                        entry['detail_field_count'] = len(fields)

            # Panel layout: layout.panel or layout.column.default.columns
            panel = layout.get('panel', [])
            if isinstance(panel, list) and len(panel) > 0:
                entry['has_panel_layout'] = True
                entry['panel_column_count'] = len(panel)
            else:
                # Also check column.default.columns (named format)
                col_section = layout.get('column', {})
                if isinstance(col_section, dict):
                    default_col = col_section.get('default', {})
                    if isinstance(default_col, dict):
                        col_cols = default_col.get('columns', [])
                        if isinstance(col_cols, list) and len(col_cols) > 0:
                            entry['has_panel_layout'] = True
                            entry['panel_column_count'] = len(col_cols)

            # Card layout: layout.card (dict or non-empty list of named CardSpecs)
            card_section = layout.get('card')
            if isinstance(card_section, dict) and len(card_section) > 0:
                entry['has_card_layout'] = True
                entry['card_count'] = len(card_section)
            elif isinstance(card_section, list) and len(card_section) > 0:
                entry['has_card_layout'] = True
                entry['card_count'] = len(card_section)

            # Form layout: layout.form (dict of named form layouts)
            form_section = layout.get('form', {})
            if isinstance(form_section, dict):
                for form_name, form_def in form_section.items():
                    if not isinstance(form_def, dict):
                        continue
                    # A form layout has substance if it has sections, header, lines, or tabs
                    has_sections = isinstance(form_def.get('sections'), list) and len(form_def.get('sections', [])) > 0
                    has_header = bool(form_def.get('header'))
                    has_lines = bool(form_def.get('lines'))
                    has_tabs = isinstance(form_def.get('tabs'), list) and len(form_def.get('tabs', [])) > 0
                    if has_sections or has_header or has_lines or has_tabs:
                        entry['has_form_layout'] = True
                        tab_count = len(form_def.get('tabs', []))
                        section_count = len(form_def.get('sections', []))
                        entry['form_tab_count'] = tab_count or section_count
                        break
        else:
            entry['gaps'].append('no wc:model Setting')

        # Also check for standalone workbench_fields panel
        if not entry['has_panel_layout']:
            wb = Setting.objects.filter(
                parent_model=canonical_key,
                purpose='wc:workbench_fields',
                is_active=True,
            ).first()
            if wb:
                wb_cfg = wb.config if isinstance(wb.config, dict) else {}
                db = wb_cfg.get('db', wb_cfg)
                if isinstance(db, dict):
                    panel = db.get('panel', [])
                    if isinstance(panel, list) and len(panel) > 0:
                        entry['has_panel_layout'] = True
                        entry['panel_column_count'] = len(panel)

        # Determine gaps
        if not entry['has_list_layout']:
            entry['gaps'].append('missing list layout')
        if not entry['has_detail_layout']:
            entry['gaps'].append('missing detail layout')
        if not entry['has_panel_layout']:
            entry['gaps'].append('missing panel layout')
        if not entry['has_card_layout']:
            entry['gaps'].append('missing card layout')
        if not entry['has_form_layout']:
            entry['gaps'].append('missing form layout')
        if entry['gaps']:
            entry['needs_attention'] = True

        results.append(entry)

    return results


def audit_summary(results):
    """Return summary stats from audit results."""
    total = len(results)
    has_setting = sum(1 for r in results if r['has_wc_model_setting'])
    has_list = sum(1 for r in results if r['has_list_layout'])
    has_detail = sum(1 for r in results if r['has_detail_layout'])
    has_panel = sum(1 for r in results if r['has_panel_layout'])
    has_card = sum(1 for r in results if r['has_card_layout'])
    has_form = sum(1 for r in results if r['has_form_layout'])
    needs_attention = sum(1 for r in results if r['needs_attention'])
    fully_covered = sum(
        1 for r in results
        if r['has_list_layout'] and r['has_detail_layout']
        and r['has_panel_layout'] and r['has_card_layout']
        and r['has_form_layout']
    )
    return {
        'total_models': total,
        'has_wc_model_setting': has_setting,
        'has_list_layout': has_list,
        'has_detail_layout': has_detail,
        'has_panel_layout': has_panel,
        'has_card_layout': has_card,
        'has_form_layout': has_form,
        'fully_covered': fully_covered,
        'needs_attention': needs_attention,
    }


class Command(BaseCommand):
    help = 'Audit layout coverage for all registered models'

    def add_arguments(self, parser):
        parser.add_argument('--json', action='store_true', help='Output as JSON')
        parser.add_argument('--gaps-only', action='store_true',
                            help='Only show models that need attention')

    def handle(self, *args, **options):
        results = audit_all_layouts()
        summary = audit_summary(results)

        if options.get('gaps_only'):
            results = [r for r in results if r['needs_attention']]

        if options.get('json'):
            output = {
                'summary': summary,
                'models': results,
            }
            self.stdout.write(json.dumps(output, indent=2))
            return

        # Human-readable table
        self.stdout.write('')
        self.stdout.write(f'  Layout Parade — {summary["total_models"]} models registered')
        self.stdout.write(f'  {summary["fully_covered"]} fully covered (all 5), '
                          f'{summary["needs_attention"]} need attention')
        self.stdout.write('')
        self.stdout.write(
            f'  {"model":<30} {"setting":>7} {"list":>6} {"detail":>6} '
            f'{"panel":>6} {"card":>6} {"form":>6}  gaps'
        )
        self.stdout.write('  ' + '-' * 105)

        for r in results:
            setting_mark = 'Y' if r['has_wc_model_setting'] else '-'
            list_mark = str(r['list_column_count']) if r['has_list_layout'] else '-'
            detail_mark = str(r['detail_field_count']) if r['has_detail_layout'] else '-'
            panel_mark = str(r['panel_column_count']) if r['has_panel_layout'] else '-'
            card_mark = str(r['card_count']) if r['has_card_layout'] else '-'
            form_mark = str(r['form_tab_count']) if r['has_form_layout'] else '-'
            gaps = ', '.join(r['gaps']) if r['gaps'] else ''
            style = self.style.WARNING if r['needs_attention'] else lambda x: x
            self.stdout.write(style(
                f'  {r["model"]:<30} {setting_mark:>7} {list_mark:>6} '
                f'{detail_mark:>6} {panel_mark:>6} {card_mark:>6} '
                f'{form_mark:>6}  {gaps}'
            ))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'  Summary: {summary["has_wc_model_setting"]}/{summary["total_models"]} settings, '
            f'{summary["has_list_layout"]} list, {summary["has_detail_layout"]} detail, '
            f'{summary["has_panel_layout"]} panel, {summary["has_card_layout"]} card, '
            f'{summary["has_form_layout"]} form'
        ))
