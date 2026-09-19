"""Proposal → Quote (Bill, 2026-09-18): the model, its lines, the line's parent link,
and both tables. Renames only — no data is dropped or copied."""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0023_remove_sell_totals_is_the_only_total'),
    ]

    operations = [
        migrations.RenameModel('Proposal', 'Quote'),
        migrations.RenameModel('ProposalLine', 'QuoteLine'),
        migrations.RenameField('QuoteLine', 'proposal', 'quote'),
        migrations.AlterField(
            model_name='quoteline',
            name='quote',
            field=models.ForeignKey(blank=True, db_column='quote_id', null=True,
                                    on_delete=django.db.models.deletion.CASCADE,
                                    related_name='lines', to='transactions.quote'),
        ),
        migrations.AlterModelTable('Quote', 'quotes'),
        migrations.AlterModelTable('QuoteLine', 'quote_lines'),
    ]
