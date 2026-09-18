# Cash applications are recorded by Pending (purpose payment_application) and Ledger.
# PaymentApplication and PendingPaymentApplication were duplicate paths.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0016_line_type_finance_charge'),
    ]

    operations = [
        migrations.DeleteModel(
            name='PaymentApplication',
        ),
        # PendingPaymentApplication left the migration state before the clean start;
        # its table can still exist in databases created earlier.
        migrations.RunSQL(
            "DROP TABLE IF EXISTS pending_payment_applications",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            "DELETE FROM settings WHERE purpose = 'wc:model' AND parent_model IN ('payment_application', 'pending_payment_application')",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
