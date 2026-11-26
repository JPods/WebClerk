"""An inventory layer's form can show what the layer holds (Bill, 2026-11-26: "db.form for
inventory_layer looks very hard to see or find values").

The layer's cost was mapped to the transaction cost schema and its quantity to none, so the stored
'all' access set named cost leaves a layer does not have and none of the ones it does: the door let
out only cost.freight and cost.handling. This:

1. replaces the layer's cost leaves in its stored 'all' set with the layer's own and adds its
   quantity leaves ("a leaf added later is in no list until someone adds it", Bill, 2026-09-20);
2. replaces the generated form header (status, purpose, health_rating, dates) with three columns:
   the layer, its quantity, its cost. A header someone already edited to show quantity or cost is
   left as it is.

Frozen: the leaves and the layout are literals here.
"""
from django.db import migrations

COST = ('cost.currency', 'cost.duty', 'cost.exchange_rate', 'cost.fifo_snapshot', 'cost.freight',
        'cost.handling', 'cost.landed', 'cost.lifo_snapshot', 'cost.moving_avg', 'cost.scrap_cost',
        'cost.trend_pct', 'cost.unit_po', 'cost.vat')
QUANTITY = ('quantity.issued', 'quantity.received', 'quantity.scrapped')


def _fields(*names):
    return [{'field': name, 'label': name.split('.')[-1]} for name in names]


HEADER = {
    'type': 'header',
    'layout': 'three-column',
    'columns': [
        {'title': 'layer', 'fields': _fields('item', 'item_ida', 'warehouse', 'lot', 'serial_batch',
                                            'parent_model', 'parent_id', 'status')
            + [{'type': 'date', 'field': 'dt_created', 'label': 'dt_created'},
               {'type': 'date', 'field': 'dt_modified', 'label': 'dt_modified'}]},
        {'title': 'quantity', 'fields': _fields('quantity.received', 'quantity.issued', 'quantity.scrapped')},
        {'title': 'cost', 'fields': _fields('cost.unit_po', 'cost.freight', 'cost.duty', 'cost.handling',
                                           'cost.vat', 'cost.landed', 'cost.moving_avg', 'cost.currency')},
    ],
}


def _shows_stock(section) -> bool:
    return any(str(f.get('field', '')).startswith(('quantity.', 'cost.'))
               for column in section.get('columns') or [] if isinstance(column, dict)
               for f in column.get('fields') or [] if isinstance(f, dict))


def remade(config):
    """The definition's config with its 'all' set corrected and its generated header replaced."""
    config = dict(config or {})
    access = config.get('access')
    if isinstance(access, dict) and isinstance(access.get('sets'), dict) \
            and isinstance(access['sets'].get('all'), list):
        kept = [l for l in access['sets']['all']
                if not (isinstance(l, str) and l.startswith(('cost.', 'quantity.')))]
        sets = {**access['sets'], 'all': sorted(set(kept) | set(COST) | set(QUANTITY))}
        config['access'] = {**access, 'sets': sets}
    layout = config.get('layout')
    form = (layout or {}).get('form') if isinstance(layout, dict) else None
    default = (form or {}).get('default') if isinstance(form, dict) else None
    sections = (default or {}).get('sections') if isinstance(default, dict) else None
    if isinstance(sections, list):
        out = [HEADER if (isinstance(s, dict) and s.get('type') == 'header' and not _shows_stock(s)) else s
               for s in sections]
        if out != sections:
            config['layout'] = {**layout, 'form': {**form, 'default': {**default, 'sections': out}}}
    return config


def forward(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    for s in Setting.objects.filter(purpose='wc:model', parent_model__iexact='inventory_layer'):
        if not isinstance(s.config, dict):
            continue
        config = remade(s.config)
        if config != s.config:
            Setting.objects.filter(pk=s.pk).update(config=config)
    from apps.core.services.access import clear_cache
    clear_cache('inventory_layer')


class Migration(migrations.Migration):
    dependencies = [('products', '0026_item_landed_class_access_leaves')]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
