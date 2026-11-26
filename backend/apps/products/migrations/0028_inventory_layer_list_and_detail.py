"""The inventory layer's list and detail show what a layer is (Bill, 2026-11-26: "inventory_layer
records are thinly populated with data").

The generated list had four columns, purpose, status, item_ida and lot: two are never set on a
layer and one rarely. The generated detail named fields the model no longer has (source_doc_type,
source_doc_id, dt_locked, serial_numbers, is_deleted) and put the layer's quantity and cost after
config, metadata, refs and prefs, as two JSON blocks. Now: each count and each cost is a field
of its own, and what the layer holds and what it is carried at come first
(Bill: "canonical fields and model specific jsons should be at the top ... with .refs, .prefs,
metadata and config below"). A list or detail someone already changed from the generated one is
left as it is. Frozen: the fields are literals here.
"""
from django.db import migrations

OLD_LIST = ['purpose', 'status', 'item_ida', 'lot']
LIST = ['item_ida', 'warehouse', 'quantity.received', 'quantity.issued', 'quantity.scrapped',
        'cost.unit_po', 'cost.landed', 'parent_model', 'parent_id', 'lot', 'dt_created']
OLD_DETAIL_START = ['is_active', 'purpose', 'status', 'item_ida', 'warehouse', 'lot']
QUANTITY = ['quantity.received', 'quantity.issued', 'quantity.scrapped']
COST = ['cost.unit_po', 'cost.freight', 'cost.duty', 'cost.handling', 'cost.vat', 'cost.landed',
        'cost.moving_avg', 'cost.trend_pct', 'cost.currency']
# Each count and each cost is its own field, not a JSON block to open (Bill, 2026-11-26: "Leafs
# should show counts, costs, and other key canonical and leaf values").
DETAIL = (['item_ida', 'item', 'warehouse', 'lot', 'serial_batch', 'parent_model', 'parent_id']
          + QUANTITY + COST
          + ['status', 'purpose', 'is_active', 'is_archived', 'dt_created', 'dt_modified', 'dt_approved',
             'dt_last_used', 'times_used', 'health_rating', 'security_level', 'id', 'uuid', 'version',
             'actions', 'comments', 'refs', 'prefs', 'metadata', 'config'])
GROUPS = [
    {'key': 'layer', 'label': 'Layer',
     'fields': ['item_ida', 'item', 'warehouse', 'lot', 'serial_batch', 'parent_model', 'parent_id']},
    {'key': 'quantity', 'label': 'Quantity', 'fields': list(QUANTITY)},
    {'key': 'cost', 'label': 'Cost', 'fields': list(COST)},
    {'key': 'status', 'label': 'Status', 'fields': ['status', 'purpose', 'is_active', 'is_archived']},
    {'key': 'dates', 'label': 'Dates', 'fields': ['dt_created', 'dt_modified', 'dt_approved', 'dt_last_used']},
    {'key': 'system', 'label': 'System',
     'fields': ['times_used', 'health_rating', 'security_level', 'id', 'uuid', 'version']},
]


def remade(config):
    """The definition's config with its generated list, detail and field groups replaced."""
    config = dict(config or {})
    layout = config.get('layout')
    if not isinstance(layout, dict):
        return config
    layout = dict(layout)
    lst = ((layout.get('list') or {}).get('default') or {}) if isinstance(layout.get('list'), dict) else {}
    columns = lst.get('columns')
    if isinstance(columns, list) and [c.get('field') for c in columns if isinstance(c, dict)] == OLD_LIST:
        layout['list'] = {**layout['list'], 'default': {**lst, 'columns': [
            {'field': f, 'label': f.split('.')[-1], 'visible': True} for f in LIST]}}
    det = ((layout.get('detail') or {}).get('default') or {}) if isinstance(layout.get('detail'), dict) else {}
    fields = det.get('fields')
    generated = isinstance(fields, list) and fields[:len(OLD_DETAIL_START)] == OLD_DETAIL_START
    if generated:
        layout['detail'] = {**layout['detail'], 'default': {**det, 'fields': list(DETAIL)}}
    config['layout'] = layout
    if generated and isinstance(config.get('field_groups'), list):
        config['field_groups'] = [dict(g) for g in GROUPS]
    return config


def forward(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    for s in Setting.objects.filter(purpose='wc:model', parent_model__iexact='inventory_layer'):
        if not isinstance(s.config, dict):
            continue
        config = remade(s.config)
        if config != s.config:
            Setting.objects.filter(pk=s.pk).update(config=config)


class Migration(migrations.Migration):
    dependencies = [('products', '0027_inventory_layer_form_and_leaves')]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
