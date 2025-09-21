from django.core.management.base import BaseCommand
from django.apps import apps
from typing import List, Optional

class Command(BaseCommand):
    help = "Enable/disable wcapi exposure for models via core.Setting."

    def add_arguments(self, parser):
        parser.add_argument("--app", action="append", dest="apps", help="App label to include (repeatable)")
        parser.add_argument("--model", action="append", dest="models", help="Model name (model_name) to toggle (repeatable)")
        parser.add_argument("--all", action="store_true", dest="all_models", help="Affect all models")
        parser.add_argument("--disable", action="store_true", dest="disable", help="Set is_active=False")

    def handle(self, *args, **opts):
        Setting = apps.get_model("core", "Setting")
        target_apps: Optional[List[str]] = [a.lower() for a in (opts.get("apps") or [])] or None
        target_models: Optional[List[str]] = [m.lower() for m in (opts.get("models") or [])] or None
        affect_all: bool = bool(opts.get("all_models"))
        enable = not bool(opts.get("disable"))

        if not affect_all and not target_apps and not target_models:
            self.stderr.write("Specify --all or at least one --app/--model")
            return

        changed = 0
        for Model in apps.get_models():
            app_ok = not target_apps or Model._meta.app_label.lower() in target_apps
            model_ok = not target_models or (Model._meta.model_name or "").lower() in target_models
            if not affect_all and not (app_ok or model_ok):
                continue
            obj, _ = Setting.objects.get_or_create(
                purpose="wcapi",
                model_name=Model._meta.model_name,
                defaults={"is_active": False, "data": {"allow_fields": None, "rules": {}}},
            )
            current_is_active = getattr(obj, "is_active", None)
            if current_is_active != enable:
                setattr(obj, "is_active", enable)
                obj.save(update_fields=["is_active"])
                changed += 1
        state = "enabled" if enable else "disabled"
        self.stdout.write(self.style.SUCCESS(f"{state} wcapi on {changed} models"))