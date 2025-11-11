# Generated manually for converting multilingual fields to JSON

from django.db import migrations, models


def migrate_multilingual_data_forward(apps, schema_editor):
    Action = apps.get_model('core', 'Action')
    for action in Action.objects.all():
        # Convert action fields
        action_dict = {}
        if action.action_en:
            action_dict['en'] = action.action_en
        if action.action_ar:
            action_dict['ar'] = action.action_ar
        if action.action_bn:
            action_dict['bn'] = action.action_bn
        if action.action_es:
            action_dict['es'] = action.action_es
        action.action = action_dict

        # Convert description fields
        desc_dict = {}
        if action.description_en:
            desc_dict['en'] = action.description_en
        if action.description_ar:
            desc_dict['ar'] = action.description_ar
        if action.description_bn:
            desc_dict['bn'] = action.description_bn
        if action.description_es:
            desc_dict['es'] = action.description_es
        action.description = desc_dict

        action.save()


def migrate_multilingual_data_reverse(apps, schema_editor):
    Action = apps.get_model('core', 'Action')
    for action in Action.objects.all():
        # Reverse convert action fields
        action_dict = action.action or {}
        action.action_en = action_dict.get('en')
        action.action_ar = action_dict.get('ar')
        action.action_bn = action_dict.get('bn')
        action.action_es = action_dict.get('es')

        # Reverse convert description fields
        desc_dict = action.description or {}
        action.description_en = desc_dict.get('en')
        action.description_ar = desc_dict.get('ar')
        action.description_bn = desc_dict.get('bn')
        action.description_es = desc_dict.get('es')

        action.save()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_rename_kanban_meta_to_project_metadata'),
    ]

    operations = [
        migrations.AddField(
            model_name='action',
            name='action',
            field=models.JSONField(blank=True, default=dict, null=True),
        ),
        migrations.AddField(
            model_name='action',
            name='description',
            field=models.JSONField(blank=True, default=dict, null=True),
        ),
        migrations.RunPython(
            migrate_multilingual_data_forward,
            migrate_multilingual_data_reverse
        ),
        migrations.RemoveField(
            model_name='action',
            name='action_en',
        ),
        migrations.RemoveField(
            model_name='action',
            name='action_ar',
        ),
        migrations.RemoveField(
            model_name='action',
            name='action_bn',
        ),
        migrations.RemoveField(
            model_name='action',
            name='action_es',
        ),
        migrations.RemoveField(
            model_name='action',
            name='description_en',
        ),
        migrations.RemoveField(
            model_name='action',
            name='description_ar',
        ),
        migrations.RemoveField(
            model_name='action',
            name='description_bn',
        ),
        migrations.RemoveField(
            model_name='action',
            name='description_es',
        ),
    ]