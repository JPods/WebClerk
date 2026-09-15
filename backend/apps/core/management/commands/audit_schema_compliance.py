"""Audit schema compliance — read-only report of Setting violations.

Usage:
    ./manage.py audit_schema_compliance              # report only
    ./manage.py audit_schema_compliance --fix        # Alice mode: fix violations
    ./manage.py audit_schema_compliance --records     # also check record envelopes
    ./manage.py audit_schema_compliance --model contact  # check one model's records
    ./manage.py audit_schema_compliance --enforce    # PJPV: reshape all records to current schema
    ./manage.py audit_schema_compliance --enforce --dry-run  # show what would change
"""
from django.core.management.base import BaseCommand
from apps.core.services.schema_validate import (
    audit_all_schema_settings,
    validate_record_envelopes,
    enforce_pjpv_schemas,
)


class Command(BaseCommand):
    help = "Audit Setting schema records for BaseModel compliance"

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix', action='store_true',
            help='Fix violations (Alice mode). Default: report only.',
        )
        parser.add_argument(
            '--records', action='store_true',
            help='Also check record-level envelope compliance.',
        )
        parser.add_argument(
            '--model', type=str, default=None,
            help='Check records for this model only (requires --records or --enforce).',
        )
        parser.add_argument(
            '--limit', type=int, default=100,
            help='Max records to check per model (default 100).',
        )
        parser.add_argument(
            '--enforce', action='store_true',
            help='PJPV: reshape all JSON envelopes to current Pydantic schema. '
                 'Unknown keys → userdefined{}. Missing keys → defaults.',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Show what --enforce would change without saving.',
        )

    def handle(self, *args, **options):
        fix = options.get('fix', False)

        # ── PJPV Enforce mode — reshape all records to current schema ──
        if options.get('enforce'):
            self.stdout.write(self.style.MIGRATE_HEADING(
                '\n=== PJPV Schema Enforcement ===\n'
            ))
            result = enforce_pjpv_schemas(
                model_filter=options.get('model'),
                dry_run=options.get('dry_run', False),
                stdout=self.stdout,
                style=self.style,
            )
            self.stdout.write(f"\nRecords checked: {result['total_records']}")
            self.stdout.write(f"Records reshaped: {result['reshaped']}")
            self.stdout.write(f"Unknown keys moved to userdefined: {result['unknown_keys_moved']}")
            self.stdout.write(f"Missing keys filled: {result['missing_keys_filled']}")
            self.stdout.write(f"Errors: {result['errors']}")
            if options.get('dry_run'):
                self.stdout.write(self.style.WARNING('\n  DRY RUN — no changes saved.\n'))
            return

        # ── Layer 1: Setting schema compliance ──
        self.stdout.write(self.style.MIGRATE_HEADING(
            '\n=== Layer 1: Setting Schema Compliance ===\n'
        ))

        result = audit_all_schema_settings(fix=fix)

        self.stdout.write(f"Settings checked: {result['total_settings']}")
        self.stdout.write(f"Clean: {result['clean_settings']}")
        self.stdout.write(f"With violations: {result['settings_with_violations']}")
        self.stdout.write(f"Total violations: {len(result['violations'])}")

        if result['violations']:
            self.stdout.write('')
            for v in result['violations']:
                icon = self.style.SUCCESS('  FIXED') if fix else self.style.ERROR('  FAIL')
                self.stdout.write(
                    f"{icon} [{v['purpose']}] {v['parent_model']}.{v['field']} "
                    f"— {v['violation_type']}: {v['message']}"
                )
        else:
            self.stdout.write(self.style.SUCCESS('\n  All settings comply with BaseModel.\n'))

        # ── Layer 2: Record envelope compliance (optional) ──
        if options.get('records'):
            self.stdout.write(self.style.MIGRATE_HEADING(
                '\n=== Layer 2: Record Envelope Compliance ===\n'
            ))
            self._check_records(
                model_filter=options.get('model'),
                limit=options.get('limit', 100),
                fix=fix,
            )

    def _check_records(self, model_filter=None, limit=100, fix=False):
        """Check record-level envelope compliance."""
        from django.apps import apps as django_apps
        from apps.core.constants.model_registry import MODEL_REGISTRY

        models_to_check = {}
        for key, meta in MODEL_REGISTRY.items():
            if model_filter and key != model_filter:
                continue
            try:
                parts = meta.model.rsplit('.', 1)
                if len(parts) == 2:
                    module_path, class_name = parts
                    app_label = module_path.split('.')[1]  # apps.<app_label>.models...
                    Model = django_apps.get_model(app_label, class_name)
                    models_to_check[key] = Model
            except Exception:
                continue

        total_records = 0
        total_violations = 0

        for model_name, Model in sorted(models_to_check.items()):
            # Only check models that inherit BaseModel envelope fields
            if not hasattr(Model, 'metadata'):
                continue

            records = Model.objects.all()[:limit]
            model_violations = 0

            for record in records:
                violations = validate_record_envelopes(record)
                if violations:
                    model_violations += len(violations)
                    for v in violations:
                        if fix:
                            self._fix_record_violation(record, v)
                            icon = self.style.SUCCESS('  FIXED')
                        else:
                            icon = self.style.ERROR('  FAIL')
                        self.stdout.write(
                            f"{icon} {v['message']}"
                        )
                total_records += 1

            total_violations += model_violations
            status = self.style.SUCCESS('OK') if model_violations == 0 else self.style.ERROR(f'{model_violations} violations')
            self.stdout.write(f"  {model_name}: {min(len(records), limit)} records — {status}")

        self.stdout.write(f"\nRecords checked: {total_records}")
        self.stdout.write(f"Total violations: {total_violations}")

    def _fix_record_violation(self, record, violation):
        """Fix a single record envelope violation."""
        import json
        field = violation['field']
        fix_type = violation.get('fix', '')

        if fix_type == 'set_default':
            defaults = {
                'metadata': {},
                'refs': {'links': {}, 'tags': [], 'keywords': [], 'categories': []},
                'prefs': {'userdefined': {}},
                'comments': {'general': {'public': [], 'process': [], 'foreign': []}, 'records': {}},
                'config': {},
            }
            setattr(record, field, defaults.get(field, {}))
            record.save(update_fields=[field, 'dt_modified'])

        elif fix_type == 'parse_or_default':
            value = getattr(record, field)
            try:
                parsed = json.loads(value)
                if isinstance(parsed, dict):
                    setattr(record, field, parsed)
                else:
                    setattr(record, field, {})
            except (json.JSONDecodeError, TypeError):
                setattr(record, field, {})
            record.save(update_fields=[field, 'dt_modified'])
