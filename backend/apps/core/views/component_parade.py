"""
Component Parade — extract and serve layout components from wc:model Settings.

Endpoints:
  GET /wcapi/_component_parade/?type=panel   — all layout items of a given type, grouped by model
  GET /wcapi/_component_parade_preview/?model=customer&limit=10  — sample records for live preview

Layout types: panel, list, detail, card, form
"""
import logging

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models.setting import Setting
from apps.core.constants.model_registry import MODEL_REGISTRY, get_model_meta

logger = logging.getLogger(__name__)

VALID_TYPES = ('panel', 'list', 'detail', 'card', 'form', 'print')


def _extract_panels(layout: dict) -> list[dict]:
    """Extract panel layout items from config.layout."""
    items = []
    # layout.panel — flat list of DbFieldSpec
    panel = layout.get('panel', [])
    if isinstance(panel, list) and len(panel) > 0:
        items.append({
            'name': 'default',
            'kind': 'panel',
            'columns': len(panel),
            'spec': panel,
        })

    # layout.column.{name} — named column layouts (alternative panel format)
    col_section = layout.get('column', {})
    if isinstance(col_section, dict):
        for col_name, col_def in col_section.items():
            if not isinstance(col_def, dict):
                continue
            cols = col_def.get('columns', [])
            if isinstance(cols, list) and len(cols) > 0:
                items.append({
                    'name': col_name,
                    'kind': 'column',
                    'columns': len(cols),
                    'spec': col_def,
                })
    return items


def _extract_lists(layout: dict) -> list[dict]:
    """Extract list layout items from config.layout."""
    items = []
    list_section = layout.get('list', {})
    if isinstance(list_section, dict):
        for list_name, list_def in list_section.items():
            if not isinstance(list_def, dict):
                continue
            cols = list_def.get('columns', [])
            if isinstance(cols, list) and len(cols) > 0:
                items.append({
                    'name': list_name,
                    'kind': 'list',
                    'columns': len(cols),
                    'spec': list_def,
                })
    return items


def _extract_details(layout: dict) -> list[dict]:
    """Extract detail layout items from config.layout."""
    items = []
    detail_section = layout.get('detail', {})
    if isinstance(detail_section, dict):
        for detail_name, detail_def in detail_section.items():
            if not isinstance(detail_def, dict):
                continue
            sections = detail_def.get('sections', detail_def.get('fields', []))
            field_count = len(sections) if isinstance(sections, list) else 0
            if field_count > 0 or detail_def.get('sections'):
                items.append({
                    'name': detail_name,
                    'kind': 'detail',
                    'fields': field_count,
                    'spec': detail_def,
                })
    return items


def _extract_cards(layout: dict) -> list[dict]:
    """Extract card layout items from config.layout."""
    items = []
    card_section = layout.get('card')
    if isinstance(card_section, dict) and len(card_section) > 0:
        for card_name, card_def in card_section.items():
            if not isinstance(card_def, dict):
                continue
            fields = card_def.get('fields', [])
            items.append({
                'name': card_name,
                'kind': 'card',
                'fields': len(fields) if isinstance(fields, list) else 0,
                'spec': card_def,
            })
    elif isinstance(card_section, list) and len(card_section) > 0:
        for i, card_def in enumerate(card_section):
            name = card_def.get('title', f'card_{i}') if isinstance(card_def, dict) else f'card_{i}'
            fields = card_def.get('fields', []) if isinstance(card_def, dict) else []
            items.append({
                'name': name,
                'kind': 'card',
                'fields': len(fields) if isinstance(fields, list) else 0,
                'spec': card_def if isinstance(card_def, dict) else {},
            })
    return items


def _extract_forms(layout: dict) -> list[dict]:
    """Extract form layout items from config.layout."""
    items = []
    form_section = layout.get('form', {})
    if isinstance(form_section, dict):
        for form_name, form_def in form_section.items():
            if not isinstance(form_def, dict):
                continue
            has_header = bool(form_def.get('header'))
            has_lines = bool(form_def.get('lines'))
            has_tabs = isinstance(form_def.get('tabs'), list) and len(form_def.get('tabs', [])) > 0
            has_sections = isinstance(form_def.get('sections'), list) and len(form_def.get('sections', [])) > 0
            if has_header or has_lines or has_tabs or has_sections:
                items.append({
                    'name': form_name,
                    'kind': 'form',
                    'tabs': len(form_def.get('tabs', [])),
                    'has_header': has_header,
                    'has_lines': has_lines,
                    'spec': form_def,
                })
    return items


def _extract_prints(layout: dict) -> list[dict]:
    """Extract print layout items from config.layout."""
    items = []
    print_section = layout.get('print', {})
    if isinstance(print_section, dict):
        for print_name, print_def in print_section.items():
            if not isinstance(print_def, dict):
                continue
            items.append({
                'name': print_name,
                'kind': 'print',
                'fields': len(print_def.get('fields', print_def.get('columns', []))),
                'spec': print_def,
            })
    return items


EXTRACTORS = {
    'panel': _extract_panels,
    'list': _extract_lists,
    'detail': _extract_details,
    'card': _extract_cards,
    'form': _extract_forms,
    'print': _extract_prints,
}


class ComponentParadeView(APIView):
    """Return all layout components of a given type, grouped by model."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        layout_type = request.query_params.get('type', '').strip().lower()
        if layout_type not in VALID_TYPES:
            return Response({
                'error': f'Invalid type. Use one of: {", ".join(VALID_TYPES)}',
            }, status=400)

        extractor = EXTRACTORS[layout_type]
        models = []

        for model_key in sorted(MODEL_REGISTRY.keys()):
            meta = get_model_meta(model_key)
            if not meta:
                continue

            canonical_key = meta.key
            wc_model = Setting.objects.filter(
                parent_model=canonical_key,
                purpose='wc:model',
                is_active=True,
            ).first()

            if not wc_model:
                continue

            cfg = wc_model.config if isinstance(wc_model.config, dict) else {}
            layout = cfg.get('layout', {})
            if not isinstance(layout, dict):
                continue

            items = extractor(layout)

            # For panels, also check standalone workbench_fields
            if layout_type == 'panel' and not items:
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
                            items.append({
                                'name': 'workbench',
                                'kind': 'panel',
                                'columns': len(panel),
                                'spec': panel,
                            })

            if items:
                models.append({
                    'model': model_key,
                    'singular': meta.singular,
                    'kind': meta.kind,
                    'items': items,
                })

        return Response({
            'type': layout_type,
            'total_models': len(models),
            'total_items': sum(len(m['items']) for m in models),
            'models': models,
        })


class ComponentParadePreviewView(APIView):
    """Return sample records for a model to render in the parade preview."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        model_name = request.query_params.get('model', '').strip().lower()
        limit = min(int(request.query_params.get('limit', '10')), 50)

        if not model_name:
            return Response({'error': 'model parameter required'}, status=400)

        meta = get_model_meta(model_name)
        if not meta:
            return Response({'error': f'Unknown model: {model_name}'}, status=404)

        try:
            ModelClass = meta.import_model()
            qs = ModelClass.objects.all().order_by('-id')[:limit]
            records = []
            for obj in qs:
                record = {'id': obj.id}
                for field in obj._meta.get_fields():
                    if not field.concrete:
                        continue
                    name = field.name
                    val = getattr(obj, name, None)
                    # Serialize to JSON-safe values
                    if hasattr(val, 'isoformat'):
                        val = val.isoformat()
                    elif hasattr(val, '__iter__') and not isinstance(val, (str, dict, list)):
                        val = str(val)
                    record[name] = val
                records.append(record)

            return Response({
                'model': model_name,
                'singular': meta.singular,
                'count': len(records),
                'records': records,
            })
        except Exception as e:
            logger.exception('ComponentParadePreview error for %s', model_name)
            return Response({'error': str(e)}, status=500)
