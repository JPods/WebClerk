from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('products', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Variant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('canonical_key', models.CharField(db_index=True, max_length=255)),
                ('attrs', models.JSONField(blank=True, default=dict)),
                ('set_uuid', models.UUIDField(db_index=True)),
                ('variant_uuid', models.UUIDField(db_index=True, unique=True)),
                ('dt_created', models.BigIntegerField(db_index=True, default=0)),
                ('dt_modified', models.BigIntegerField(db_index=True, default=0)),
                ('item', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='variant_row', to='products.item')),
                ('parent_item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='variant_children', to='products.item')),
            ],
            options={
                'indexes': [
                    models.Index(fields=['parent_item'], name='variant_parent_idx'),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name='variant',
            constraint=models.UniqueConstraint(fields=('parent_item', 'canonical_key'), name='uniq_parent_key'),
        ),
    ]
