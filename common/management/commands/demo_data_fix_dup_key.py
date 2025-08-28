# python manage.py demo_data_fix_dup_key

import os      # Standard library for file and path operations
import json    # Standard library for working with JSON data
from collections import Counter  # Import Counter for counting duplicates
from django.core.management.base import BaseCommand  # Base class for Django management commands
from django.apps import apps  # Utility to access all registered Django models

class Command(BaseCommand):

    def handle(self, *args, **options):
        self.check_duplicates("common/management/commands/all_tables_export.json")

    def check_duplicates(self, json_path):
        with open(json_path, 'r') as f:
            data = json.load(f)

        for table, records in data.items():
            ids = [record.get('id') for record in records if 'id' in record]
            counter = Counter(ids)
            duplicates = [id_ for id_, count in counter.items() if count > 1]
            if duplicates:
                self.stdout.write(self.style.ERROR(f"Table '{table}' has duplicate ids: {duplicates}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"Table '{table}' has no duplicate ids."))
def check_duplicates(json_path):
    with open(json_path, 'r') as f:
        data = json.load(f)

    for table, records in data.items():
        ids = [record.get('id') for record in records if 'id' in record]
        counter = Counter(ids)
        duplicates = [id_ for id_, count in counter.items() if count > 1]
        if duplicates:
            print(f"Table '{table}' has duplicate ids: {duplicates}")
        else:
            print(f"Table '{table}' has no duplicate ids.")

if __name__ == "__main__":
    check_duplicates("common/management/commands/all_tables_export.json")