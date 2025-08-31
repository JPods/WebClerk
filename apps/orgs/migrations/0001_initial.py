"""Fresh initial migration for orgs app (pruned history).

NOTE: Replace prior historical chain (0001_initial ... 0006_squashed_connections).
Before using on a brand new database, delete old migration files so only this
remains as 0001_initial.py (rename this file accordingly) then run:
  python manage.py migrate orgs

If you already have a database with the old chain applied, do NOT apply this
over it without resetting the DB; it defines the same final schema but would
conflict with existing migration records.
"""

from django.db import migrations, models
from django.contrib.postgres.indexes import GinIndex
import uuid
import apps.orgs.models.base_org_model as base
import common.models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='OrgBase',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('ida', models.CharField(blank=True, db_index=True, max_length=40)),
                ('created_dt', models.BigIntegerField(db_index=True, default=0)),
                ('modified_dt', models.BigIntegerField(db_index=True, default=0)),
                ('version', models.PositiveIntegerField(default=1)),
                ('is_deleted', models.BooleanField(db_index=True, default=False)),
                ('is_archived', models.BooleanField(db_index=True, default=False)),
                ('metadata', models.JSONField(default=common.models.default_metadata, help_text='Universal metadata envelope')),
                ('refs', models.JSONField(default=common.models.default_refs, help_text='Keywords / tags / lightweight links')),
                ('prefs', models.JSONField(default=common.models.default_prefs, help_text='User preferences / settings')),
                ('comments', models.JSONField(default=common.models.default_comments, help_text='Threaded notes / comment fields')),
                ('health_rating', models.IntegerField(default=0, help_text='Data quality rating (0-100)')),
                ('org_type', models.CharField(choices=[('customer', 'Customer'), ('vendor', 'Vendor'), ('rep', 'Rep'), ('employee', 'Employee'), ('manufacturer', 'Manufacturer'), ('other', 'Other')], db_index=True, max_length=20)),
                ('display_name', models.CharField(db_index=True, max_length=255)),
                ('status', models.CharField(blank=True, db_index=True, max_length=30)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('contacts', models.JSONField(default=base.default_contacts)),
                ('locations', models.JSONField(default=base.default_locations)),
                ('domains', models.JSONField(default=base.default_domains)),
                ('phones', models.JSONField(default=base.default_phones)),
                ('emails', models.JSONField(default=base.default_emails)),
                ('docs', models.JSONField(default=base.default_docs)),
                ('connections', models.JSONField(default=base.default_connections)),
                ('relations', models.JSONField(default=base.default_relations)),
                ('financial', models.JSONField(default=base.default_financial)),
                ('data', models.JSONField(default=base.default_data)),
                ('metrics', models.JSONField(default=base.default_metrics)),
                ('gl_accounts', models.JSONField(default=base.default_gl_accounts)),
            ],
            options={
                'verbose_name': 'Organization',
                'verbose_name_plural': 'Organizations',
                'indexes': [
                    GinIndex(fields=['contacts'], name='org_contacts_gin'),
                    GinIndex(fields=['relations'], name='org_rel_gin'),
                    GinIndex(fields=['financial'], name='org_financial_gin'),
                    GinIndex(fields=['domains'], name='org_domains_gin'),
                ],
                'constraints': [
                    models.CheckConstraint(check=~models.Q(display_name=""), name='org_display_name_not_empty'),
                ],
            },
        ),
        migrations.CreateModel(
            name='CustomerOrg',
            fields=[],
            options={'verbose_name': 'Customer', 'verbose_name_plural': 'Customers', 'proxy': True},
            bases=('orgs.orgbase',),
        ),
        migrations.CreateModel(
            name='EmployeeOrg',
            fields=[],
            options={'verbose_name': 'Employee', 'verbose_name_plural': 'Employees', 'proxy': True},
            bases=('orgs.orgbase',),
        ),
        migrations.CreateModel(
            name='ManufacturerOrg',
            fields=[],
            options={'verbose_name': 'Manufacturer', 'verbose_name_plural': 'Manufacturers', 'proxy': True},
            bases=('orgs.orgbase',),
        ),
        migrations.CreateModel(
            name='RepOrg',
            fields=[],
            options={'verbose_name': 'Rep', 'verbose_name_plural': 'Reps', 'proxy': True},
            bases=('orgs.orgbase',),
        ),
        migrations.CreateModel(
            name='VendorOrg',
            fields=[],
            options={'verbose_name': 'Vendor', 'verbose_name_plural': 'Vendors', 'proxy': True},
            bases=('orgs.orgbase',),
        ),
    ]
