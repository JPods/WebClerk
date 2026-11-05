"""Item.margin_pct is the item's own margin (readme 104 item 7, 2026-11-05).

Margin on list price at the company's cost basis, the formula price_resolver uses on a line,
set on save and unknown (null) without a price or a cost. It was 0.00 on every item: a nightly
velocity job that never ran, and a default of 0 that read as a figure. Existing items are
recomputed by `manage.py recompute_item_margin` (one formula, no live model in a migration);
a new install has no items, and from here on save sets it.
"""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('products', '0024_delete_seriallog')]
    operations = [
        migrations.AlterField(
            model_name='item', name='margin_pct',
            field=models.DecimalField(
                max_digits=8, decimal_places=2, null=True, blank=True,
                help_text="Margin on list price at the company's cost basis (price_resolver.resolve_cost), "
                          "set on save; unknown (null) without a price or a cost — never 0 for 'not computed'."),
        ),
    ]
