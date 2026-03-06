"""
Seed RBAC roles from code defaults.

Usage:
    python manage.py seed_rbac_roles [--dry-run] [--force]

Options:
    --dry-run   Show what would be created without actually creating
    --force     Overwrite existing RoleConfig records with defaults
"""
from django.core.management.base import BaseCommand, CommandError

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
        
        self.stdout.write(f"Seeding RBAC roles from defaults...")
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
                continue
            
            # Prepare RoleConfig data
            role_config_data = {
                "role": role_name,
                "description": role_data.get("description", ""),
                "is_portal": role_data.get("is_portal", False),
                "is_active": True,
                "parent_role": role_data.get("parent_role"),
                "permissions": role_data.get("permissions", {}),
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
                    role_config = existing
                    roles_updated += 1
                else:
                    role_config = RoleConfig.objects.create(**role_config_data)
                    roles_created += 1
                self.stdout.write(f"  {'Updated' if existing else 'Created'} RoleConfig: {role_name}")
            
            # Process model configs
            models_data = role_data.get("models", {})
            for model_name, model_data in models_data.items():
                if model_name == "*":
                    # Skip wildcard for now - handled at query time
                    continue
                
                # Find existing ModelRoleConfig
                existing_mrc = None
                if not dry_run:
                    existing_mrc = ModelRoleConfig.objects.filter(
                        role=role_config,
                        model_name=model_name
                    ).first()
                
                model_config_data = {
                    "model_name": model_name,
                    "query_filters": model_data.get("query_filters", {}),
                    "view_fields": model_data.get("view_fields", []),
                    "edit_fields": model_data.get("edit_fields", []),
                    "allow_create": model_data.get("allow_create", False),
                    "allow_delete": model_data.get("allow_delete", False),
                }
                
                if dry_run:
                    action = "UPDATE" if existing_mrc else "CREATE"
                    self.stdout.write(f"    [{action}] ModelRoleConfig: {model_name}")
                else:
                    if existing_mrc and force:
                        for key, value in model_config_data.items():
                            if key != "model_name":
                                setattr(existing_mrc, key, value)
                        existing_mrc.save()
                        model_configs_updated += 1
                    elif not existing_mrc:
                        ModelRoleConfig.objects.create(
                            role=role_config,
                            **model_config_data
                        )
                        model_configs_created += 1
        
        # Summary
        self.stdout.write("")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN COMPLETE - no changes made"))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Done! Roles: {roles_created} created, {roles_updated} updated, {roles_skipped} skipped. "
                f"ModelConfigs: {model_configs_created} created, {model_configs_updated} updated."
            ))
