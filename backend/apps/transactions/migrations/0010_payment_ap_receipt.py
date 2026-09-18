"""Add AP payment support: receipt FK on Payment, totals on Receipt,
rename Payment.type received/expense → cash_in/cash_out.

Schema + data migration in one file.
"""
from django.db import migrations, models
import django.db.models.deletion


def default_receipt_totals():
    return {
        "total": 0,
        "freight": 0,
        "duty": 0,
        "handling": 0,
        "vat": 0,
        "paid": 0,
        "balance": 0,
    }


def rename_payment_types_forward(apps, schema_editor):
    """Rename received → cash_in, expense → cash_out in existing data."""
    Payment = apps.get_model('transactions', 'Payment')
    Payment.objects.filter(type='received').update(type='cash_in')
    Payment.objects.filter(type='expense').update(type='cash_out')


def rename_payment_types_backward(apps, schema_editor):
    """Reverse: cash_in → received, cash_out → expense."""
    Payment = apps.get_model('transactions', 'Payment')
    Payment.objects.filter(type='cash_in').update(type='received')
    Payment.objects.filter(type='cash_out').update(type='expense')


def sync_receipt_totals_forward(apps, schema_editor):
    """Populate totals JSON from existing scalar fields on all receipts."""
    Receipt = apps.get_model('transactions', 'Receipt')
    for r in Receipt.objects.all():
        r.totals = {
            'total': float(r.vendor_invoice_amount),
            'freight': float(r.vendor_invoice_freight),
            'duty': float(r.duty),
            'handling': float(r.handling),
            'vat': float(r.vat),
            'paid': 0,
            'balance': float(r.vendor_invoice_amount),
        }
        r.save(update_fields=['totals'])


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0009_align_model_fields'),
    ]

    operations = [
        # 1. Add receipt FK to Payment
        migrations.AddField(
            model_name='payment',
            name='receipt',
            field=models.ForeignKey(
                blank=True,
                db_column='receipt_id',
                help_text='Receipt this payment applies to (AP — cash_out)',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='payments',
                to='transactions.receipt',
            ),
        ),

        # 2. Add totals JSONField to Receipt
        migrations.AddField(
            model_name='receipt',
            name='totals',
            field=models.JSONField(
                blank=True,
                default=default_receipt_totals,
                help_text='AP totals: total, freight, duty, handling, vat, paid, balance',
                null=True,
            ),
        ),

        # 3. Update Payment.type choices (schema only — Django stores the
        #    choices on the field definition, not in the database)
        migrations.AlterField(
            model_name='payment',
            name='type',
            field=models.CharField(
                choices=[('cash_in', 'Cash In'), ('cash_out', 'Cash Out')],
                db_index=True,
                default='cash_out',
                help_text='Required. cash_in=money in (AR), cash_out=money out (AP). Category tells the rest.',
                max_length=20,
            ),
        ),

        # 4. Data migration: rename existing type values
        migrations.RunPython(
            rename_payment_types_forward,
            rename_payment_types_backward,
        ),

        # 5. Populate receipt totals from scalar fields
        migrations.RunPython(
            sync_receipt_totals_forward,
            migrations.RunPython.noop,
        ),
    ]
