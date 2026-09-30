"""Carry each layer's and movement's source into parent_model/parent_id (see 0020). Its own
migration: Postgres will not create 0020's indexes or drop 0022's columns in a transaction that
has just updated the rows.
"""
from django.db import migrations


LINE_MODELS = ('receiptline', 'invoiceline', 'workorderline', 'orderline', 'purchaseline')


def carry_parent(apps, schema_editor):
    for name in ('InventoryLayer', 'InventoryMovement'):
        Model = apps.get_model('products', name)
        for model_key in LINE_MODELS:
            Model.objects.filter(source_doc_type=model_key).update(parent_model=model_key)
            for pk, doc_id in (Model.objects.filter(source_doc_type=model_key)
                               .values_list('pk', 'source_doc_id')):
                Model.objects.filter(pk=pk).update(parent_id=doc_id)



class Migration(migrations.Migration):

    dependencies = [
        ('products', '0020_layer_parent_pair'),
    ]

    operations = [
        migrations.RunPython(carry_parent, migrations.RunPython.noop),
    ]
