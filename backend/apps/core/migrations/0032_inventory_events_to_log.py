"""Inventory events into the one Log (Bill, 2026-10-28: fold in all the logs): purpose
inventory, action = event_type, about item / item_id. Their LLM restatement becomes the readable
line (config.name); event_id is kept as the Log's uuid; created_at (timestamptz) → UTC epoch
ms. Refuses if the Log took fewer rows than the source held."""
from django.db import migrations
from django.db.models import CharField, F
from django.db.models.functions import Cast


def _num(v):
    return float(v) if v is not None else None


def copy_inventory_events(apps, schema_editor):
    Event = apps.get_model('ai_assistant', 'InventoryEvent')
    Log = apps.get_model('core', 'Log')
    rows = []
    for e in Event.objects.order_by('created_at').iterator():
        dt = int(e.created_at.timestamp() * 1000) if e.created_at else 0
        doc = ({'model': e.transaction_type, 'id': e.transaction_id, 'ida': e.transaction_ida}
               if e.transaction_type else {})
        details = {k: v for k, v in {
            'category': e.category, 'item_code': e.item_code, 'document': doc,
            'line_id': e.line_id, 'quantity_before': _num(e.quantity_before),
            'quantity_after': _num(e.quantity_after), 'quantity_delta': _num(e.quantity_delta),
            'unit_cost': _num(e.unit_cost), 'unit_price': _num(e.unit_price),
            'on_hand': _num(e.on_hand), 'on_order': _num(e.on_order),
            'on_purchase': _num(e.on_purchase), 'available': _num(e.available),
            'reorder_point': _num(e.reorder_point),
            'org_id': e.customer_id or e.vendor_id, 'reason': e.reason,
            'payload': e.payload}.items() if v not in (None, '', {}, [])}
        config = {'details': details}
        if e.llm_summary:
            config['name'] = e.llm_summary
        rows.append(Log(uuid=e.event_id, purpose='inventory', action=e.event_type or '',
                        user_id=None, model_name='item', record_id=e.item_id, config=config,
                        refs={'actor': {'kind': 'system' if e.is_system else 'user',
                                        'source': 'signal'}},
                        dt_created=dt, dt_modified=dt))
    Log.objects.bulk_create(rows, batch_size=500)
    Log.objects.filter(ida='').update(ida=Cast(F('id'), output_field=CharField()))
    n_old, n_new = Event.objects.count(), Log.objects.filter(purpose='inventory').count()
    if n_new < n_old:
        raise RuntimeError(f"InventoryEvent copy incomplete: {n_old} rows, {n_new} in Log")
    print(f"\n  Inventory events copied to Log: {len(rows)}")


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0031_lesson'),
        ('ai_assistant', '0012_delete_alicecoachinglog'),
    ]

    operations = [
        migrations.RunPython(copy_inventory_events, migrations.RunPython.noop),
    ]
