"""A catalog line may name no item: a scope line covers all items, categories or vendors
(Bill, 2026-10-22). Rows already stored all name an item, so nothing is rewritten."""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0022_layer_source_fields_deleted'),
    ]

    operations = [
        migrations.AlterField(
            model_name='catalogline',
            name='item',
            field=models.ForeignKey(blank=True, db_column='item_id', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='catalogline_related', to='products.item'),
        ),
        migrations.AlterField(
            model_name='catalogline',
            name='scope',
            field=models.JSONField(blank=True, default=dict, help_text='What a line without an item covers: {all_items: false, categories: [], vendors: [vendor ids]}'),
        ),
    ]
