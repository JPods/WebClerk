from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        ('sync', '0003_connection_security_level_exchange_security_level'),
    ]

    operations = [
        # Rename the legacy Exchange model to ExchangeTransaction without recreating the table
        migrations.RenameModel(
            old_name='Exchange',
            new_name='ExchangeTransaction',
        ),
        # Rename FK field to match current models while preserving db_column
        migrations.RenameField(
            model_name='exchangetransaction',
            old_name='connection_id',
            new_name='connection',
        ),
        migrations.RenameIndex(
            model_name='exchangerate',
            new_name='acct_exrate_curpair_act_idx',
            old_name='acct_exrate_base_target_active_idx',
        ),
        migrations.RemoveField(
            model_name='exchangerate',
            name='connection_id',
        ),
        migrations.AddField(
            model_name='exchangerate',
            name='connection',
            field=models.ForeignKey(blank=True, db_column='connection_id', null=True, on_delete=django.db.models.deletion.SET_NULL, to='sync.connection'),
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
