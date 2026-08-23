import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('docs', '0005_remove_document_model_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='questionanswer',
            name='document',
            field=models.ForeignKey(
                blank=True,
                db_column='document_id',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='qa_questions_doc',
                to='docs.document',
            ),
        ),
    ]
