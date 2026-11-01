"""The order every list reads in — one rule for lists, panels and reports (Bill, 2026-11-01).

1. What the caller asked (?ordering=, a column click, a saved search).
2. The model's config.orderby — its wc:model Setting, chosen on purpose.
3. sequence, when the model has one.
4. Newest first.

id ends every order, so rows that tie keep their places from one read to the next.

orderby leads sequence because sequence alone is rarely the whole order. A bill of materials
ordered by sequence lists every parent's line 1, then every line 2; what is wanted is each
parent's lines together, in sequence: ["parent_item_id", "sequence"].

DEFAULT is the first guess seeded into config.orderby; the company changes it on the Setting.
"""
from __future__ import annotations

from typing import Optional

from apps.core.services import definition

_LINES = ('order', 'invoice', 'quote', 'purchase', 'receipt', 'requisition', 'workorder')

#: model key -> config.orderby seeded where the definition has none.
DEFAULT: dict[str, list[str]] = {
    'bill_of_material': ['parent_item_id', 'sequence'],
    # An item line before a scope line (no item): ascending puts nulls last in PostgreSQL.
    'catalog_line': ['catalog_id', 'item_id'],
    **{f'{head}_line': [f'{head}_id', 'line_number'] for head in _LINES},
    'domain': ['contact_id', 'sequence'],
    'question_answer': ['document_id', 'sequence'],
    'linkage': ['group_id', 'sequence'],
    'report': ['target_model', 'sort_order', 'name'],
    'tag': ['sequence', 'name'],
    'specification': ['item_id', 'name'],
    'item_xref': ['item_id', '-is_preferred', 'purpose'],
    'contact': ['name_last', 'name_first'],
    'statement_line': ['-dt_transaction'],
    'currency': ['ida'],
    'gl_account': ['ida'],
    'tax_jurisdiction': ['ida'],
    'term': ['name'],
    'warehouse': ['name'],
    # A sequence that orders only within a parent or connection: newest first reads better.
    'action': ['-dt_created'],
    'document': ['-dt_created'],
    'pending': ['-id'],
}


def valid(fields, ModelCls) -> list[str]:
    """The fields of `fields` (a list, or a comma-separated string) the model has, by name or
    column (parent_item or parent_item_id); a leading '-' is descending."""
    if isinstance(fields, str):
        fields = fields.split(',')
    if not isinstance(fields, list):
        return []
    names = set()
    for f in ModelCls._meta.concrete_fields:
        names.update((f.name, f.attname))
    return [f.strip() for f in fields
            if isinstance(f, str) and f.strip().lstrip('-') in names]


def _configured(raw) -> list:
    return raw if isinstance(raw, list) else []


def order(key: str, ModelCls, asked: Optional[list[str]] = None) -> list[str]:
    """The order_by for a list of `key`, from what was asked down to newest first."""
    from apps.core.services.access import model_key
    key = model_key(key) or key            # the view's key may be squashed: billofmaterial
    fields = asked or valid(definition.part(key, ('orderby',), _configured), ModelCls)
    if not fields:
        names = {f.name for f in ModelCls._meta.concrete_fields}
        fields = ['sequence'] if 'sequence' in names else (
            ['-dt_created'] if 'dt_created' in names else [])
    if not any(f.lstrip('-') in ('id', 'pk') for f in fields):
        # Ties run the way the first field does: newest first breaks ties newest first.
        fields = [*fields, '-id' if fields and fields[0].startswith('-') else 'id']
    return fields
