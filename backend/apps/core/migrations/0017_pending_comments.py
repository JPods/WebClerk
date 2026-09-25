from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_pending_gateway_event_unique'),
    ]

    operations = [
        migrations.AddField(
            model_name='pending',
            name='comments',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
