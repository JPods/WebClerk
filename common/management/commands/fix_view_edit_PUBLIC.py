#could not get it to recognize the model from the table name
#clear
#python manage.py fix_view_edit_PUBLIC
from django.core.management.base import BaseCommand
from apps.core.models import Setting
from django.apps import apps

table_model = {
    "actions": "apps.core.Action",
    "settings": "apps.core.Setting",
    "templates": "apps.core.Template",
    "domains": "apps.core.Domain",
    "emails": "apps.communications.Email",
    "phones": "apps.communications.Phone",
    "locations": "apps.communications.Location",
    "contacts": "apps.communications.Contact",
}

class Command(BaseCommand):
    help = "Update PUBLIC.view in Setting.data for all tables"

    def handle(self, *args, **kwargs):
        settings = Setting.objects.filter(purpose="view_edit")
        for setting in settings:
            if not setting.table_name:
                self.stdout.write(f"table_name is None for setting id: {setting.id}")
                continue

            model_path = table_model.get(setting.table_name, None)
            if not model_path:
                self.stdout.write(f"No model mapping for table_name: {setting.table_name}")
                continue

            try:
                app_label, model_name = model_path.rsplit('.', 1)
                model = apps.get_model(app_label, model_name)
            except (ValueError, LookupError):
                self.stdout.write(f"Model not found for table_name: {setting.table_name} (model: {model_path})")
                continue

            objects = model.objects.all()
            public_view_list = []
            for obj in objects:
                field_names = [f.name for f in model._meta.fields if f.name != 'id']
                first3chars = [
                    getattr(obj, name)[:3] if isinstance(getattr(obj, name), str)
                    else str(getattr(obj, name))[:3]
                    for name in field_names
                ]
                public_view_list.append({
                    'id': obj.pk,
                    'fields': first3chars
                })

            if setting.data is None:
                setting.data = Setting._meta.get_field("data").get_default()
            if "PUBLIC" not in setting.data:
                setting.data["PUBLIC"] = {}
            setting.data["PUBLIC"]["view"] = public_view_list
            setting.save()
            self.stdout.write(f"Updated PUBLIC.view for table: {setting.table_name}")