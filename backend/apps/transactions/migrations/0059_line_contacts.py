"""Line contacts (readme 109 P6; Bill, 2026-11-12): the people a quote, order or invoice line
names, and the serial the line issued.

1. The contact definition gains the list of roles each installation edits,
   ``selectlists.transaction_role``, starting with the warranty holder.
2. The 'all' access sets learn the new leaves, so the door does not project them out on read
   (TFTS 2026-11-12): ``lines.refs.contacts.*`` on the three documents, ``refs.contacts.*`` on
   their line models and on serial.

Frozen: the leaves and the first role are literals here.
"""
from django.db import migrations

FIELDS = ('role', 'contact_id', 'display_name', 'company', 'email', 'phone')
ON_DOCUMENT = tuple(f'lines.refs.contacts.{f}' for f in FIELDS)
ON_RECORD = tuple(f'refs.contacts.{f}' for f in FIELDS)
LEAVES = {'quote': ON_DOCUMENT, 'order': ON_DOCUMENT, 'invoice': ON_DOCUMENT,
          'quote_line': ON_RECORD, 'order_line': ON_RECORD, 'invoice_line': ON_RECORD,
          'serial': ON_RECORD}
ROLE_FIELD = 'transaction_role'
FIRST_ROLES = [{'value': 'warranty_holder', 'label': 'Warranty Holder'}]


def grown(config, leaves):
    """The definition's config with its 'all' set grown; unchanged when it has no sets."""
    config = dict(config or {})
    access = config.get('access')
    if not isinstance(access, dict) or not isinstance(access.get('sets'), dict) \
            or not isinstance(access['sets'].get('all'), list):
        return config
    sets = dict(access['sets'])
    current = list(sets['all'])
    for leaf in leaves:
        if leaf not in current:
            current.append(leaf)
    sets['all'] = sorted(current)
    config['access'] = {**access, 'sets': sets}
    return config


def with_roles(config):
    """The contact definition's config with the role list, when it has none."""
    config = dict(config or {})
    lists = dict(config.get('selectlists') or {})
    if not lists.get(ROLE_FIELD):
        lists[ROLE_FIELD] = [dict(r) for r in FIRST_ROLES]
        config['selectlists'] = lists
    return config


def forward(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    for s in Setting.objects.filter(purpose='wc:model'):
        key = (s.parent_model or '').lower()
        if not isinstance(s.config, dict):
            continue
        config = s.config
        if key in LEAVES:
            config = grown(config, LEAVES[key])
        if key == 'contact':
            config = with_roles(config)
        if config != s.config:
            Setting.objects.filter(pk=s.pk).update(config=config)
    from apps.core.services.access import clear_cache
    from apps.core.services import definition
    for key in list(LEAVES) + ['contact']:
        clear_cache(key)
        definition.clear(key)


class Migration(migrations.Migration):
    dependencies = [('transactions', '0058_receipt_layout_drops_purchase_and_ship_to_fields')]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
