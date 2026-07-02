"""Add CoreModel fields to PendingInventoryAdjustment.

Switches PendingInventoryAdjustment from models.Model to CoreModel,
adding uuid, ida, dt_created, dt_modified, version, is_active, security_level.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0003_add_is_locked_to_lifecycle'),
    ]

    operations = [
        migrations.AddField(
            model_name='pendinginventoryadjustment',
            name='uuid',
            field=models.UUIDField(editable=False, unique=True, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='pendinginventoryadjustment',
            name='ida',
            field=models.CharField(max_length=40, blank=True, db_index=True, default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='pendinginventoryadjustment',
            name='dt_created',
            field=models.BigIntegerField(default=0, db_index=True),
        ),
        migrations.AddField(
            model_name='pendinginventoryadjustment',
            name='dt_modified',
            field=models.BigIntegerField(default=0, db_index=True),
        ),
        migrations.AddField(
            model_name='pendinginventoryadjustment',
            name='version',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='pendinginventoryadjustment',
            name='is_active',
            field=models.BooleanField(default=True, db_index=True, help_text='Record is logically active'),
        ),
        migrations.AddField(
            model_name='pendinginventoryadjustment',
            name='security_level',
            field=models.IntegerField(default=0, blank=True, db_index=True, help_text='Security level or classification'),
        ),
    ]
