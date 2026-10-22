"""Price levels are retail, wholesale, distributor and sample — only (Bill, 2026-10-22).

Orgs, transaction headers and lines that hold a letter (A–D) or a word in another case
are rewritten to the word. queryset.update(): a label change only — a door save of an
issued invoice could re-price or re-ledger it. After this, save refuses any other value
(save._price_level_is_named). Values that are neither are left and counted, not guessed.
"""
from django.db import migrations

LETTERS = {'A': 'retail', 'B': 'wholesale', 'C': 'distributor', 'D': 'sample'}
WORDS = tuple(LETTERS.values())


def _models(apps):
    for app_label in ('orgs', 'transactions'):
        for model in apps.get_app_config(app_label).get_models():
            if model._meta.proxy or 'price_level' not in {f.name for f in model._meta.concrete_fields}:
                continue
            yield model


def forwards(apps, schema_editor):
    for model in _models(apps):
        changed = 0
        for letter, word in LETTERS.items():
            changed += model.objects.filter(price_level__in=(letter, letter.lower())).update(price_level=word)
        for word in WORDS:
            changed += (model.objects.filter(price_level__iexact=word)
                        .exclude(price_level=word).update(price_level=word))
        left = (model.objects.exclude(price_level__in=WORDS).exclude(price_level='')
                .exclude(price_level__isnull=True).count())
        if changed or left:
            print(f'\n  price_level {model._meta.label}: {changed} rewritten'
                  + (f', {left} still outside the four words' if left else ''))


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0051_terms_text'),
        ('orgs', '0011_terms_text'),
    ]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
