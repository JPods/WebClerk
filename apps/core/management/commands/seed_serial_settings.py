"""Seed the Setting record for Serial model -- actions, statuses, and behaviors."""
from django.core.management.base import BaseCommand
from apps.core.models import Setting
from common.schemas.serial import DEFAULT_SERIAL_ACTIONS


SERIAL_STATUSES = [
    {"value": "available", "label": "Available", "description": "In stock, ready to sell or assign"},
    {"value": "received", "label": "Received", "description": "Received on PO, not yet put away or made available"},
    {"value": "reserved", "label": "Reserved", "description": "Held for an order, not yet shipped"},
    {"value": "issued", "label": "Issued", "description": "Shipped or sold on invoice"},
    {"value": "returned", "label": "Returned", "description": "Came back from customer, pending inspection"},
    {"value": "referenced", "label": "Referenced", "description": "Linked to a document without physical movement"},
    {"value": "warranty", "label": "Warranty", "description": "Active warranty claim in progress"},
    {"value": "damaged", "label": "Damaged", "description": "Marked damaged, not available for sale"},
    {"value": "scrapped", "label": "Scrapped", "description": "Written off"},
]


class Command(BaseCommand):
    help = "Seed Setting record for Serial model (actions, statuses, behaviors)"

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Overwrite existing setting")

    def handle(self, *args, **options):
        existing = Setting.objects.filter(
            parent_model="serial", purpose="schema_map", is_active=True
        ).first()

        if existing and not options["force"]:
            self.stdout.write(f"Setting.serial already exists (id={existing.pk}). Use --force to overwrite.")
            return

        config = {
            "serial_actions": DEFAULT_SERIAL_ACTIONS,
            "serial_statuses": SERIAL_STATUSES,
            "pydantic_schema": "common.schemas.serial",
            "config_schema": "SerialConfig",
            "action_schema": "SerialAction",
            "behaviors": {
                "warranty_starts_on": "issued",
                "default_receive_status": "received",
                "default_return_status": "returned",
                "floor_plan_enabled": True,
                "require_notes_on_scrap": True,
                "require_notes_on_damage": True,
                "require_notes_on_return": True,
                "auto_available_after_inspection": False,
            },
        }

        if existing:
            existing.config = config
            existing.name = "Serial schema and behaviors"
            existing.save()
            self.stdout.write(f"Updated Setting.serial (id={existing.pk})")
        else:
            setting = Setting.objects.create(
                name="Serial schema and behaviors",
                parent_model="serial",
                purpose="schema_map",
                scope="system",
                config=config,
            )
            self.stdout.write(f"Created Setting.serial (id={setting.pk})")
