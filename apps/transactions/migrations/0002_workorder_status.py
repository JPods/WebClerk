from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='workorder',
            name='status',
            field=models.CharField(
                max_length=30,
                blank=True,
                db_index=True,
                default='planned',
                help_text='Optional lifecycle / state label',
            ),
        ),
    ]
