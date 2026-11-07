"""Where an org came from: source_name on every org, the same list as a contact's (Bill,
2026-11-07, readme 106 B: "consistency is good"). A document takes it from its party like terms."""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('orgs', '0012_drop_org_type')]
    operations = [
        migrations.AddField(
            model_name='orgbase', name='source_name',
            field=models.CharField(blank=True, db_index=True, default='', max_length=80,
                                   help_text="How this org originated: referral, website, trade show, … (the contact's list)"),
        ),
    ]
