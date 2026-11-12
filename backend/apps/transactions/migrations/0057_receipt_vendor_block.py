"""A receipt carries one party block, ``vendor`` — who the goods came from (readme 109; Bill,
2026-11-12: the receipt form's vendor column should read the receipt's own fields, not
``purchase.*``). It has no bill-to and no ship-to ("Receipt does not have a ship-to, correct").

1. Every receipt: ``bill_to`` (where a vendor pick used to write the vendor) becomes ``vendor``;
   an empty ``ship_to`` is dropped.
2. The stored receipt layout: the vendor column reads company.name and the vendor block.
3. The stored access sets and role lists: ``*.bill_to.*`` leaves become ``*.vendor.*``;
   ``*.ship_to.*`` leaves go.

Frozen: literals here, as common/schemas/aspects.DOCUMENT_PARTIES had them.
"""
from django.db import migrations

ASPECTS = ('addresses', 'emails', 'phones')
PATHS = {'purchase.company': 'company.name', 'purchase.attention': 'addresses.vendor.attention',
         'purchase.address_full': 'addresses.vendor.full_address', 'purchase.phone': 'phones.vendor.number',
         'purchase.email': 'emails.vendor.email'}
LABELS = {'company.name': 'company', 'addresses.vendor.attention': 'attention',
          'addresses.vendor.full_address': 'address', 'phones.vendor.number': 'phone',
          'emails.vendor.email': 'email'}


def moved_receipt(doc):
    """{aspect: value} to write on one receipt; {} when nothing changes."""
    out = {}
    for aspect in ASPECTS:
        value = getattr(doc, aspect, None)
        if not isinstance(value, dict) or not ({'bill_to', 'ship_to'} & set(value)):
            continue
        new = {k: v for k, v in value.items() if k not in ('bill_to', 'ship_to')}
        held = value.get('bill_to')
        if held and any(held.values()) and not new.get('vendor'):
            new['vendor'] = held
        if value.get('ship_to') and any(value['ship_to'].values()):
            new['ship_to'] = value['ship_to']            # someone typed one: kept, never dropped
        if new != value:
            out[aspect] = new
    return out


def moved_layout(node):
    if isinstance(node, list):
        return [moved_layout(item) for item in node]
    if isinstance(node, dict):
        if node.get('field') in PATHS:
            field = PATHS[node['field']]
            return {**node, 'field': field, 'label': LABELS[field]}
        return {k: moved_layout(v) for k, v in node.items()}
    return node


def _leaf(leaf):
    """A party-block leaf as the receipt names it now; None for one it no longer has."""
    parts = leaf.split('.') if isinstance(leaf, str) else []
    if len(parts) >= 3 and parts[0] in ASPECTS:
        if parts[1] == 'bill_to':
            return '.'.join([parts[0], 'vendor'] + parts[2:])
        if parts[1] == 'ship_to':
            return None
    return leaf


def _leaves(leaves):
    out = []
    for leaf in leaves:
        leaf = _leaf(leaf)
        if leaf is not None and leaf not in out:
            out.append(leaf)
    return out


def moved_definition(config):
    if not isinstance(config, dict):
        return config
    config = dict(config)
    if 'layout' in config:
        config['layout'] = moved_layout(config['layout'])
    access = config.get('access')
    if isinstance(access, dict):
        access = dict(access)
        if isinstance(access.get('sets'), dict):
            access['sets'] = {n: sorted(_leaves(v)) if isinstance(v, list) else v for n, v in access['sets'].items()}
        if isinstance(access.get('roles'), dict):
            access['roles'] = {n: ({k: (_leaves(v) if k in ('view', 'edit') and isinstance(v, list) else v)
                                    for k, v in b.items()} if isinstance(b, dict) else b)
                               for n, b in access['roles'].items()}
        config['access'] = access
    return config


def forward(apps, schema_editor):
    Receipt = apps.get_model('transactions', 'Receipt')
    Setting = apps.get_model('core', 'Setting')
    for doc in Receipt.objects.only('id', *ASPECTS).iterator():
        changed = moved_receipt(doc)
        if changed:
            Receipt.objects.filter(pk=doc.pk).update(**changed)
    for s in Setting.objects.filter(purpose='wc:model', parent_model__iexact='receipt'):
        config = moved_definition(s.config)
        if config != s.config:
            Setting.objects.filter(pk=s.pk).update(config=config)
    from apps.core.services.access import clear_cache
    clear_cache('receipt')


class Migration(migrations.Migration):
    dependencies = [('transactions', '0056_counterparty_details_in_the_party_block')]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
