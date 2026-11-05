"""The lists code held, into the definitions that lacked them; terms is a lookup (readme 105).

Step (d) deleted field_behaviors' inline option tables. Four of them fed fields whose model
definition carried no list of its own, so those dropdowns went empty: ship_via on six
documents, source_name on contact / item_xref / receipt, price_level and priority on receipt.
They join those definitions here. Terms came from the Term records and now render as a lookup
on the term model (field_behaviors); a layout that forced terms to a plain select loses that type
so the behavior decides.
"""
from django.db import migrations

LISTS = {
    "ship_via": {
        "options": [
            {
                "value": "fedex",
                "label": "FedEx"
            },
            {
                "value": "ups",
                "label": "UPS"
            },
            {
                "value": "usps",
                "label": "USPS"
            },
            {
                "value": "dhl",
                "label": "DHL"
            },
            {
                "value": "freight",
                "label": "Freight"
            },
            {
                "value": "local",
                "label": "Local Delivery"
            },
            {
                "value": "will_call",
                "label": "Will Call"
            }
        ],
        "models": [
            "invoice",
            "order",
            "purchase",
            "quote",
            "receipt",
            "workorder"
        ]
    },
    "source_name": {
        "options": [
            {
                "value": "direct",
                "label": "Direct"
            },
            {
                "value": "referral",
                "label": "Referral"
            },
            {
                "value": "social_media",
                "label": "Social Media"
            },
            {
                "value": "website",
                "label": "Website"
            },
            {
                "value": "trade_show",
                "label": "Trade Show"
            },
            {
                "value": "cold_call",
                "label": "Cold Call"
            },
            {
                "value": "email_campaign",
                "label": "Email Campaign"
            },
            {
                "value": "repeat",
                "label": "Repeat Customer"
            },
            {
                "value": "partner",
                "label": "Partner"
            },
            {
                "value": "other",
                "label": "Other"
            }
        ],
        "models": [
            "contact",
            "item_xref",
            "receipt"
        ]
    },
    "price_level": {
        "options": [
            {
                "value": "retail",
                "label": "retail"
            },
            {
                "value": "wholesale",
                "label": "wholesale"
            },
            {
                "value": "distributor",
                "label": "distributor"
            },
            {
                "value": "sample",
                "label": "sample"
            }
        ],
        "models": [
            "receipt"
        ]
    },
    "priority": {
        "options": [
            {
                "value": "low",
                "label": "Low"
            },
            {
                "value": "normal",
                "label": "Normal"
            },
            {
                "value": "high",
                "label": "High"
            },
            {
                "value": "urgent",
                "label": "Urgent"
            }
        ],
        "models": [
            "receipt"
        ]
    }
}


def _add_lists(config, model):
    out = dict(config); lists = dict(out.get('selectlists') or {}); changed = False
    for field, spec in LISTS.items():
        if model in spec['models'] and not lists.get(field):
            lists[field] = [dict(o) for o in spec['options']]; changed = True
    if changed:
        out['selectlists'] = lists
    return out, changed


def _untype_terms(node):
    """Every layout field named terms loses an explicit select type and its inline options
    (a list of its own — cod, net10, net30 — that matched no Term ida; the lookup finds the
    Term records)."""
    if isinstance(node, dict):
        if node.get('field') == 'terms' and (node.get('type') == 'select' or 'options' in node):
            return {k: v for k, v in node.items() if k not in ('type', 'options')}
        return {k: _untype_terms(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_untype_terms(x) for x in node]
    return node


def forward(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    for s in Setting.objects.filter(purpose='wc:model').iterator():
        if not isinstance(s.config, dict):
            continue
        config, _ = _add_lists(s.config, s.parent_model)
        config = _untype_terms(config)
        if config != s.config:
            Setting.objects.filter(pk=s.pk).update(config=config)


class Migration(migrations.Migration):
    dependencies = [('core', '0056_card_paths_and_pending_form')]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
