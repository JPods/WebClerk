"""Best guesses at a model's layout, from its fields — for a model layouts.json does not hold.

Each guess reads only the model's concrete fields. They replace the four seeders that each
guessed a part (seed_default_layouts, seed_card_layouts, seed_panel_columns,
seed_model_definitions' columns); the per-model choices those seeders held are in
layouts.json now, taken from the layouts in use (Bill, 2026-10-29).
"""
from __future__ import annotations

from typing import Optional

TRANSACTIONS = {'order', 'invoice', 'quote', 'purchase', 'receipt', 'requisition', 'workorder'}
SELL = {'order', 'invoice', 'quote'}
TABS = ['contacts', 'actions', 'touches', 'documents', 'files']

# Plumbing: never shown.
SKIP = {'id', 'uuid', 'version', 'security_level', 'times_used', 'is_archived', 'is_staff',
        'is_superuser', 'config', 'metadata', 'refs', 'prefs', 'actions', 'password', 'groups',
        'user_permissions', 'last_login', 'search_vector', 'row_version', 'line_increment'}
# System timestamps: shown in the schedule card and detail, never as a list column.
SYSTEM_DT = {'dt_created', 'dt_modified', 'dt_approved', 'dt_last_used', 'dt_joined', 'dt_kanban',
             'dt_reconciliation', 'dt_processed', 'dt_start_original', 'dt_end_original'}
IDENTITY = ['ida', 'name', 'display_name', 'name_first', 'name_last', 'action', 'subject',
            'title', 'sku', 'description', 'status', 'purpose', 'kind', 'org_type', 'role',
            'action_type', 'kanban_column', 'scope']
# List columns, in the order a person scans: who, what, value, why, when, status.
TIERS = [
    ({'ida'}, 100, 'left'),
    ({'company', 'attention', 'contact', 'customer', 'vendor', 'assigned_to', 'display_name',
      'rep', 'name_first', 'name_last', 'manufacturer'}, 140, 'left'),
    ({'name', 'action', 'subject', 'description', 'sku', 'kind', 'uom', 'action_type', 'type',
      'scope', 'parent_model', 'category', 'title'}, 160, 'left'),
    ({'total', 'balance', 'amount', 'price', 'cost', 'sell', 'fee_amount'}, 100, 'right'),
    ({'purpose', 'reason', 'explanation', 'intent', 'objective'}, 140, 'left'),
    ({'dt_start', 'dt_deadline', 'dt_needed', 'dt_cash', 'dt_completed', 'dt_expected',
      'dt_end'}, 100, 'center'),
    ({'status', 'process', 'priority', 'percent_complete', 'difficulty'}, 90, 'center'),
]
MAX_LIST, MAX_PANEL = 12, 6
EDIT_RULES = {'status_field': 'status', 'locked_statuses': []}


def _fields(key: str) -> dict:
    """{name: field} of the model's concrete columns, without plumbing; {} when not a model."""
    from apps.core.utils import registry
    model = registry.resolve(key)
    if model is None:
        return {}
    names = {f.name: f for f in model._meta.concrete_fields}
    fk_ids = {n for n in names if n.endswith('_id') and n[:-3] in names}
    return {n: f for n, f in names.items() if n not in SKIP and n not in fk_ids}


def _json(field) -> bool:
    return field.get_internal_type() == 'JSONField'


def _spec(name: str, field=None) -> dict:
    spec = {'field': name, 'label': name}
    choices = [c[0] for c in (getattr(field, 'choices', None) or []) if c[0] not in (None, '')]
    if choices:
        spec.update(type='select', options=choices)
    elif name.startswith('dt_'):
        spec['type'] = 'date'
    return spec


def list_columns(key: str, limit: int = MAX_LIST) -> list:
    fields = _fields(key)
    available = {n for n, f in fields.items() if not _json(f) and n not in SYSTEM_DT}
    columns, used = [], set()
    for names, width, align in TIERS:
        for name in sorted(names & available - used):
            if len(columns) >= limit:
                return columns
            spec = {'field': name, 'label': name, 'width': width, 'align': align, 'visible': True}
            if name.startswith('dt_'):
                spec['format'] = 'date'
            columns.append(spec)
            used.add(name)
    for name in sorted(available - used):
        if len(columns) >= limit:
            break
        columns.append({'field': name, 'label': name, 'width': 120, 'align': 'left', 'visible': True})
    return columns


def detail_fields(key: str) -> list:
    """Every field worth reading: plain fields first, then JSON, then system dates."""
    fields = _fields(key)
    plain = [n for n, f in fields.items() if not _json(f) and n not in SYSTEM_DT]
    nested = [n for n, f in fields.items() if _json(f)]
    system = [n for n in fields if n in SYSTEM_DT]
    return plain + nested + system


def cards(key: str) -> dict:
    """Named cards: identity, details, schedule, and financial for a transaction."""
    fields = _fields(key)
    identity = []
    for name in IDENTITY:
        if name in fields:
            field = fields[name]
            identity.append({'field': f'{name}.en', 'label': name} if _json(field) else _spec(name, field))
    taken = {s['field'].split('.')[0] for s in identity}
    details = [_spec(n, f) for n, f in sorted(fields.items())
               if n not in taken and not n.startswith('dt_') and not _json(f)
               and f.get_internal_type() != 'BooleanField']
    schedule = [_spec(n) for n in sorted(fields) if n.startswith('dt_')]
    out = {}
    for name, specs in (('identity', identity), ('details', details), ('schedule', schedule)):
        if specs:
            out[name] = {'title': name, 'fields': specs}
    if key in TRANSACTIONS:
        out['financial'] = {'title': 'financial', 'fields': [
            {'field': f, 'label': f} for f in ('company.name', 'totals.amount', 'totals.total',
                                               'totals.balance', 'totals.tax')]}
    return out


def panel(key: str) -> list:
    """Columns when the model shows inside another record's page."""
    return [{k: v for k, v in c.items() if k in ('field', 'label', 'width', 'align', 'format')}
            for c in list_columns(key, MAX_PANEL)]


def form(key: str, card_specs: Optional[dict] = None) -> dict:
    """A header of the model's cards, its lines for a transaction, comments, and the tabs."""
    card_specs = card_specs if card_specs is not None else cards(key)
    sections = []
    if card_specs:
        sections.append({'type': 'header', 'layout': 'three-column', 'columns': [
            {'title': spec.get('title', name), 'fields': spec.get('fields', [])}
            for name, spec in card_specs.items()]})
    if key in TRANSACTIONS:
        sections.append({'type': 'line_card', 'family': family_of(key), 'toolbar': ['L', 'S', 'XR', 'M'],
                         'actions': []})
    sections.append(header_comments())
    sections.append({'type': 'tabs', 'tabs': [{'label': t, 'content': t} for t in TABS]})
    return {'list': 'default', 'detail': 'default', 'model': key, 'family': family_of(key),
            'edit_rules': dict(EDIT_RULES), 'sections': sections}


def family_of(key: str) -> str:
    if key in TRANSACTIONS:
        return 'sell' if key in SELL else 'exec'
    return 'core'


def header_comments() -> dict:
    return {'type': 'panel', 'label': 'comments', 'content': 'comments', 'config': {'channels': [
        {'key': 'process', 'label': 'process', 'color': 'var(--db-accent-green)'},
        {'key': 'public', 'label': 'public', 'color': 'var(--db-accent)'},
        {'key': 'partner', 'label': 'foreign', 'color': 'var(--db-accent-purple)'}]}}
