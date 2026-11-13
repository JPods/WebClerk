"""The purchase form's header loses its ``bill_to`` column (Bill, 2026-11-12: "Remove the
bill_to in the purchase form. If it needs to be changed users can make the change in the
addresses object"). The block itself stays on the document, still filled from the company
profile at birth (party_fill.take_company_blocks); only the form column goes. The header is
then three columns: vendor, ship_to, purchase.

So that the change can be made there, the form's json panel lists ``addresses``, ``emails`` and
``phones`` (it listed config, totals, cost, tax, metadata, refs, prefs — not the party objects).
"""
from django.db import migrations

GONE = 'bill_to'
PARTY_OBJECTS = ('addresses', 'emails', 'phones')


def without_column(layout):
    """The layout with the form header's column titled ``bill_to`` removed and the party
    objects listed in the json panel, in every form."""
    if not isinstance(layout, dict) or not isinstance(layout.get('form'), dict):
        return layout
    forms = {}
    for name, form in layout['form'].items():
        if isinstance(form, dict) and isinstance(form.get('sections'), list):
            sections = [
                {**s, 'columns': [c for c in s['columns']
                                  if not (isinstance(c, dict) and c.get('title') == GONE)]}
                if isinstance(s, dict) and s.get('type') == 'header' and isinstance(s.get('columns'), list) else s
                for s in form['sections']]
            sections = [
                {**s, 'fields': [f for f in PARTY_OBJECTS if f not in s['fields']] + list(s['fields'])}
                if isinstance(s, dict) and s.get('type') == 'json_tree' and isinstance(s.get('fields'), list) else s
                for s in sections]
            form = {**form, 'sections': sections}
        forms[name] = form
    return {**layout, 'form': forms}


def forward(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    for s in Setting.objects.filter(purpose='wc:model', parent_model__iexact='purchase'):
        if isinstance(s.config, dict) and 'layout' in s.config:
            layout = without_column(s.config['layout'])
            if layout != s.config['layout']:
                Setting.objects.filter(pk=s.pk).update(config={**s.config, 'layout': layout})


class Migration(migrations.Migration):
    dependencies = [('transactions', '0060_line_contacts_switch')]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
