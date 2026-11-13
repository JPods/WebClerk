"""An inquiry form no longer exempts a tester mailbox from its limits (Bill, 2026-11-13:
"remove all zzqq behaviors"; users train on real data or keep a separate training set).
InquiryLimits forbids unknown keys, so a Report that still stored config.inquiry.limits.testing
would stop validating and its public form would stop answering. This removes the key.
"""
from django.db import migrations


def forward(apps, schema_editor):
    Report = apps.get_model('core', 'Report')
    for report in Report.objects.filter(config__inquiry__limits__has_key='testing'):
        config = dict(report.config)
        inquiry = dict(config['inquiry'])
        inquiry['limits'] = {k: v for k, v in inquiry['limits'].items() if k != 'testing'}
        config['inquiry'] = inquiry
        report.config = config
        report.save(update_fields=['config'])


class Migration(migrations.Migration):
    dependencies = [('core', '0073_org_access_leaves_for_defaults_and_source')]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
