"""One active wc:model Setting per model (Setting audit S-5, 2026-10-28). The old rule
guarded wc:list_column_config, a purpose with no rows."""

from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0035_log_staff_read_all'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='setting',
            name='uniq_active_list_column_config_parent_model',
        ),
        migrations.AddConstraint(
            model_name='setting',
            constraint=models.UniqueConstraint(
                condition=Q(purpose='wc:model') & Q(is_active=True)
                & Q(parent_model__isnull=False) & ~Q(parent_model=''),
                fields=('parent_model', 'purpose'),
                name='uniq_active_wc_model_parent_model',
            ),
        ),
    ]
