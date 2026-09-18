# Backfill parent_line_id from refs.source and recompute remaining on parents.
# Split from 0021 so index creation commits before rows are updated.

from django.db import migrations

from decimal import Decimal, ROUND_HALF_UP


# Parent-child pairs only: proposal_line -> order_line, order_line -> invoice_line.
# readmes/transactions/line-quantity.md
PAIRS = (
    ('OrderLine', 'ProposalLine', 'proposal_line_id'),
    ('InvoiceLine', 'OrderLine', 'order_line_id'),
)


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def link_and_recompute(apps, schema_editor):
    for child_name, parent_name, key in PAIRS:
        Child = apps.get_model('transactions', child_name)
        Parent = apps.get_model('transactions', parent_name)
        parent_ids = set(Parent.objects.values_list('pk', flat=True))
        for child in Child.objects.all().only('pk', 'refs'):
            source = (child.refs or {}).get('source') if isinstance(child.refs, dict) else None
            raw = source.get(key) if isinstance(source, dict) else None
            try:
                pid = int(raw) if raw else None
            except (TypeError, ValueError):
                pid = None
            if pid in parent_ids:
                Child.objects.filter(pk=child.pk).update(parent_line_id=pid)

    for child_name, parent_name, _key in PAIRS:
        Child = apps.get_model('transactions', child_name)
        Parent = apps.get_model('transactions', parent_name)
        sums, counts = {}, {}
        for pid, q in Child.objects.exclude(parent_line_id=None).values_list('parent_line_id', 'quantity'):
            sums[pid] = sums.get(pid, 0.0) + _num((q or {}).get('active'))
            counts[pid] = counts.get(pid, 0) + 1
        for parent in Parent.objects.all().only('pk', 'quantity', 'status'):
            q = dict(parent.quantity) if isinstance(parent.quantity, dict) else {}
            precision = int(q.get('precision', 2) or 2)
            unconsumed = _num(q.get('active')) - sums.get(parent.pk, 0.0)
            remaining = float(Decimal(str(unconsumed)).quantize(Decimal(1).scaleb(-precision), rounding=ROUND_HALF_UP))
            q.pop('children_active', None)
            q['remaining'] = 0 if q.get('is_complete') else remaining
            status = parent.status
            if counts.get(parent.pk) and round(unconsumed, precision) == 0:
                status = 'transferred'
            elif status == 'transferred':
                status = ''
            Parent.objects.filter(pk=parent.pk).update(quantity=q, status=status)



class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0021_line_parent_line_id'),
    ]

    operations = [
        migrations.RunPython(link_and_recompute, migrations.RunPython.noop),
    ]
