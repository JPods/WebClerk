"""Add capital asset fields to Purchase and probability to Proposal."""

from django.db import migrations, models


def backfill_proposal_probability(apps, schema_editor):
    """Migrate probability from metadata JSON to scalar field."""
    Proposal = apps.get_model('transactions', 'Proposal')
    updated = 0
    for p in Proposal.objects.filter(metadata__has_key='probability'):
        raw = p.metadata.get('probability')
        if raw is not None:
            try:
                val = float(raw)
                p.probability = val / 100.0 if val > 1.0 else val
                p.save(update_fields=['probability'])
                updated += 1
            except (ValueError, TypeError):
                pass
    if updated:
        print(f'  Backfilled probability on {updated} proposals')


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0007_add_company_json_to_payment_receipt'),
    ]

    operations = [
        migrations.AddField(
            model_name='purchase',
            name='is_capital',
            field=models.BooleanField(
                default=False, db_index=True,
                help_text='True if this purchase is a capital asset (balance sheet, not expense)'),
        ),
        migrations.AddField(
            model_name='purchase',
            name='capital_asset',
            field=models.JSONField(
                null=True, blank=True,
                help_text='Capital asset details: asset_name, useful_life_months, salvage_value, '
                          'depreciation_method, placed_in_service, location, serial_number, notes'),
        ),
        migrations.AddField(
            model_name='proposal',
            name='probability',
            field=models.FloatField(
                default=0.0, db_index=True,
                help_text='Close probability 0.0-1.0. Feeds forecast: totals x probability = weighted pipeline.'),
        ),
        migrations.RunPython(backfill_proposal_probability, migrations.RunPython.noop),
    ]
