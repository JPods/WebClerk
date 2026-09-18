"""Rename the stocking pair inside item.quantity and drop the dead vendor pair.

One pair beside on_hand: min (reorder point) and max (order up to).
inventory_min/max -> min/max; vendor_min/max deleted — nothing ever wrote them
(Bill, 2026-09-17).
"""
from django.db import migrations


def to_min_max(apps, schema_editor):
    Item = apps.get_model('products', 'Item')
    for item in Item.objects.exclude(quantity=None).only('pk', 'quantity').iterator():
        quantity = item.quantity if isinstance(item.quantity, dict) else None
        if not quantity:
            continue
        touched = {'inventory_min', 'inventory_max', 'vendor_min', 'vendor_max'} & set(quantity)
        if not touched:
            continue
        new = {k: v for k, v in quantity.items()
               if k not in ('inventory_min', 'inventory_max', 'vendor_min', 'vendor_max')}
        if 'inventory_min' in quantity:
            new['min'] = quantity['inventory_min']
        if 'inventory_max' in quantity:
            new['max'] = quantity['inventory_max']
        Item.objects.filter(pk=item.pk).update(quantity=new)


def back_to_inventory(apps, schema_editor):
    Item = apps.get_model('products', 'Item')
    for item in Item.objects.exclude(quantity=None).only('pk', 'quantity').iterator():
        quantity = item.quantity if isinstance(item.quantity, dict) else None
        if not quantity or not ({'min', 'max'} & set(quantity)):
            continue
        new = {k: v for k, v in quantity.items() if k not in ('min', 'max')}
        if 'min' in quantity:
            new['inventory_min'] = quantity['min']
        if 'max' in quantity:
            new['inventory_max'] = quantity['max']
        Item.objects.filter(pk=item.pk).update(quantity=new)


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0009_drop_orgitem_quantity_thresholds'),
    ]

    operations = [
        migrations.RunPython(to_min_max, back_to_inventory),
    ]
