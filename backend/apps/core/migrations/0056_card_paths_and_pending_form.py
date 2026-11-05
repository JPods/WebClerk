"""Two wrong figures on screen (readme 105 step 1, 2026-11-05).

1. The dashboard cards (wc:dd_card Setting) named 'total', 'cost', 'balance' and 'margin_pct';
   a transaction carries them at totals.total, totals.cost, totals.balance, totals.margin_pc, so
   every card said $0.00 (FAULT 20261103T221823). The server computes the card now
   (dashboard/dd_card_metrics) and the config names the record's paths.
2. The pending form named changes.doc_id, changes.line_id and changes.reason, keys no pending
   carries, so the fields showed empty for everyone; the form shows changes as one JSON field.
"""
from django.db import migrations

PATHS = {'total': 'totals.total', 'cost': 'totals.cost', 'balance': 'totals.balance', 'margin_pct': 'totals.margin_pc'}


def _cards(config):
    cards = dict(config.get('cards') or {})
    for key, card in cards.items():
        if not isinstance(card, dict):
            continue
        card = dict(card)
        card['metrics'] = [
            {**m, **({'field': PATHS[m['field']]} if m.get('field') in PATHS else {}),
             **({'fields': [PATHS.get(f, f) for f in m['fields']]} if isinstance(m.get('fields'), list) else {})}
            for m in (card.get('metrics') or [])]
        dist = card.get('distribution')
        if isinstance(dist, dict) and dist.get('field') in PATHS:
            card['distribution'] = {**dist, 'field': PATHS[dist['field']]}
        cards[key] = card
    return {**config, 'cards': cards}


def _pending_form(node):
    if isinstance(node, dict):
        out = {}
        for k, v in node.items():
            if k == 'fields' and isinstance(v, list) and any(
                    isinstance(f, dict) and str(f.get('field', '')).startswith('changes.') for f in v):
                fields, done = [], False
                for f in v:
                    if isinstance(f, dict) and str(f.get('field', '')).startswith('changes.'):
                        if not done:
                            fields.append({'type': 'json_tree', 'field': 'changes', 'label': 'changes'})
                            done = True
                        continue
                    fields.append(f)
                out[k] = fields
            else:
                out[k] = _pending_form(v)
        return out
    if isinstance(node, list):
        return [_pending_form(x) for x in node]
    return node


def forward(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    for s in Setting.objects.filter(purpose='wc:dd_card'):
        if isinstance(s.config, dict):
            Setting.objects.filter(pk=s.pk).update(config=_cards(s.config))
    for s in Setting.objects.filter(purpose='wc:model', parent_model='pending'):
        if isinstance(s.config, dict):
            Setting.objects.filter(pk=s.pk).update(config=_pending_form(s.config))


class Migration(migrations.Migration):
    dependencies = [('core', '0055_layout_status_options')]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
