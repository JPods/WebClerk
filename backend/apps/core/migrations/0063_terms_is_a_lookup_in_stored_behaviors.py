"""Terms is a lookup on the Term record in every stored definition (Bill, 2026-11-05: "terms
need to be a selectlist").

0057 made field_behaviors compute terms as a lookup on term by ida, which the seed writes into
a definition's config.behaviors — but no stored definition holds a terms behavior at all (the
definitions were seeded before the code named one and never re-seeded), so every form drew
terms as a plain text box: the form reads the stored behaviors, never the code. The same gap
0061 closed for contact_id. Every definition of a model that carries terms gets the lookup.
"""
from django.db import migrations

TERMS = {'type': 'lookup', 'model': 'term', 'display': 'ida', 'value': 'ida'}
#: The models with a terms column that have a definition (orgs, documents, ledger, cash).
MODELS = ('cash', 'customer', 'employee', 'invoice', 'ledger', 'manufacturer', 'order', 'other_org',
          'purchase', 'quote', 'receipt', 'rep', 'vendor', 'workorder')


def forward(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    for s in Setting.objects.filter(purpose='wc:model', parent_model__in=MODELS).iterator():
        if not isinstance(s.config, dict):
            continue
        behaviors = dict(s.config.get('behaviors') or {})
        want = {**{k: v for k, v in (behaviors.get('terms') or {}).items() if k in ('label', 'help')}, **TERMS}
        if behaviors.get('terms') != want:
            behaviors['terms'] = want
            Setting.objects.filter(pk=s.pk).update(config={**s.config, 'behaviors': behaviors})


class Migration(migrations.Migration):
    dependencies = [('core', '0062_company_default_order_new')]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
