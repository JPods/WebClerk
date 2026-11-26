"""A receipt line's share of each charge becomes its own figure, cost.landed (Bill, 2026-11-25).

Bill: "The point to make to users changing a line's values is that it does not recalculate other
lines. If they wish to recalc, they should change at the receipt level and re-run the spreader."
Until now a save spread every charge over the lines (after the user's pins, cost.landed_override)
and kept only the answer, in totals.landed. Now the line holds its share and a save never spreads.

1. Every receipt line takes the shares it already carries: cost.landed = its totals.landed (the
   non-zero components), so no receipt's layers or totals move. cost.landed_override is removed.
2. Every model definition's access sets name the leaves by their new path
   (cost.landed_override.<comp> becomes cost.landed.<comp>), and the receipt's sets that read
   totals learn totals.unallocated.<comp> ("a leaf added later is in no list until someone adds
   it", Bill 2026-09-20). Frozen: the leaves are literals here.
"""
from django.db import migrations

COMPONENTS = ('freight', 'duty', 'handling', 'vat')
UNALLOCATED = tuple(f'totals.unallocated.{c}' for c in COMPONENTS)


def line_cost(cost, totals):
    """The line's cost with its shares taken from what its totals carry and the pins gone."""
    cost = dict(cost or {})
    cost.pop('landed_override', None)
    carried = (totals or {}).get('landed') if isinstance(totals, dict) else None
    shares = {c: float(carried.get(c) or 0) for c in COMPONENTS if carried and carried.get(c)}
    if shares:
        cost['landed'] = shares
    else:
        cost.pop('landed', None)
    return cost


def renamed(config, is_receipt):
    """The definition's config with its access sets renamed and, for the receipt, grown."""
    config = dict(config or {})
    access = config.get('access')
    if not isinstance(access, dict) or not isinstance(access.get('sets'), dict):
        return config
    sets = {}
    for name, leaves in access['sets'].items():
        if not isinstance(leaves, list):
            sets[name] = leaves
            continue
        out = [l.replace('cost.landed_override.', 'cost.landed.') if isinstance(l, str) else l for l in leaves]
        if is_receipt and 'totals.total' in out:
            out += [l for l in UNALLOCATED if l not in out]
        sets[name] = sorted(out) if all(isinstance(l, str) for l in out) else out
    config['access'] = {**access, 'sets': sets}
    return config


def forward(apps, schema_editor):
    ReceiptLine = apps.get_model('transactions', 'ReceiptLine')
    for line in ReceiptLine.objects.all().only('id', 'cost', 'totals').iterator():
        cost = line_cost(line.cost, line.totals)
        if cost != (line.cost or {}):
            ReceiptLine.objects.filter(pk=line.pk).update(cost=cost)

    Setting = apps.get_model('core', 'Setting')
    touched = set()
    for s in Setting.objects.filter(purpose='wc:model'):
        if not isinstance(s.config, dict):
            continue
        config = renamed(s.config, (s.parent_model or '').lower() == 'receipt')
        if config != s.config:
            Setting.objects.filter(pk=s.pk).update(config=config)
            touched.add((s.parent_model or '').lower())
    from apps.core.services.access import clear_cache
    for model in touched:
        clear_cache(model)


class Migration(migrations.Migration):
    dependencies = [('transactions', '0061_purchase_form_drops_bill_to_column')]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
