import json
from django.core.management.base import BaseCommand
from django.apps import apps

class Command(BaseCommand):
    help = "Import all fields from a JSON file into their respective tables, updating if id exists"

    def add_arguments(self, parser):
        parser.add_argument('json_path', type=str, help='Path to the JSON file to import')

    def handle(self, *args, **options):
        path = options['json_path']
        with open(path, 'r') as f:
            all_data = json.load(f)

        for model_key, records in all_data.items():
            try:
                app_label, model_name = model_key.split('.')
                model = apps.get_model(app_label, model_name)
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Could not find model {model_key}: {e}"))
                continue

            model_fields = set(f.name for f in model._meta.fields)
            pk_name = model._meta.pk.name
            for record in records:
                filtered_record = {k: v for k, v in record.items() if k in model_fields}
                skipped_fields = set(record.keys()) - model_fields
                if skipped_fields:
                    self.stdout.write(self.style.WARNING(
                        f"Skipped fields for {model_key}: {', '.join(skipped_fields)}"
                    ))
                try:
                    obj = None
                    if pk_name in filtered_record:
                        try:
                            obj = model.objects.get(**{pk_name: filtered_record[pk_name]})
                        except model.DoesNotExist:
                            obj = None
                    if obj:
                        for k, v in filtered_record.items():
                            setattr(obj, k, v)
                        obj.save()
                        self.stdout.write(self.style.SUCCESS(
                            f"Updated {model_key} record with {pk_name}={filtered_record[pk_name]}"
                        ))
                    else:
                        model.objects.create(**filtered_record)
                        self.stdout.write(self.style.SUCCESS(
                            f"Created new {model_key} record"
                        ))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f"Failed to process {model_key} record: {e}"
                    ))

        self.stdout.write(self.style.SUCCESS(f"Import completed from {path}"))