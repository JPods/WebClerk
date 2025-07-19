import os
import json
from django.core.management.base import BaseCommand
from ...models import Setting

# before running this command, ensure that the JSON file exists at the specified path.
# make sure the virtual environment is activated, source ./bin/activate
# this activates the Django environment in the base folder and 
# allows you to run management commands.
# execute this in terminal with: python manage.py load_default_company

class Command(BaseCommand):
    help = "Load default company"

    def handle(self, *args, **options):
        # Path to the JSON file
        json_file_path = os.path.join(os.getcwd(), "common", "default_company.json")

        try:
            # Read the JSON file
            with open(json_file_path, "r") as file:
                data = json.load(file)

            # Validate that data is a list
            if not isinstance(data, list):
                raise ValueError("JSON file must contain an array of objects")

            # Counters for tracking inserted and updated records
            inserted_count = 0
            updated_count = 0

            # Loop through each object in the JSON array
            for item in data:
                try:
                    # Validate required fields
                    required_fields = ["name", "purpose", "role", "table_name", "data"]
                    missing_fields = [field for field in required_fields if field not in item]
                    if missing_fields:
                        self.stdout.write(
                            self.style.ERROR(
                                f"Missing required fields {missing_fields} in item with name '{item.get('name', 'unknown')}'"
                            )
                        )
                        continue

                    # Check if a setting with the same attributes already exists
                    existing_setting = Setting.objects.filter(
                        name=item["name"], purpose=item["purpose"], role=item["role"], table_name=item["table_name"]
                    ).first()

                    if existing_setting:
                        # Update existing setting
                        existing_setting.is_active = item.get("is_active", True)
                        existing_setting.data = item["data"]
                        existing_setting.comment = item.get("comment", "")
                        existing_setting.save()
                        updated_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Updated setting with name '{item['name']}', "
                                f"purpose '{item['purpose']}', "
                                f"role '{item['role']}', "
                                f"table_name '{item['table_name']}'"
                            )
                        )
                    else:
                        # Create new Setting instance
                        Setting.objects.create(
                            is_active=item.get("is_active", True),
                            name=item["name"],
                            purpose=item["purpose"],
                            role=item["role"],
                            table_name=item["table_name"],
                            data=item["data"],
                            comment=item.get("comment", ""),
                        )
                        inserted_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Created setting with name '{item['name']}', "
                                f"purpose '{item['purpose']}', "
                                f"role '{item['role']}', "
                                f"table_name '{item['table_name']}'"
                            )
                        )

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"Error processing item {item.get('name', 'unknown')}: {str(e)}")
                    )

            # Summary
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully loaded {inserted_count} new settings and updated {updated_count} existing settings."
                )
            )

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"JSON file not found at: {json_file_path}"))
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR("Invalid JSON format in the file"))
        except ValueError as ve:
            self.stdout.write(self.style.ERROR(f"Validation error: {str(ve)}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {str(e)}"))
