from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('transactions', '0015_purchase_receipt'),
    ]

    operations = [
        migrations.AddField(
            model_name='workorder',
            name='work_no',
            field=models.CharField(max_length=64, default='', db_index=True),
        ),
    ]
