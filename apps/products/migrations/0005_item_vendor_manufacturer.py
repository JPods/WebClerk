"""Add vendor and manufacturer ForeignKey fields to Item.

Links Item to OrgBase for vendor and manufacturer tracking.
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0004_pending_inventory_inherit_coremodel'),
        ('orgs', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='item',
            name='vendor',
            field=models.ForeignKey(
                blank=True, null=True,
                db_column='vendor_id',
                db_index=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='items_as_vendor',
                to='orgs.orgbase',
            ),
        ),
        migrations.AddField(
            model_name='item',
            name='manufacturer',
            field=models.ForeignKey(
                blank=True, null=True,
                db_column='manufacturer_id',
                db_index=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='items_as_manufacturer',
                to='orgs.orgbase',
            ),
        ),
    ]
