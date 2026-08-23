"""
Add document_type to Report.config for key print templates.
Enables pdfme PDF generation from the Report record.

Replaces earlier Setting-based approach — Reports are the right model
for document definitions. Settings are for configuration.
"""
from django.db import migrations


# Map report names to pdfme document_type keys
DOCUMENT_TYPE_MAP = {
    ('invoice', 'Invoice - Standard'): 'invoice',
    ('invoice', 'Credit Memo'): 'creditmemo',
    ('invoice', 'Invoice - Shipping'): 'invoice',
    ('invoice', 'Invoice - Shipping w/Disc'): 'invoice',
    ('invoice', 'Invoice - PP Ship'): 'invoice',
    ('invoice', 'Invoice - PP Standard'): 'invoice',
    ('invoice', 'Invoice - Foreign'): 'invoice',
    ('invoice', 'Net Invoice'): 'invoice',
    ('order', 'Order Confirmation'): 'order',
    ('proposal', 'Proposal 1'): 'proposal',
    ('purchase', 'Purchase Order'): 'purchase',
    ('workorder', 'Work Order'): 'workorder',
}


def add_document_types(apps, schema_editor):
    Report = apps.get_model('core', 'Report')
    Setting = apps.get_model('core', 'Setting')

    for (model_name, name), doc_type in DOCUMENT_TYPE_MAP.items():
        reports = Report.objects.filter(
            model_name=model_name, name=name, output_type='print',
        )
        for report in reports:
            config = report.config or {}
            config['document_type'] = doc_type
            report.config = config
            report.save(update_fields=['config'])

    # Remove Setting records from earlier approach (if any)
    Setting.objects.filter(purpose='print_template').delete()


def remove_document_types(apps, schema_editor):
    Report = apps.get_model('core', 'Report')
    for (model_name, name), _ in DOCUMENT_TYPE_MAP.items():
        reports = Report.objects.filter(
            model_name=model_name, name=name, output_type='print',
        )
        for report in reports:
            config = report.config or {}
            config.pop('document_type', None)
            report.config = config
            report.save(update_fields=['config'])


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0027_purpose_to_basemodel'),
    ]
    operations = [
        migrations.RunPython(add_document_types, remove_document_types),
    ]
