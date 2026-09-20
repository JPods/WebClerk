"""Rebuild item commitment buckets from the documents that commit them.

The buckets on_qt / on_so / on_po / on_wo are echoes: each one is Σ remaining of the
live lines on open documents of that type. When they disagree with the documents —
imported data that never went through the pending path, a movement written in a shape
nothing dispatched, an edit that predates a fix — the documents are right and the bucket
is wrong. Reconcile, never clamp (Axiom 6).

on_hand and allocated are NOT touched: on_hand is what is on the shelf, and allocated is
a person's decision. Neither can be derived from documents.

    manage.py rebuild_commitment_buckets              # dry run, shows the gaps
    manage.py rebuild_commitment_buckets --apply
    manage.py rebuild_commitment_buckets --item 612 --apply
"""
from collections import defaultdict

from django.apps import apps as dj_apps
from django.core.management.base import BaseCommand

#: document type -> the bucket it commits
SPEC = (('quote', 'on_qt'), ('order', 'on_so'), ('purchase', 'on_po'), ('workorder', 'on_wo'))
CLOSED = ('complete', 'canceled')
BUCKETS = tuple(bucket for _model, bucket in SPEC)


def wanted_by_item(item_id=None):
    """Σ remaining of live lines on open documents, per item per bucket.

    on_qt is a weighted forecast, not a raw sum: the increment path multiplies a quote
    line by its header's close probability (base_line_model.forecast_probability), so a
    rebuild that summed raw remaining would fight it. Same function, same weight.
    """
    from apps.transactions.models.base_line_model import forecast_probability

    want = defaultdict(lambda: dict.fromkeys(BUCKETS, 0.0))
    for model_name, bucket in SPEC:
        Model = dj_apps.get_model('transactions', model_name)
        headers = Model.objects.filter(is_deleted=False).exclude(status__in=CLOSED)
        for header in headers:
            weight = forecast_probability(header) if model_name == 'quote' else 1.0
            for line in header.lines.filter(is_deleted=False).only('quantity', 'item'):
                item = line.item if isinstance(line.item, dict) else {}
                raw = item.get('item_id') or item.get('id_num')
                if not raw:
                    continue
                pk = int(raw)
                if item_id and pk != int(item_id):
                    continue
                quantity = line.quantity if isinstance(line.quantity, dict) else {}
                want[pk][bucket] += float(quantity.get('remaining') or 0) * weight
    return want


def commitment_gaps(item_id=None) -> list[dict]:
    """Where the buckets disagree with the documents — the reconciliation, as data.

    The same function the command uses, so the report and the repair can never drift.
    Alice raises this; a person runs the repair.
    """
    Item = dj_apps.get_model('products', 'Item')
    want = wanted_by_item(item_id)
    items = Item.objects.filter(is_deleted=False)
    if item_id:
        items = items.filter(pk=item_id)

    out = []
    for item in items.only('id', 'ida', 'name', 'quantity'):
        quantity = item.quantity or {}
        expect = want.get(item.pk) or dict.fromkeys(BUCKETS, 0.0)
        for bucket in BUCKETS:
            have = float(quantity.get(bucket) or 0)
            target = round(expect[bucket], 4)
            if abs(have - target) > 0.0001:
                out.append({'item_id': item.pk, 'ida': item.ida or item.name,
                            'bucket': bucket, 'have': have, 'expect': target,
                            'gap': round(have - target, 4)})
    return sorted(out, key=lambda r: -abs(r['gap']))


class Command(BaseCommand):
    help = "Rebuild on_qt / on_so / on_po / on_wo from open documents."

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='write the corrected buckets')
        parser.add_argument('--item', type=int, help='one item only')

    def handle(self, *args, **options):
        Item = dj_apps.get_model('products', 'Item')
        apply_changes = options['apply']
        want = wanted_by_item(options.get('item'))

        items = Item.objects.filter(is_deleted=False)
        if options.get('item'):
            items = items.filter(pk=options['item'])

        changed = 0
        gaps = []
        for item in items.only('id', 'ida', 'name', 'quantity'):
            quantity = dict(item.quantity or {})
            expect = want.get(item.pk) or dict.fromkeys(BUCKETS, 0.0)
            deltas = {}
            for bucket in BUCKETS:
                have = float(quantity.get(bucket) or 0)
                target = round(expect[bucket], 4)
                if abs(have - target) > 0.0001:
                    deltas[bucket] = (have, target)
                    quantity[bucket] = target
            if not deltas:
                continue
            changed += 1
            gaps.append((item.pk, item.ida or item.name, deltas))
            if apply_changes:
                allocated = float(quantity.get('allocated') or 0)
                quantity['available'] = float(quantity.get('on_hand') or 0) - allocated
                Item.objects.filter(pk=item.pk).update(quantity=quantity)

        for pk, label, deltas in sorted(gaps, key=lambda g: -max(abs(h - t) for h, t in g[2].values()))[:20]:
            detail = ', '.join(f"{b} {h:g} -> {t:g}" for b, (h, t) in deltas.items())
            self.stdout.write(f"  item {pk:>5} {str(label)[:24]:<24} {detail}")

        verb = 'Rebuilt' if apply_changes else 'Would rebuild'
        self.stdout.write(self.style.SUCCESS(
            f"{verb} commitment buckets on {changed} item(s). on_hand and allocated untouched."))
        if not apply_changes and changed:
            self.stdout.write("Dry run — pass --apply to write.")
