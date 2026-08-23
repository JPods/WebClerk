"""Template field resolver — resolves {{model.field}} placeholders against live records.

Two functions:
  resolve_template(template_str, context_dict) → resolved string
  get_template_fields(model_name) → available fields + related models

Used by: letters, emails, labels, external integrations, Alice.
All through one resolution path.
"""
import re
import logging
from typing import Any, Dict, List, Optional, Tuple

from django.db import models as dj_models

logger = logging.getLogger(__name__)

# Match {{model.field}} or {{model.field.subfield}}
PLACEHOLDER_RE = re.compile(r'\{\{(\w+(?:\.\w+)*)\}\}')


def _get_model_class(model_name: str):
    """Resolve model class from slug via wcapi registry."""
    from apps.core.services.wcapi_registry import get_model
    return get_model(model_name)


def _deep_get(obj, dotpath: str) -> Any:
    """Walk a dot-separated path on an object or dict.

    Handles: Django model fields, JSON dict fields, nested dicts.
    Returns None if any segment is missing.
    """
    parts = dotpath.split('.')
    current = obj
    for part in parts:
        if current is None:
            return None
        if isinstance(current, dict):
            current = current.get(part)
        elif hasattr(current, part):
            val = getattr(current, part)
            # If it's a FK, get the related object
            if callable(val) and not isinstance(val, str):
                try:
                    current = val()
                except Exception:
                    current = None
            else:
                current = val
        else:
            return None
    return current


def _format_value(value: Any) -> str:
    """Format a value for display in resolved text."""
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'Yes' if value else 'No'
    if isinstance(value, float):
        # Currency-like formatting for common money fields
        if abs(value) >= 0.01:
            return f'{value:,.2f}'
        return str(value)
    if isinstance(value, dict):
        # For JSON fields, try common display patterns
        if 'en' in value:
            return str(value['en'])
        if 'display_name' in value:
            return str(value['display_name'])
        return str(value)
    if isinstance(value, list):
        return ', '.join(str(v) for v in value)
    return str(value)


def resolve_template(template_str: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve {{model.field}} placeholders in a template string.

    Args:
        template_str: Text with {{model.field.subfield}} placeholders.
        context: {"model_name": record_id_or_dict, ...}
            e.g. {"order": 29, "contact": 41}
            or   {"order": {"ida": "DEV-29", ...}}  (pre-loaded dict)

    Returns:
        {
            "resolved": "Dear Bill, ...",
            "fields_used": ["contact.name_first", "order.ida"],
            "fields_missing": ["order.ship_date"],
            "context_models": ["order", "contact"]
        }
    """
    # Load records for each model in context
    records: Dict[str, Any] = {}
    for model_name, ref in context.items():
        if isinstance(ref, dict):
            # Already a dict — use directly
            records[model_name] = ref
        elif isinstance(ref, int) or (isinstance(ref, str) and ref.isdigit()):
            # Load from database
            model_cls = _get_model_class(model_name)
            if model_cls:
                try:
                    records[model_name] = model_cls.objects.get(pk=int(ref))
                except model_cls.DoesNotExist:
                    records[model_name] = None
            else:
                records[model_name] = None
        else:
            records[model_name] = None

    # Also load related records automatically (customer from order, etc.)
    for model_name, record in list(records.items()):
        if record is None:
            continue
        # Auto-resolve common FKs if not already in context
        for fk_name in ['customer', 'vendor', 'contact', 'manufacturer']:
            if fk_name not in records:
                fk_id = None
                if isinstance(record, dict):
                    fk_id = record.get(f'{fk_name}_id') or record.get(fk_name)
                else:
                    fk_id = getattr(record, f'{fk_name}_id', None)
                if fk_id and isinstance(fk_id, (int, str)):
                    fk_cls = _get_model_class(fk_name)
                    if fk_cls:
                        try:
                            records[fk_name] = fk_cls.objects.get(pk=int(fk_id))
                        except Exception:
                            pass

    fields_used = []
    fields_missing = []

    def replacer(match):
        full_path = match.group(1)
        parts = full_path.split('.', 1)
        model_name = parts[0]
        field_path = parts[1] if len(parts) > 1 else None

        record = records.get(model_name)
        if record is None:
            fields_missing.append(full_path)
            return match.group(0)  # Leave placeholder as-is

        if field_path is None:
            # Just {{model}} — use string representation
            val = str(record)
        else:
            val = _deep_get(record, field_path)

        if val is None:
            fields_missing.append(full_path)
            return match.group(0)

        fields_used.append(full_path)
        return _format_value(val)

    resolved = PLACEHOLDER_RE.sub(replacer, template_str)

    return {
        'resolved': resolved,
        'fields_used': fields_used,
        'fields_missing': fields_missing,
        'context_models': list(records.keys()),
    }


def get_template_fields(model_name: str) -> Dict[str, Any]:
    """Return available fields for a model, including JSON subfields and related models.

    Args:
        model_name: e.g. "order", "invoice", "contact"

    Returns:
        {
            "model": "order",
            "fields": ["ida", "status", "dt", "due_date", ...],
            "json_fields": {
                "totals": ["total", "subtotal", "tax", "shipping", "received", "balance"],
                "price": ["unit", "extended", "discount"],
                ...
            },
            "related": {
                "customer": ["ida", "display_name", "company", "email", "phone", "credit_limit"],
                "contact": ["name_first", "name_last", "email", "phone"],
                "lines": ["item.ida", "item.description", "quantity.staged", "price.unit", "price.extended"]
            },
            "examples": [
                "{{order.ida}}", "{{order.totals.total}}", "{{customer.company}}", "{{contact.name_first}}"
            ]
        }
    """
    model_cls = _get_model_class(model_name)
    if not model_cls:
        return {'error': f'Model {model_name} not found'}

    # Get direct fields
    fields = []
    json_fields = {}
    fk_models = {}

    for field in model_cls._meta.get_fields():
        name = field.name
        if name.startswith('_') or name in ('id', 'password'):
            continue

        if isinstance(field, dj_models.JSONField):
            fields.append(name)
            # Document known JSON subfields
            json_fields[name] = _get_json_subfields(model_name, name)
        elif isinstance(field, (dj_models.ForeignKey, dj_models.OneToOneField)):
            related_model = field.related_model
            fk_name = name.replace('_fk', '').replace('_id', '')
            fk_models[fk_name] = _get_model_fields_simple(related_model)
            fields.append(f'{name}_id')
        elif isinstance(field, (dj_models.ManyToOneRel, dj_models.ManyToManyRel)):
            continue  # Skip reverse relations
        else:
            fields.append(name)

    # Build examples
    examples = [f'{{{{{model_name}.{f}}}}}' for f in fields[:5]]
    for jf, subfields in json_fields.items():
        if subfields:
            examples.append(f'{{{{{model_name}.{jf}.{subfields[0]}}}}}')
    for rel_name, rel_fields in fk_models.items():
        if rel_fields:
            examples.append(f'{{{{{rel_name}.{rel_fields[0]}}}}}')

    return {
        'model': model_name,
        'fields': sorted(fields),
        'json_fields': json_fields,
        'related': fk_models,
        'examples': examples,
    }


def _get_json_subfields(model_name: str, field_name: str) -> List[str]:
    """Return known subfield keys for common JSON fields."""
    KNOWN_JSON = {
        'totals': ['total', 'subtotal', 'tax', 'shipping', 'other', 'received', 'balance',
                    'sell_total', 'cost_total', 'margin', 'margin_pct'],
        'price': ['unit', 'extended', 'discount', 'discount_pct', 'base', 'retail',
                  'wholesale', 'distributor', 'sample', 'currency'],
        'cost': ['unit', 'extended', 'standard', 'avg', 'last'],
        'quantity': ['staged', 'active', 'remaining', 'received', 'shipped',
                     'on_hand', 'on_so', 'on_po', 'on_p', 'available'],
        'item': ['item_id', 'ida_item', 'description', 'unit_measure'],
        'tax': ['rate', 'amount', 'jurisdiction', 'taxable_amount'],
        'physical': ['weight', 'dimensions', 'packages'],
        'finance': ['payment_terms', 'credit_limit', 'balance'],
        'metadata': ['training', 'source', 'project_name'],
        'refs': ['links', 'source'],
        'comments': ['notes', 'public', 'internal'],
        'action': ['en'],
        'description': ['en'],
    }
    return KNOWN_JSON.get(field_name, [])


def _get_model_fields_simple(model_cls) -> List[str]:
    """Get simple field names from a model (no reverse relations)."""
    fields = []
    for field in model_cls._meta.get_fields():
        name = field.name
        if name.startswith('_') or name in ('id', 'password'):
            continue
        if isinstance(field, (dj_models.ManyToOneRel, dj_models.ManyToManyRel)):
            continue
        if isinstance(field, (dj_models.ForeignKey, dj_models.OneToOneField)):
            fields.append(f'{name}_id')
        else:
            fields.append(name)
    return sorted(fields[:20])  # Cap at 20 for readability
