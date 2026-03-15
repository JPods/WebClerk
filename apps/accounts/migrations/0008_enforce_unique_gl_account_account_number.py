from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0007_load_default_gl_accounts"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="glaccount",
            constraint=models.UniqueConstraint(
                fields=("account_number",),
                condition=(
                    Q(is_active=True)
                    & Q(is_deleted=False)
                    & Q(is_archived=False)
                    & Q(account_number__isnull=False)
                    & ~Q(account_number="")
                ),
                name="uniq_active_gl_account_account_number",
            ),
        ),
    ]
