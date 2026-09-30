"""The layer and movement source fields go, after 0020 carried them into parent_model/parent_id.

A separate migration: Postgres refuses to drop a column in the transaction that just updated its
rows (pending trigger events).
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0021_layer_parent_carried'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='inventorylayer',
            name='source',
        ),
        migrations.RemoveField(
            model_name='inventorylayer',
            name='source_doc_id',
        ),
        migrations.RemoveField(
            model_name='inventorylayer',
            name='source_doc_type',
        ),
        migrations.RemoveField(
            model_name='inventorymovement',
            name='source_doc_id',
        ),
        migrations.RemoveField(
            model_name='inventorymovement',
            name='source_doc_type',
        ),
    ]
