from django.db import migrations, models
import django.contrib.postgres.search
from django.contrib.postgres.indexes import GinIndex


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Document',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(editable=False, unique=True)),
                ('ida', models.CharField(blank=True, db_index=True, help_text='Alternate ID for external systems (indexed)', max_length=40)),
                ('created_dt', models.BigIntegerField(db_index=True, default=0, help_text='Denormalized created timestamp (ms UTC)')),
                ('modified_dt', models.BigIntegerField(db_index=True, default=0, help_text='Denormalized modified timestamp (ms UTC)')),
                ('is_deleted', models.BooleanField(db_index=True, default=False)),
                ('is_archived', models.BooleanField(db_index=True, default=False)),
                ('version', models.PositiveIntegerField(default=1, help_text='Incremented on each successful save')),
                ('metadata', models.JSONField(help_text='Universal API metadata structure')),
                ('refs', models.JSONField(help_text='References: keywords, tags, categories')),
                ('prefs', models.JSONField(help_text='User preferences and settings')),
                ('comments', models.JSONField(help_text='User comments and notes')),
                ('health_rating', models.IntegerField(default=0, help_text='Data quality rating (0-100)')),
                ('name', models.CharField(blank=True, db_index=True, max_length=255, null=True)),
                ('status', models.CharField(blank=True, db_index=True, max_length=255, null=True)),
                ('description', models.CharField(blank=True, max_length=255, null=True)),
                ('body', models.TextField(blank=True, null=True)),
                ('data', models.JSONField(blank=True, null=True)),
                ('comment', models.TextField(blank=True, null=True)),
                ('confidential', models.CharField(blank=True, max_length=255, null=True)),
                ('copyright', models.JSONField(blank=True, help_text='{level:int,path:str,holder:str,notes:[]} structure', null=True)),
                ('count_accessed', models.IntegerField(default=0)),
                ('table_name', models.CharField(blank=True, db_index=True, max_length=255, null=True)),
                ('retention_period', models.IntegerField(blank=True, null=True)),
                ('security_level', models.IntegerField(blank=True, db_index=True, null=True)),
                ('sequence', models.IntegerField(blank=True, null=True)),
                ('size_bytes', models.IntegerField(blank=True, null=True)),
                ('mime_type', models.CharField(blank=True, max_length=255, null=True)),
                ('path', models.JSONField(blank=True, null=True)),
                ('checksum', models.CharField(blank=True, max_length=255, null=True)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('search_vector', django.contrib.postgres.search.SearchVectorField(editable=False, null=True)),
            ],
            options={'db_table': 'documents'},
        ),
        migrations.AddIndex(
            model_name='document',
            index=models.Index(fields=['security_level'], name='doc_sec_level_idx'),
        ),
        migrations.AddIndex(
            model_name='document',
            index=models.Index(fields=['status'], name='doc_status_idx'),
        ),
        migrations.AddIndex(
            model_name='document',
            index=models.Index(fields=['name'], name='doc_name_idx'),
        ),
        migrations.AddIndex(
            model_name='document',
            index=models.Index(fields=['table_name'], name='doc_table_name_idx'),
        ),
        migrations.AddIndex(
            model_name='document',
            index=GinIndex(fields=['search_vector'], name='doc_search_gin'),
        ),
    ]
