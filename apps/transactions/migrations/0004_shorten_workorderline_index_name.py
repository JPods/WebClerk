from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("transactions", "0003_workorder_choices_indexes"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="workorderline",
            name="workorderline_parent_status_idx",
        ),
        migrations.AddIndex(
            model_name="workorderline",
            index=models.Index(fields=["parent_ref_id", "status"], name="wo_line_parent_status_idx"),
        ),
    ]
