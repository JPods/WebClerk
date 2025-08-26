#from django.apps import apps
from django.db import models
from django.core.management.base import BaseCommand
import json

class Command(BaseCommand):
    help = "Build settings for working with gantt charts"

    #required_fields = ["name", "purpose", "role", "table_name", "data"]

    required_fields = ["name", "purpose", "role", "table_name", "data"]

    def create_settings_record(self, **kwargs):
        """
        #Stub: Create a settings record for gantt charts.
        #Required fields: name, purpose, role, table_name, data
        #Returns the created record as a dictionary.
        """
        record = {}
        for field in self.required_fields:
            record[field] = kwargs.get(field)
        # TODO: Save record to DB or file as needed
        self.stdout.write(f"Settings record created: {json.dumps(record, indent=2)}")
        return record
    
    def assign_by_field(self):
        settings_data = {
            "name": "Project Gantt",
            "purpose": "Track project tasks",
            "role": "admin",
            "table_name": "actions",
            "data": {"some": "value"}
        }
        record = self.create_settings_record(**settings_data)
        return record
    
    def load_from_json(self, json_string):
        """
        Load settings from a JSON string and create a settings record.
        
        """
        try:
            settings_data = json.loads(json_string)
        except json.JSONDecodeError as e:
            self.stderr.write(f"Invalid JSON: {e}")
            return None

        # Validate required fields
        missing_fields = [field for field in self.required_fields if field not in settings_data]
        if missing_fields:
            self.stderr.write(f"Missing required fields: {', '.join(missing_fields)}")
            return None

        record = self.create_settings_record(**settings_data)
        return record

    def example_json(self):
        """
        Return an example JSON string for gantt chart settings.
        """
        example_json = {
            "name": "Project Gantt",
            "purpose": "Track project tasks",
            "role": "admin",
            "table_name": "actions",
            "data": {"some": "value"}
        }
        return json.dumps(example_json, indent=2)

    def example_record(self):
        """
        Return an example settings record created from the example JSON.
        """
        settings_data = json.loads(self.example_json())
        record = self.create_settings_record(**settings_data)
        return record   