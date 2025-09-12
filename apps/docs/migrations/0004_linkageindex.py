from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('docs', '0002_alter_document_uuid_alter_linkage_uuid_alter_qa_uuid_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='LinkageIndex',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('table_name', models.CharField(db_index=True, max_length=255)),
                ('record_id', models.IntegerField(db_index=True)),
                ('linkage', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='index_entries', to='docs.linkage')),
            ],
            options={
                'db_table': 'linkage_index',
            },
        ),
        migrations.AddConstraint(
            model_name='linkageindex',
            constraint=models.UniqueConstraint(fields=('table_name', 'record_id'), name='uniq_linkage_index_pair'),
        ),
        migrations.AddIndex(
            model_name='linkageindex',
            index=models.Index(fields=['linkage'], name='linx_lkg_idx'),
        ),
        migrations.AddIndex(
            model_name='linkageindex',
            index=models.Index(fields=['table_name', 'linkage'], name='linx_tbl_lkg_idx'),
        ),
    ]
