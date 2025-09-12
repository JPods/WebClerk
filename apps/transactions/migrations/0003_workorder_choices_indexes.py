from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0002_workorder_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='workorder',
            name='status',
            field=models.CharField(
                choices=[
                    ('planned', 'Planned'),
                    ('released', 'Released'),
                    ('in_progress', 'In Progress'),
                    ('hold', 'Hold'),
                    ('complete', 'Complete'),
                    ('canceled', 'Canceled'),
                ],
                db_index=True,
                default='planned',
                help_text='Lifecycle state',
                max_length=30,
            ),
        ),
        migrations.AddIndex(
            model_name='workorder',
            index=models.Index(fields=['status', 'dt_created'], name='workorder_status_created_idx'),
        ),
        migrations.AddIndex(
            model_name='workorderline',
            index=models.Index(fields=['parent_ref_id', 'status'], name='workorderline_parent_status_idx'),
        ),
    ]
