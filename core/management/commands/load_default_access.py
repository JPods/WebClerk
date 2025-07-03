import os
import json
from django.core.management.base import BaseCommand
from ...models import Setting

class Command(BaseCommand):
    help = 'Load default access settings from JSON file into Setting model'

    def handle(self, *args, **options):
        # Path to the JSON file
        json_file_path = os.path.join(os.getcwd(), 'common','default_access.json')
        
        try:
            # Read the JSON file
            with open(json_file_path, 'r') as file:
                data = json.load(file)
            
            # Counters for tracking inserted and updated records
            inserted_count = 0
            updated_count = 0
            
            # Loop through each object in the JSON array
            for item in data:
                try:
                    # Check if a setting with the same attributes already exists
                    existing_setting = Setting.objects.filter(
                        name=item.get('name'),
                        purpose=item.get('purpose'),
                        role=item.get('role'),
                        table_name=item.get('table_name')
                    ).first()
                    
                    if existing_setting:
                        # Update existing setting
                        existing_setting.is_active = item.get('is_active', True)
                        existing_setting.data = item.get('data')
                        existing_setting.comment = item.get('comment')
                        existing_setting.save()
                        updated_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Updated setting with name '{item.get('name')}', "
                                f"purpose '{item.get('purpose')}', "
                                f"role '{item.get('role')}', "
                                f"table_name '{item.get('table_name')}'"
                            )
                        )
                    else:
                        # Create new Setting instance
                        Setting.objects.create(
                            is_active=item.get('is_active', True),
                            name=item.get('name'),
                            purpose=item.get('purpose'),
                            role=item.get('role'),
                            table_name=item.get('table_name'),
                            data=item.get('data'),
                            comment=item.get('comment')
                        )
                        inserted_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Created setting with name '{item.get('name')}', "
                                f"purpose '{item.get('purpose')}', "
                                f"role '{item.get('role')}', "
                                f"table_name '{item.get('table_name')}'"
                            )
                        )
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Error processing item {item.get('name', 'unknown')}: {str(e)}"
                        )
                    )
            
            # Summary
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully loaded {inserted_count} new settings and updated {updated_count} existing settings."
                )
            )
            
        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR(f"JSON file not found at: {json_file_path}")
            )
        except json.JSONDecodeError:
            self.stdout.write(
                self.style.ERROR("Invalid JSON format in the file")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"An error occurred: {str(e)}")
            )