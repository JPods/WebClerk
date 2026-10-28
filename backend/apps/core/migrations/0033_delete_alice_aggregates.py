"""Delete Alice's sales-totals Settings (purpose alice:aggregates).

Settings hold application structure and Alice's behaviour options, not data. The
tracker that kept these rows locked one Setting row in every transaction save and
held wrong totals (29 invoices against 36). Totals are computed when asked.
"""

from django.db import migrations


def delete_aggregates(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    Setting.objects.filter(purpose='alice:aggregates').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0032_inventory_events_to_log'),
    ]

    operations = [
        migrations.RunPython(delete_aggregates, migrations.RunPython.noop),
    ]
