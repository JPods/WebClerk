"""Rename Budget.account → account_debit, add account_credit.

Both sides of every budget entry are now explicit. No assumed
knowledge of the balancing account.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_budget'),
    ]

    operations = [
        # 1. Rename account → account_debit
        migrations.RenameField(
            model_name='budget',
            old_name='account',
            new_name='account_debit',
        ),

        # 2. Add account_credit
        migrations.AddField(
            model_name='budget',
            name='account_credit',
            field=models.CharField(
                blank=True,
                db_index=True,
                default='',
                help_text='GL account being credited (e.g., 1000-CASH, 2100-ACCRUED-PAYROLL)',
                max_length=255,
            ),
        ),

        # 3. Remove old index, add new indexes
        migrations.RemoveIndex(
            model_name='budget',
            name='idx_budget_period_acct',
        ),
        migrations.AddIndex(
            model_name='budget',
            index=models.Index(
                fields=['period', 'account_debit'],
                name='idx_budget_period_acct_dr',
            ),
        ),
        migrations.AddIndex(
            model_name='budget',
            index=models.Index(
                fields=['period', 'account_credit'],
                name='idx_budget_period_acct_cr',
            ),
        ),
    ]
