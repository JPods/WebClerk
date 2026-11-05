"""Form fields the door would refuse (2026-11-05): a layout edits fields the model has.

The scan after the customer fix (display_name) found twenty more editable layout fields that are
no field and no leaf: cash contact (the field is contact_id) and notes
(metadata.reconciliation.notes); receipt's purchase.* party display (read-only), its landed-cost
entries (allocations.freight / duty / handling / vat, allocations.method read-only); requisition's
guessed transaction fields (company, phone, attention, address_full, email, ship_via, terms,
dt_needed, source_name, priority — the model has none; dropped); other_org's list display_name
(company).
"""
from django.db import migrations

SPEC = {
    "cash": {
        "contact": [
            "rename",
            "contact_id"
        ],
        "notes": [
            "rename",
            "metadata.reconciliation.notes"
        ]
    },
    "receipt": {
        "purchase.company": [
            "readonly",
            None
        ],
        "purchase.phone": [
            "readonly",
            None
        ],
        "purchase.attention": [
            "readonly",
            None
        ],
        "purchase.address_full": [
            "readonly",
            None
        ],
        "purchase.email": [
            "readonly",
            None
        ],
        "purchase.ida": [
            "readonly",
            None
        ],
        "vendor_invoice_freight": [
            "rename",
            "allocations.freight"
        ],
        "duty": [
            "rename",
            "allocations.duty"
        ],
        "handling": [
            "rename",
            "allocations.handling"
        ],
        "vat": [
            "rename",
            "allocations.vat"
        ],
        "allocation_method": [
            "readonly",
            "allocations.method"
        ]
    },
    "requisition": {
        "company": [
            "drop",
            None
        ],
        "phone": [
            "drop",
            None
        ],
        "attention": [
            "drop",
            None
        ],
        "address_full": [
            "drop",
            None
        ],
        "email": [
            "drop",
            None
        ],
        "ship_via": [
            "drop",
            None
        ],
        "terms": [
            "drop",
            None
        ],
        "dt_needed": [
            "drop",
            None
        ],
        "source_name": [
            "drop",
            None
        ],
        "priority": [
            "drop",
            None
        ]
    },
    "other_org": {
        "display_name": [
            "rename",
            "company"
        ]
    }
}


def _fix(node, spec):
    if isinstance(node, dict):
        if isinstance(node.get('fields'), list):
            out = []
            for f in node['fields']:
                if isinstance(f, dict) and f.get('field') in spec:
                    kind, new = spec[f['field']]
                    if kind == 'drop':
                        continue
                    g = dict(f)
                    if new:
                        g['field'] = new
                        g['label'] = f.get('label') or new.split('.')[-1]
                    if kind == 'readonly':
                        g['type'] = 'readonly'
                    out.append(g)
                else:
                    out.append(_fix(f, spec))
            node = {**node, 'fields': out}
        if isinstance(node.get('columns'), list):
            cols = [_fix(c, spec) for c in node['columns']]
            node = {**node, 'columns': [c for c in cols if not (isinstance(c, dict) and 'fields' in c and not c['fields'])]}
        return {k: (_fix(v, spec) if k not in ('fields', 'columns') else v) for k, v in node.items()}
    if isinstance(node, list):
        return [_fix(x, spec) for x in node]
    return node


def _fix_list(cols, spec):
    out = []
    for c in cols:
        if isinstance(c, dict) and c.get('field') in spec:
            kind, new = spec[c['field']]
            if kind == 'drop':
                continue
            c = {**c, 'field': new or c['field']}
        out.append(c)
    return out


def _apply(layout, model):
    spec = SPEC.get(model)
    if not spec or not isinstance(layout, dict):
        return layout
    lay = dict(layout)
    for part in ('form', 'card'):
        if isinstance(lay.get(part), dict):
            lay[part] = _fix(lay[part], spec)
    if isinstance(lay.get('list'), dict):
        lay['list'] = {k: ({**v, 'columns': _fix_list(v['columns'], spec)}
                           if isinstance(v, dict) and isinstance(v.get('columns'), list) else v)
                       for k, v in lay['list'].items()}
    return lay


def forward(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    for s in Setting.objects.filter(purpose='wc:model', parent_model__in=list(SPEC)):
        if isinstance(s.config, dict) and 'layout' in s.config:
            layout = _apply(s.config['layout'], s.parent_model)
            if layout != s.config['layout']:
                Setting.objects.filter(pk=s.pk).update(config={**s.config, 'layout': layout})


class Migration(migrations.Migration):
    dependencies = [('core', '0059_org_forms_company_not_display_name')]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
