"""A purchase names its vendor in a ``vendor`` block; its bill-to and ship-to are the company's
own (Bill, 2026-11-12: "change bill_to name to vendor and show the vendor and address").

Until now the vendor's company and address sat in the purchase's ``bill_to`` block. Three moves,
each a no-op where it is already done:

1. Every purchase: ``addresses/emails/phones.bill_to`` -> ``.vendor`` (the bill-to is left blank;
   the next save takes the company's own).
2. The stored purchase layout: the vendor's column is titled ``vendor`` and reads ``*.vendor.*``;
   a ``bill_to`` column follows it.
3. The company profile: ``company.address_receiving`` becomes ``company.addresses.ship_to`` —
   the shape every org carries. No second spelling is kept.
"""
from django.db import migrations

ASPECTS = ('addresses', 'emails', 'phones')
BILL_TO = {'title': 'bill_to', 'fields': [
    {'field': 'addresses.bill_to.company', 'label': 'company'},
    {'field': 'addresses.bill_to.attention', 'label': 'attention'},
    {'field': 'addresses.bill_to.full_address', 'label': 'address'},
    {'field': 'phones.bill_to.number', 'label': 'phone'},
    {'field': 'emails.bill_to.email', 'label': 'email'}]}


def vendor_columns(columns):
    """The header's columns with the vendor's column named for what it holds, and a bill-to
    column after it. Returns the same list object when there is nothing to change."""
    if not isinstance(columns, list) or any(isinstance(c, dict) and c.get('title') == 'vendor' for c in columns):
        return columns
    out = []
    for col in columns:
        if isinstance(col, dict) and col.get('title') == 'bill_to' and col.get('title_ida'):
            fields = [{**f, 'field': f['field'].replace('.bill_to.', '.vendor.')}
                      if isinstance(f, dict) and isinstance(f.get('field'), str) else f
                      for f in col.get('fields') or []]
            out += [{**col, 'title': 'vendor', 'fields': fields}, {**BILL_TO, 'fields': [dict(f) for f in BILL_TO['fields']]}]
        else:
            out.append(col)
    return out if len(out) != len(columns) else columns


def vendor_layout(layout):
    """A purchase layout with ``vendor_columns`` applied to every form's header sections."""
    if not isinstance(layout, dict) or not isinstance(layout.get('form'), dict):
        return layout
    forms = {}
    for name, form in layout['form'].items():
        if isinstance(form, dict) and isinstance(form.get('sections'), list):
            form = {**form, 'sections': [
                {**s, 'columns': vendor_columns(s['columns'])} if isinstance(s, dict) and 'columns' in s else s
                for s in form['sections']]}
        forms[name] = form
    return {**layout, 'form': forms}


def vendor_block(doc):
    """{aspect: value} for a purchase whose bill_to holds the vendor and that has no vendor block."""
    addresses = doc.addresses if isinstance(doc.addresses, dict) else {}
    held = addresses.get('bill_to') or {}
    if addresses.get('vendor') or not (held.get('company') or held.get('full_address')):
        return {}
    out = {}
    for aspect in ASPECTS:
        value = getattr(doc, aspect, None)
        if isinstance(value, dict) and 'bill_to' in value:
            value = dict(value)
            value['vendor'] = value.pop('bill_to')
            out[aspect] = value
    return out


def company_ship_to(config):
    """The company profile's config with ``address_receiving`` moved into ``addresses.ship_to``."""
    company = config.get('company') if isinstance(config, dict) else None
    if not isinstance(company, dict) or 'address_receiving' not in company:
        return config
    company = dict(company)
    receiving = (company.pop('address_receiving') or '').strip()
    addresses = dict(company.get('addresses') or {})
    if receiving and not (addresses.get('ship_to') or {}).get('full_address'):
        addresses['ship_to'] = {'contact_id': None, 'company': company.get('name') or company.get('legal_name') or '',
                                'attention': '', 'full_address': receiving, 'instructions': ''}
        company['addresses'] = addresses
    return {**config, 'company': company}


def forward(apps, schema_editor):
    Purchase = apps.get_model('transactions', 'Purchase')
    Setting = apps.get_model('core', 'Setting')
    for doc in Purchase.objects.only('id', *ASPECTS).iterator():
        moved = vendor_block(doc)
        if moved:
            Purchase.objects.filter(pk=doc.pk).update(**moved)
    for s in Setting.objects.filter(purpose='wc:model', parent_model__iexact='purchase'):
        if isinstance(s.config, dict) and 'layout' in s.config:
            layout = vendor_layout(s.config['layout'])
            if layout != s.config['layout']:
                Setting.objects.filter(pk=s.pk).update(config={**s.config, 'layout': layout})
    for s in Setting.objects.filter(purpose='wc:company_profile'):
        config = company_ship_to(s.config)
        if config != s.config:
            Setting.objects.filter(pk=s.pk).update(config=config)
    # The profile is cached for operational saves and an update() fires no signal.
    from apps.core.services.cache import cache_service
    from apps.core.services.company_profile import COMPANY_CACHE
    cache_service.invalidate_namespace(COMPANY_CACHE)


class Migration(migrations.Migration):
    dependencies = [('transactions', '0053_price_level_words'), ('core', '0073_org_access_leaves_for_defaults_and_source')]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
