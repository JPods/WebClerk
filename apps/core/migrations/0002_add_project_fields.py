# Generated manually for adding project fields to Action model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='action',
            name='project_name',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='action',
            name='project_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]