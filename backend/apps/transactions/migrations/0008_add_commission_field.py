"""Add commission JSONField to all transaction headers and lines."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0007_payment_add_type_and_purchase'),
    ]

    operations = [
        # Headers
        migrations.AddField(model_name='order', name='commission', field=models.JSONField(default=dict, blank=True, null=True)),
        migrations.AddField(model_name='invoice', name='commission', field=models.JSONField(default=dict, blank=True, null=True)),
        migrations.AddField(model_name='proposal', name='commission', field=models.JSONField(default=dict, blank=True, null=True)),
        migrations.AddField(model_name='purchase', name='commission', field=models.JSONField(default=dict, blank=True, null=True)),
        migrations.AddField(model_name='workorder', name='commission', field=models.JSONField(default=dict, blank=True, null=True)),
        migrations.AddField(model_name='receipt', name='commission', field=models.JSONField(default=dict, blank=True, null=True)),
        # Lines
        migrations.AddField(model_name='orderline', name='commission', field=models.JSONField(default=dict, blank=True, null=True)),
        migrations.AddField(model_name='invoiceline', name='commission', field=models.JSONField(default=dict, blank=True, null=True)),
        migrations.AddField(model_name='proposalline', name='commission', field=models.JSONField(default=dict, blank=True, null=True)),
        migrations.AddField(model_name='purchaseline', name='commission', field=models.JSONField(default=dict, blank=True, null=True)),
        migrations.AddField(model_name='workorderline', name='commission', field=models.JSONField(default=dict, blank=True, null=True)),
        migrations.AddField(model_name='receiptline', name='commission', field=models.JSONField(default=dict, blank=True, null=True)),
    ]
