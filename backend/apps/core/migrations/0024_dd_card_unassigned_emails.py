"""The Administration dashboard shows unassigned emails (Bill, 2026-10-16).

Adds the "email" card (server_action get_email_health, linking to the list of Email records
with no contact) to an existing dd_card:base Setting and puts it on the operations
dashboard. A card or row an admin already changed is left alone: the card is added only
when absent, the row only when no row names it.
"""
from django.db import migrations

CARD = {
    'label': 'Unassigned Emails',
    'link': '/databrowser?model=email&contact__isnull=true',
    'server_action': 'get_email_health',
    'metrics': [],
}


def forward(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    for setting in Setting.objects.filter(purpose='wc:dd_card', name='dd_card:base'):
        config = setting.config if isinstance(setting.config, dict) else {}
        cards = config.setdefault('cards', {})
        changed = 'email' not in cards
        cards.setdefault('email', CARD)
        ops = (config.get('dashboards') or {}).get('operations')
        if isinstance(ops, dict) and isinstance(ops.get('rows'), list):
            if not any('email' in row for row in ops['rows'] if isinstance(row, list)):
                ops['rows'].append(['email'])
                changed = True
        if changed:
            Setting.objects.filter(pk=setting.pk).update(config=config)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_is_locked_setting_leaves'),
    ]

    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
