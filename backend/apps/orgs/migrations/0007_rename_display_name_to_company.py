"""display_name becomes company.

Bill, 2026-09-20: *"display_name is not how anyone will refer to it. People are perfectly
content to a customer company being the person's name if they are an individual."* Labels
match field names in this product, so `display_name` was a label users actually read, and a
neutral word invented to cover the rare case made the common one worse for everyone.

Written by hand rather than by makemigrations, which asks interactively whether a field was
renamed and, answered with --no-input, would emit RemoveField + AddField and drop every
company name in the table. RenameField carries the data across.

The `company` property that aliased this column is gone with it — no shim, no fallback.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orgs', '0006_rep_assignment'),
    ]

    operations = [
        # The constraint names the column, so it has to come off before the rename.
        migrations.RemoveConstraint(
            model_name='orgbase',
            name='org_display_name_not_empty',
        ),
        migrations.RenameField(
            model_name='orgbase',
            old_name='display_name',
            new_name='company',
        ),
        migrations.AddConstraint(
            model_name='orgbase',
            constraint=models.CheckConstraint(
                condition=~models.Q(company=''),
                name='org_company_not_empty',
            ),
        ),
    ]
