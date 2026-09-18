"""copyright column → config.copyright.

A declared term about the document, not observed state, so it belongs in the
config envelope (permanent) rather than in a column of its own. The column held
no data in any installation, so there is nothing to carry across.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('docs', '0003_add_document_model_name_record_id'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='document',
            name='copyright',
        ),
    ]
