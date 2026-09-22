"""D02 (Bill, 2026-09-21): one landed-cost engine, and each landed cost names its own basis.

allocations.method was one word for the whole receipt, and nothing read it — the live
engine spread by amount regardless. It is now {freight, duty, handling, vat} → value |
weight | quantity. An existing word is carried to all four components, so a receipt that
asked for 'quantity' now gets it; the recompute on next save honours it.
"""
from django.db import migrations

COMPONENTS = ('freight', 'duty', 'handling', 'vat')
BASES = ('value', 'weight', 'quantity')


def per_component(apps, schema_editor):
    Receipt = apps.get_model('transactions', 'Receipt')
    for receipt in Receipt.objects.all().only('pk', 'allocations'):
        alloc = receipt.allocations if isinstance(receipt.allocations, dict) else {}
        method = alloc.get('method')
        if isinstance(method, dict):
            continue
        word = method if method in BASES else 'value'
        alloc['method'] = {c: word for c in COMPONENTS}
        Receipt.objects.filter(pk=receipt.pk).update(allocations=alloc)


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0039_rep_assignment'),
    ]

    operations = [
        migrations.RunPython(per_component, migrations.RunPython.noop),
    ]
