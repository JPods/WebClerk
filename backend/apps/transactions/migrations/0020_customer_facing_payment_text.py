# Customers read "payment" (Bill, 2026-09-17). Record and field names stay cash;
# printed titles, receipt/statement text, and dunning messages say payment.

import json

from django.db import migrations

PHRASES = [
    ('CASH RECEIPT', 'PAYMENT RECEIPT'),
    ('Cash Receipt', 'Payment Receipt'),
    ('Cash Info', 'Payment Info'),
    ('Thank you for your cash.', 'Thank you for your payment.'),
    ('Recent Cash', 'Recent Payments'),
    ('CASH #', 'PAYMENT #'),
    ('Cash #', 'Payment #'),
    ('remit cash', 'remit payment'),
    ('arrange cash', 'arrange payment'),
    ('Immediate cash', 'Immediate payment'),
    ('prompt cash', 'prompt payment'),
    ('appreciate cash of', 'appreciate payment of'),
    ('Cash Terms', 'Terms'),
]


def _text(value):
    for old, new in PHRASES:
        value = value.replace(old, new)
    return value


def _walk(node):
    if isinstance(node, dict):
        return {k: _walk(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_walk(v) for v in node]
    if isinstance(node, str):
        return _text(node)
    return node


def forward(apps, schema_editor):
    pattern = '|'.join(old for old, _ in PHRASES).replace('#', '\\#')
    with schema_editor.connection.cursor() as cur:
        # config only: report and setting names stay internal (cash)
        for table in ('reports', 'settings'):
            cur.execute(f'select id, config from "{table}" where config::text ~ %s', [pattern])
            for pk, config in cur.fetchall():
                config = json.loads(config) if isinstance(config, str) else config
                new = _walk(config)
                if new != config:
                    cur.execute(f'update "{table}" set config = %s where id = %s', [json.dumps(new), pk])


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0019_cash_rename_data'),
    ]

    operations = [
        migrations.RunPython(forward, migrations.RunPython.noop),
    ]
