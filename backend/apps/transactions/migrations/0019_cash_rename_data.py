# Stored values follow the payment → cash rename (Bill, 2026-09-16).
#
# Keys and identifier-like values use the same rules as the code rename:
#   payment → cash, payments → cash_entries (identifiers) / Cash (labels),
#   payment_term(s)/paymentterm → term(s), paymentmethod → cash_method, dt_payment → dt_cash.
# Kept: outside-service vocabulary (payment_intent, payment_method_token) and
# accounting words (overpayment, prepayment, down/late/partial payment).
# Prose longer than a label is left to the documentation review.

import re

from django.db import migrations

PROTECT = [
    'payment_method_token', 'paymentMethodToken', 'gateway_payment_intent_id',
    'id_gateway_payment_intent', 'payment_intent', 'paymentIntent',
    'overpayment', 'Overpayment', 'prepayment', 'Prepayment', 'DownPayment', 'down_payment',
    'Down Payment', 'down payment', 'late_payment', 'LatePayment', 'late payment', 'Late Payment',
    'partial_payment', 'partial payment', 'Partial Payment',
]
PROTECT.sort(key=len, reverse=True)

RULES = [(re.compile(p), r) for p, r in [
    (r'payment_terms\b', 'terms'), (r'payment_term_id\b', 'term_id'), (r'paymentterm_id\b', 'term_id'),
    (r'payment_term\b', 'term'), (r'paymentterm\b', 'term'), (r'PaymentTerm\b', 'Term'),
    (r'paymentmethod_id\b', 'cash_method_id'), (r'paymentmethod\b', 'cash_method'),
    (r'3Payments30Days', '3Pay30Days'),
    (r'ApplyPayments', 'ApplyCash'), (r'apply-payments', 'apply-cash'), (r'apply_payments', 'apply_cash'),
    (r'applypayments', 'applycash'),
    (r'(?<=/)payments(?=/|\b)', 'cash'),
    (r'PAYMENTS', 'CASH_ENTRIES'),
    (r'(?<=[a-z0-9])Payments', 'CashEntries'),
    (r'(?<![A-Za-z0-9_])Payments(?=[A-Z_])', 'CashEntries'),
    (r'(?<![A-Za-z0-9])Payments(?![A-Za-z0-9_])', 'Cash'),
    (r'payments', 'cash_entries'),
    (r'PAYMENT', 'CASH'), (r'Payment', 'Cash'), (r'payment', 'cash'),
]]
LABEL_RULES = [(re.compile(p), r) for p, r in [
    (r'(?<![A-Za-z0-9_])Payments(?![A-Za-z0-9_])', 'Cash'),
    (r'(?<![A-Za-z0-9_])payments(?![A-Za-z0-9_])', 'cash'),
]]


def _rename(text, label=False):
    if not isinstance(text, str) or not re.search('payment', text, re.I):
        return text
    slots = {}
    for i, tok in enumerate(PROTECT):
        if tok in text:
            key = f'\x00{i}\x00'
            text = text.replace(tok, key)
            slots[key] = tok
    for rx, rep in (LABEL_RULES if label else []) + RULES:
        text = rx.sub(rep, text)
    for key, tok in slots.items():
        text = text.replace(key, tok)
    return text


def _is_label(value):
    return ' ' in value.strip()


def _value(value):
    """Identifier-like strings and short labels change; prose does not."""
    if not isinstance(value, str) or '\n' in value or len(value) > 80:
        return value
    return _rename(value, label=_is_label(value))


def _walk(node):
    if isinstance(node, dict):
        return {_rename(k, label=_is_label(k)): _walk(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_walk(v) for v in node]
    return _value(node)


TARGETS = {
    'settings': ['ida', 'purpose', 'parent_model', 'name', 'config', 'refs', 'paths'],
    'reports': ['ida', 'name', 'model_name', 'config', 'refs', 'paths', 'metadata'],
    'workspace': ['ida', 'name', 'component', 'route', 'config', 'refs'],
    'core_modelroleconfig': ['model_name', 'refs'],
    'ledger': ['model_name', 'refs'],
    'pending': ['model_name', 'purpose', 'name', 'changes'],
    'gl_journals': ['source_model', 'refs'],
    'transactions_cash': ['ida', 'metadata', 'prefs'],
    'orgs_orgbase': ['financial', 'refs'],
    'invoices': ['refs'],
    'contacts': ['metadata'],
    'terms': ['refs'],
    'touches': ['refs'],
}


def forward(apps, schema_editor):
    import json
    conn = schema_editor.connection
    with conn.cursor() as cur:
        for table, columns in TARGETS.items():
            cur.execute(
                "select column_name, data_type from information_schema.columns "
                "where table_schema = current_schema() and table_name = %s", [table])
            types = dict(cur.fetchall())
            for col in columns:
                if col not in types:
                    continue
                cur.execute(f'select id, "{col}" from "{table}" where "{col}"::text ~* %s', ['payment'])
                for pk, val in cur.fetchall():
                    if types[col] in ('jsonb', 'json'):
                        if isinstance(val, str):
                            val = json.loads(val)
                        new = _walk(val)
                        if new != val:
                            cur.execute(f'update "{table}" set "{col}" = %s where id = %s', [json.dumps(new), pk])
                    else:
                        new = _value(val)
                        if new != val:
                            cur.execute(f'update "{table}" set "{col}" = %s where id = %s', [new, pk])
        # Navigation history pointing at deleted application models
        cur.execute(
            "update contacts set metadata = jsonb_set(metadata, '{navigation_log}', "
            "coalesce((select jsonb_agg(e) from jsonb_array_elements(metadata->'navigation_log') e "
            "where e->>'model' <> 'pending_cash_application'), '[]'::jsonb)) "
            "where metadata->'navigation_log' @> '[{\"model\": \"pending_cash_application\"}]'")


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0018_cash_rename'),
        ('core', '0006_cash_rename'),
        ('accounts', '0010_cash_rename'),
        ('sync', '0004_cash_rename'),
    ]

    operations = [
        migrations.RunPython(forward, migrations.RunPython.noop),
    ]
