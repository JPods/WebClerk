"""The cash card's Received and Disbursed count money only (plan 102, 2026-11-06): a discount,
write-off, small-balance or FX Cash is an adjustment, never money received. The stored
wc:dd_card metrics take the exclusion the seed now carries (seed_dd_cards)."""
from django.db import migrations

ADJUSTMENTS = ['write_off', 'small_balance', 'fx_gain', 'fx_loss', 'discount']


def forward(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    for s in Setting.objects.filter(purpose='wc:dd_card'):
        config = s.config if isinstance(s.config, dict) else None
        cash = ((config or {}).get('cards') or {}).get('cash') if config else None
        if not cash or not isinstance(cash.get('metrics'), list):
            continue
        changed = False
        for m in cash['metrics']:
            if m.get('field') == 'amount' and m.get('agg') == 'sum' and not m.get('exclude'):
                m['exclude'] = {'method__in': list(ADJUSTMENTS)}
                changed = True
        if changed:
            Setting.objects.filter(pk=s.pk).update(config=config)


class Migration(migrations.Migration):
    dependencies = [('core', '0070_every_setting_has_a_uuid')]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
