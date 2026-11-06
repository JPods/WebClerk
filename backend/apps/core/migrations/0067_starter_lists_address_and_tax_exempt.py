"""Starter lists where a form took free text (Bill, 2026-11-05: "the vast majority of user
input fields should have a selectlist"): an address's type, state and country, an org's
tax_exempt_code. Best-guess baselines a staff member edits (select_lists.add_value); a
definition that already holds the list keeps its own.
"""
from django.db import migrations

STATES = [
    ('AL', 'Alabama'), ('AK', 'Alaska'), ('AZ', 'Arizona'), ('AR', 'Arkansas'), ('CA', 'California'),
    ('CO', 'Colorado'), ('CT', 'Connecticut'), ('DE', 'Delaware'), ('DC', 'District of Columbia'),
    ('FL', 'Florida'), ('GA', 'Georgia'), ('HI', 'Hawaii'), ('ID', 'Idaho'), ('IL', 'Illinois'),
    ('IN', 'Indiana'), ('IA', 'Iowa'), ('KS', 'Kansas'), ('KY', 'Kentucky'), ('LA', 'Louisiana'),
    ('ME', 'Maine'), ('MD', 'Maryland'), ('MA', 'Massachusetts'), ('MI', 'Michigan'), ('MN', 'Minnesota'),
    ('MS', 'Mississippi'), ('MO', 'Missouri'), ('MT', 'Montana'), ('NE', 'Nebraska'), ('NV', 'Nevada'),
    ('NH', 'New Hampshire'), ('NJ', 'New Jersey'), ('NM', 'New Mexico'), ('NY', 'New York'),
    ('NC', 'North Carolina'), ('ND', 'North Dakota'), ('OH', 'Ohio'), ('OK', 'Oklahoma'), ('OR', 'Oregon'),
    ('PA', 'Pennsylvania'), ('RI', 'Rhode Island'), ('SC', 'South Carolina'), ('SD', 'South Dakota'),
    ('TN', 'Tennessee'), ('TX', 'Texas'), ('UT', 'Utah'), ('VT', 'Vermont'), ('VA', 'Virginia'),
    ('WA', 'Washington'), ('WV', 'West Virginia'), ('WI', 'Wisconsin'), ('WY', 'Wyoming'),
]
COUNTRIES = [('US', 'United States'), ('CA', 'Canada'), ('MX', 'Mexico'), ('GB', 'United Kingdom'),
             ('DE', 'Germany'), ('FR', 'France'), ('AU', 'Australia'), ('JP', 'Japan'), ('CN', 'China'),
             ('IN', 'India'), ('BR', 'Brazil')]
LISTS = {
    'address': {
        'address_type': [('billing', 'Billing'), ('shipping', 'Shipping'), ('home', 'Home'),
                         ('work', 'Work'), ('other', 'Other')],
        'state': STATES,
        'country': COUNTRIES,
    },
}
TAX_EXEMPT = [('', 'Taxable'), ('resale', 'Resale'), ('nonprofit', 'Nonprofit'), ('government', 'Government'),
              ('agricultural', 'Agricultural'), ('manufacturing', 'Manufacturing'), ('other', 'Other')]
for org in ('customer', 'vendor', 'manufacturer', 'rep', 'employee', 'other_org'):
    LISTS[org] = {'tax_exempt_code': TAX_EXEMPT}


def _options(pairs):
    return [{'value': v, 'label': l} for v, l in pairs if v != '']


def forward(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    for s in Setting.objects.filter(purpose='wc:model', parent_model__in=list(LISTS)):
        if not isinstance(s.config, dict):
            continue
        lists = dict(s.config.get('selectlists') or {})
        changed = False
        for field, pairs in LISTS[s.parent_model].items():
            if not lists.get(field):
                lists[field] = _options(pairs)
                changed = True
        if changed:
            Setting.objects.filter(pk=s.pk).update(config={**s.config, 'selectlists': lists})


class Migration(migrations.Migration):
    dependencies = [('core', '0066_select_typed_layout_field_has_a_list')]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
