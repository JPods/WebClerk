"""Every Setting has a uuid (fresh-install proof, 2026-11-06): the bundle packer skips a
Setting without one ("cannot be merge-controlled"), so wc_demo's specification definition and
its wc:ai Setting never reached the bundles and a fresh install had no specification lists."""
import uuid

from django.db import migrations


def forward(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    for s in Setting.objects.filter(uuid__isnull=True):
        Setting.objects.filter(pk=s.pk).update(uuid=uuid.uuid4())


class Migration(migrations.Migration):
    dependencies = [('core', '0069_specification_status_list')]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
