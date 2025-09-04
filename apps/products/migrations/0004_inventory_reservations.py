from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0003_pending_inventory_adjustments'),
    ]

    operations = [
        migrations.CreateModel(
            name='InventoryReservation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('qty', models.DecimalField(decimal_places=4, max_digits=14)),
                ('state', models.CharField(choices=[('pending', 'Pending'), ('committed', 'Committed'), ('canceled', 'Canceled'), ('expired', 'Expired')], db_index=True, default='pending', max_length=20)),
                ('expires_at', models.DateTimeField(db_index=True)),
                ('committed_at', models.DateTimeField(blank=True, null=True)),
                ('released_at', models.DateTimeField(blank=True, null=True)),
                ('context', models.JSONField(blank=True, default=dict)),
                ('reason', models.CharField(blank=True, max_length=80)),
                ('created_dt', models.DateTimeField(auto_now_add=True)),
                ('modified_dt', models.DateTimeField(auto_now=True)),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reservations', to='products.item')),
                ('stack', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reservations', to='products.inventorystack')),
                ('warehouse', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='reservations', to='products.warehouse')),
            ],
            options={
                'indexes': [
                    models.Index(fields=('state', 'expires_at'), name='invres_state_exp_idx'),
                    models.Index(fields=('item', 'warehouse', 'state'), name='invres_item_wh_state_idx'),
                ],
            },
        ),
    ]
