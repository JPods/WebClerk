"""A document's ``company`` is who its counterparty is — identity only; their contact details
have one home, the party block (readme 109 P4; Bill, 2026-11-12: "Let's do 1 and 2").

Until now the vendor's or customer's attention, address, phone and email were kept three
times on a document — in ``company``, in the party block and in ``refs.links`` — and on the
pilot they already disagreed. Four moves, each a no-op where it is already done:

1. Every document whose counterparty block is blank takes it from the ``company`` snapshot
   (so no detail is lost), then ``company`` keeps id, ida, name, is_individual.
2. Stored layouts: ``company.email`` / ``company.phone`` read the block instead.
3. Stored access sets and role lists: a ``company.<detail>`` leaf becomes the block's leaf.
4. The definition caches are cleared.

Frozen: the roles are literals here, as common/schemas/aspects.DOCUMENT_PARTIES had them.
"""
from django.db import migrations

#: model key → (Django model name, its counterparty's block; None = no block takes them)
DOCUMENTS = {'quote': ('Quote', 'bill_to'), 'order': ('Order', 'bill_to'), 'invoice': ('Invoice', 'bill_to'),
             'workorder': ('WorkOrder', 'bill_to'), 'purchase': ('Purchase', 'vendor'), 'receipt': ('Receipt', None)}
IDENTITY = ('id', 'ida', 'name', 'is_individual')
#: company.<detail> → where it lives in the block; None = it has no home there
MOVED = {'attention': 'addresses.{role}.attention', 'full_address': 'addresses.{role}.full_address',
         'contact_id': 'addresses.{role}.contact_id', 'email': 'emails.{role}.email',
         'phone': 'phones.{role}.number', 'domain': None, 'custom': None}


def new_path(path, role):
    """Where a ``company.<detail>`` path lives now; the path itself when it is not one;
    None when the detail has no home (dropped)."""
    if not isinstance(path, str) or not path.startswith('company.'):
        return path
    key = path.split('.', 1)[1].split('.')[0]
    if key not in MOVED:
        return path
    target = MOVED[key]
    return target.format(role=role) if target and role else None


def moved_document(doc, role):
    """{field: value} to write on one document; {} when nothing changes."""
    company = doc.company if isinstance(doc.company, dict) else {}
    out = {}
    if role:
        addresses = dict(doc.addresses) if isinstance(doc.addresses, dict) else {}
        block = addresses.get(role) or {}
        if not (block.get('company') or block.get('full_address')) and \
                (company.get('full_address') or company.get('attention') or company.get('phone') or company.get('email')):
            addresses[role] = {'contact_id': company.get('contact_id'), 'company': company.get('name') or '',
                               'attention': company.get('attention') or '',
                               'full_address': company.get('full_address') or '', 'instructions': ''}
            out['addresses'] = addresses
            for aspect, key, source in (('emails', 'email', 'email'), ('phones', 'number', 'phone')):
                value = dict(getattr(doc, aspect)) if isinstance(getattr(doc, aspect), dict) else {}
                if not (value.get(role) or {}).get(key) and company.get(source):
                    value[role] = {**(value.get(role) or {}), key: company[source]}
                    out[aspect] = value
    identity = {k: company[k] for k in IDENTITY if k in company}
    if identity != company:
        out['company'] = identity
    return out


def moved_layout(node, role):
    """A layout with every ``field: company.<detail>`` reading the block; a column whose detail
    has no home is dropped."""
    if isinstance(node, list):
        out = []
        for item in node:
            if isinstance(item, dict) and isinstance(item.get('field'), str) and new_path(item['field'], role) is None:
                continue
            out.append(moved_layout(item, role))
        return out
    if isinstance(node, dict):
        return {k: (new_path(v, role) if k == 'field' else moved_layout(v, role)) for k, v in node.items()}
    return node


def _leaves(leaves, role):
    out = []
    for leaf in leaves:
        leaf = new_path(leaf, role)
        if leaf is not None and leaf not in out:
            out.append(leaf)
    return out


def moved_access(access, role):
    """An access block whose sets and role lists name the block's leaves, not company's."""
    if not isinstance(access, dict):
        return access
    access = dict(access)
    if isinstance(access.get('sets'), dict):
        access['sets'] = {name: sorted(_leaves(v, role)) if isinstance(v, list) else v
                          for name, v in access['sets'].items()}
    if isinstance(access.get('roles'), dict):
        roles = {}
        for name, block in access['roles'].items():
            if isinstance(block, dict):
                block = {k: (_leaves(v, role) if k in ('view', 'edit') and isinstance(v, list) else v)
                         for k, v in block.items()}
            roles[name] = block
        access['roles'] = roles
    return access


def moved_definition(config, role):
    """A wc:model Setting's config with its layout and access moved."""
    if not isinstance(config, dict):
        return config
    config = dict(config)
    if 'layout' in config:
        config['layout'] = moved_layout(config['layout'], role)
    if 'access' in config:
        config['access'] = moved_access(config['access'], role)
    return config


def forward(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    for key, (model_name, role) in DOCUMENTS.items():
        Model = apps.get_model('transactions', model_name)
        for doc in Model.objects.only('id', 'company', 'addresses', 'emails', 'phones').iterator():
            changed = moved_document(doc, role)
            if changed:
                Model.objects.filter(pk=doc.pk).update(**changed)
        for s in Setting.objects.filter(purpose='wc:model', parent_model__iexact=key):
            config = moved_definition(s.config, role)
            if config != s.config:
                Setting.objects.filter(pk=s.pk).update(config=config)
    from apps.core.services.access import clear_cache
    clear_cache()


class Migration(migrations.Migration):
    dependencies = [('transactions', '0055_purchase_vendor_access_leaves')]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
