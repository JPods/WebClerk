"""The PDF designer is gone (Bill, 2026-10-28): its templates, config.pdfme_template on a
Report, are read by nothing, so they leave the records."""

from django.db import migrations


def strip(apps, schema_editor):
    Report = apps.get_model('core', 'Report')
    for report in Report.objects.filter(config__has_key='pdfme_template'):
        config = dict(report.config)
        config.pop('pdfme_template')
        Report.objects.filter(pk=report.pk).update(config=config)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0037_ai_agent_alice'),
    ]

    operations = [
        migrations.RunPython(strip, migrations.RunPython.noop),
    ]
