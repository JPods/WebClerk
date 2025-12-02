from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="setting",
            old_name="model_name",
            new_name="model_target",
        ),
    ]
