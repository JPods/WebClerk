"""Add company JSONB field to payments and receipt tables."""

from django.db import migrations, models


def backfill_company_snapshots(apps, schema_editor):
    """Backfill company snapshots from linked customer/vendor orgs."""
    from django.db import connection
    cursor = connection.cursor()

    # Payment: snapshot from customer or vendor
    cursor.execute("""
        UPDATE transactions_payment p
        SET company = jsonb_build_object(
            'id', COALESCE(o.id, 0),
            'ida', COALESCE(o.ida, ''),
            'name', COALESCE(o.display_name, ''),
            'is_individual', false,
            'attention', COALESCE(o.attention, ''),
            'email', COALESCE(o.email, ''),
            'phone', COALESCE(o.phone, ''),
            'domain', COALESCE(o.domain, ''),
            'notes', ''
        )
        FROM orgs_orgbase o
        WHERE o.id = COALESCE(p.customer_id, p.vendor_id)
          AND (p.company IS NULL OR p.company = '{}'::jsonb)
    """)

    # Receipt: snapshot from purchase's vendor
    cursor.execute("""
        UPDATE receipt r
        SET company = jsonb_build_object(
            'id', COALESCE(o.id, 0),
            'ida', COALESCE(o.ida, ''),
            'name', COALESCE(o.display_name, ''),
            'is_individual', false,
            'attention', COALESCE(o.attention, ''),
            'email', COALESCE(o.email, ''),
            'phone', COALESCE(o.phone, ''),
            'domain', COALESCE(o.domain, ''),
            'notes', ''
        )
        FROM purchases pu
        JOIN orgs_orgbase o ON o.id = pu.vendor_id
        WHERE pu.id = r.purchase_id
          AND (r.company IS NULL OR r.company = '{}'::jsonb)
    """)


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0006_add_company_json_to_transactions'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='company',
            field=models.JSONField(blank=True, default=dict,
                help_text='Counterparty snapshot: {id, ida, name, is_individual, attention, email, phone, domain, notes}'),
        ),
        migrations.AddField(
            model_name='receipt',
            name='company',
            field=models.JSONField(blank=True, default=dict,
                help_text='Counterparty snapshot: {id, ida, name, is_individual, attention, email, phone, domain, notes}'),
        ),
        migrations.RunPython(backfill_company_snapshots, migrations.RunPython.noop),
    ]
