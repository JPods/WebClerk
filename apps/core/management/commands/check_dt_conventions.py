from __future__ import annotations

from django.core.management.base import BaseCommand
from common.dt_norm import scan_model_fields
import json

class Command(BaseCommand):
    help = "Scan all models for dt_ timestamp naming convention violations."

    def add_arguments(self, parser):  # pragma: no cover simple
        parser.add_argument('--json', action='store_true', help='Output JSON report')
        parser.add_argument('--fail-on-violations', action='store_true', help='Exit non-zero if violations found')

    def handle(self, *args, **options):  # pragma: no cover - simple IO
        violations = scan_model_fields()
        if options.get('json'):
            self.stdout.write(json.dumps([v.as_dict() for v in violations], indent=2))
        else:
            if not violations:
                self.stdout.write(self.style.SUCCESS('No dt_ naming violations found.'))
            else:
                self.stdout.write(self.style.WARNING(f"{len(violations)} dt_ naming violations:"))
                for v in violations:
                    sug = f" -> suggest: {v.suggested}" if v.suggested else ''
                    self.stdout.write(f"  {v.app_label}.{v.model}.{v.field} ({v.field_type}): {v.reason}{sug}")
        if violations and options.get('fail_on_violations'):
            raise SystemExit(1)
