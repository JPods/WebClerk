"""
Seed RBAC roles from code defaults.

Usage:
    python manage.py seed_rbac_roles [--dry-run] [--force]

Options:
    --dry-run   Show what would be created without actually creating
    --force     Overwrite existing RoleConfig records with defaults
"""
from django.core.management.base import BaseCommand

from apps.core.models import RoleConfig, ModelRoleConfig
from apps.core.services.role_defaults import ROLE_DEFAULTS


class Command(BaseCommand):
    help = 'Seed RBAC role configurations from code defaults'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Overwrite existing RoleConfig records with defaults',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']

        self.stdout.write("Seeding RBAC roles from defaults...")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - no changes will be made"))

        roles_created = 0
        roles_updated = 0
        roles_skipped = 0
        model_configs_created = 0
        model_configs_updated = 0

        for role_name, role_data in ROLE_DEFAULTS.items():
            existing = RoleConfig.objects.filter(role=role_name).first()

            if existing and not force:
                roles_skipped += 1
                self.stdout.write(f"  Skipping {role_name} (exists, use --force to overwrite)")
            else:
                # Prepare RoleConfig data
                restricted = role_data.get("restricted_fields", {})
                permissions = role_data.get("permissions", {})
                if restricted:
                    permissions["restricted_fields"] = restricted

                role_config_data = {
                    "role": role_name,
                    "description": role_data.get("description", ""),
                    "is_portal": role_data.get("is_portal", False),
                    "is_active": True,
                    "parent_role": role_data.get("parent_role"),
                    "permissions": permissions,
                }

                if dry_run:
                    action = "UPDATE" if existing else "CREATE"
                    self.stdout.write(f"  [{action}] RoleConfig: {role_name}")
                else:
                    if existing:
                        for key, value in role_config_data.items():
                            if key != "role":
                                setattr(existing, key, value)
                        existing.save()
                        roles_updated += 1
                    else:
                        RoleConfig.objects.create(**role_config_data)
                        roles_created += 1
                    self.stdout.write(
                        f"  {'Updated' if existing else 'Created'} RoleConfig: {role_name}"
                    )

            # Process model configs — role CharField stores the role name string
            models_data = role_data.get("models", {})
            for model_name, model_data in models_data.items():
                if model_name == "*":
                    continue

                view_fields = model_data.get("view_fields", [])
                if view_fields == "*":
                    view_fields = ["*"]

                edit_fields = model_data.get("edit_fields", [])
                if edit_fields == "*":
                    edit_fields = ["*"]

                model_config_data = {
                    "model_name": model_name,
                    "query_filters": model_data.get("query_filters", {}),
                    "view_fields": view_fields,
                    "edit_fields": edit_fields,
                    "allow_create": model_data.get("allow_create", False),
                    "allow_delete": model_data.get("allow_delete", False),
                }

                existing_mrc = ModelRoleConfig.objects.filter(
                    role=role_name,
                    model_name=model_name,
                ).first()

                if dry_run:
                    action = "UPDATE" if existing_mrc else "CREATE"
                    self.stdout.write(f"    [{action}] ModelRoleConfig: {role_name}:{model_name}")
                else:
                    if existing_mrc and force:
                        for key, value in model_config_data.items():
                            if key != "model_name":
                                setattr(existing_mrc, key, value)
                        existing_mrc.save()
                        model_configs_updated += 1
                    elif not existing_mrc:
                        ModelRoleConfig.objects.create(
                            role=role_name,
                            **model_config_data,
                        )
                        model_configs_created += 1

        # Summary
        self.stdout.write("")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN COMPLETE - no changes made"))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Done! Roles: {roles_created} created, {roles_updated} updated, "
                f"{roles_skipped} skipped. "
                f"ModelConfigs: {model_configs_created} created, "
                f"{model_configs_updated} updated."
            ))
