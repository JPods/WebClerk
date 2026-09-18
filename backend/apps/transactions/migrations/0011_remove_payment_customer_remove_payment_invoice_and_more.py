# Rename Payment → CashEntry + remove notes fields

import apps.transactions.models.receipt
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orgs', '0004_fk_to_values'),
        ('transactions', '0010_payment_ap_receipt'),
    ]

    operations = [
        # ── Remove notes fields ──
        migrations.RemoveField(
            model_name='paymentapplication',
            name='notes',
        ),
        migrations.RemoveField(
            model_name='receipt',
            name='notes',
        ),

        # ── Rename Payment → CashEntry (preserves table and data) ──
        migrations.RenameModel(
            old_name='Payment',
            new_name='CashEntry',
        ),

        # ── AlterField: update FK targets to new model name ──
        migrations.AlterField(
            model_name='paymentapplication',
            name='payment',
            field=models.ForeignKey(
                db_column='payment_id',
                help_text='The payment being applied',
                on_delete=models.CASCADE,
                related_name='applications',
                to='transactions.cashentry',
            ),
        ),

        # ── Other field changes detected ──
        migrations.AlterField(
            model_name='invoice',
            name='company',
            field=models.JSONField(blank=True, default=dict, help_text='Counterparty snapshot: {id, ida, name, contact_id, attention, full_address, phone, email, domain, is_individual}'),
        ),
        migrations.AlterField(
            model_name='order',
            name='company',
            field=models.JSONField(blank=True, default=dict, help_text='Counterparty snapshot: {id, ida, name, contact_id, attention, full_address, phone, email, domain, is_individual}'),
        ),
        migrations.AlterField(
            model_name='proposal',
            name='company',
            field=models.JSONField(blank=True, default=dict, help_text='Counterparty snapshot: {id, ida, name, contact_id, attention, full_address, phone, email, domain, is_individual}'),
        ),
        migrations.AlterField(
            model_name='purchase',
            name='company',
            field=models.JSONField(blank=True, default=dict, help_text='Counterparty snapshot: {id, ida, name, contact_id, attention, full_address, phone, email, domain, is_individual}'),
        ),
        migrations.AlterField(
            model_name='receipt',
            name='totals',
            field=models.JSONField(blank=True, default=apps.transactions.models.receipt.default_receipt_totals, help_text='AP totals: total, freight, duty, handling, vat, paid, balance', null=True),
        ),
        migrations.AlterField(
            model_name='workorder',
            name='company',
            field=models.JSONField(blank=True, default=dict, help_text='Counterparty snapshot: {id, ida, name, contact_id, attention, full_address, phone, email, domain, is_individual}'),
        ),
    ]
