from django.db import migrations, models
import django.db.models.deletion
from django.db import connection


def rename_index_forward(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == 'postgresql':
        schema_editor.execute('ALTER INDEX IF EXISTS "acct_exrate_base_target_active_idx" RENAME TO "acct_exrate_curpair_act_idx";')
    elif vendor in ('mysql', 'mariadb'):
        schema_editor.execute('ALTER TABLE `accounts_exchangerate` RENAME INDEX `acct_exrate_base_target_active_idx` TO `acct_exrate_curpair_act_idx`;')
    else:
        # SQLite and other backends: no-op
        pass


def rename_index_backward(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == 'postgresql':
        schema_editor.execute('ALTER INDEX IF EXISTS "acct_exrate_curpair_act_idx" RENAME TO "acct_exrate_base_target_active_idx";')
    elif vendor in ('mysql', 'mariadb'):
        schema_editor.execute('ALTER TABLE `accounts_exchangerate` RENAME INDEX `acct_exrate_curpair_act_idx` TO `acct_exrate_base_target_active_idx`;')
    else:
        # SQLite and other backends: no-op
        pass

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0001_initial'),
        ('sync', '0003_connection_security_level_exchange_security_level'),
    ]

    operations = [
        # Rename index across backends
        migrations.RunPython(
            rename_index_forward,
            rename_index_backward,
        ),
        # Rename the legacy Exchange model to ExchangeTransaction without recreating the table
        migrations.RenameModel(
            old_name='Exchange',
            new_name='ExchangeTransaction',
        ),
        # Add FK field to match current models while preserving db_column (safe if not exists)
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='exchangerate',
                    name='connection',
                    field=models.ForeignKey(blank=True, db_column='connection_id', null=True, on_delete=django.db.models.deletion.SET_NULL, to='sync.connection'),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM information_schema.columns "
                        "WHERE table_name='acct_exchange_rates' AND column_name='connection_id') THEN "
                        "ALTER TABLE \"acct_exchange_rates\" ADD COLUMN \"connection_id\" bigint NULL; END IF; END $$;"
                    ),
                    reverse_sql=(
                        "DO $$ BEGIN IF EXISTS (SELECT 1 FROM information_schema.columns "
                        "WHERE table_name='acct_exchange_rates' AND column_name='connection_id') THEN "
                        "ALTER TABLE \"acct_exchange_rates\" DROP COLUMN \"connection_id\"; END IF; END $$;"
                    ),
                ),
            ],
        ),
        migrations.AlterField(
            model_name='currency',
            name='name',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AlterField(
            model_name='term',
            name='is_active',
            field=models.BooleanField(db_index=True, default=True, help_text='Record is logically active'),
        ),
    ]
