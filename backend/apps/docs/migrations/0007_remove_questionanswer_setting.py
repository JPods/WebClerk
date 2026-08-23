"""Remove setting FK from QuestionAnswer — Document is the only template source."""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('docs', '0006_questionanswer_document'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='questionanswer',
            name='setting',
        ),
    ]
