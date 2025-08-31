from django.core.management.base import BaseCommand
from django.apps import apps
import json


class Command(BaseCommand):
    help = "Validate OrgBase aspect JSON blobs against pydantic schemas (full snapshot validation)."

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=0, help='Limit number of org rows scanned (0 = all)')
        parser.add_argument('--ids', type=str, default='', help='Comma separated OrgBase ids to validate (overrides limit)')
        parser.add_argument('--json', action='store_true', help='Output JSON instead of human readable text')
        parser.add_argument('--fail-on-error', action='store_true', help='Exit with code 1 if any invalid aspects found')

    def handle(self, *args, **opts):
        OrgBase = apps.get_model('orgs', 'OrgBase')
        ids_opt = [int(i) for i in opts['ids'].split(',') if i.strip()] if opts['ids'] else []
        limit = opts['limit']
        qs = OrgBase.objects.all()
        if ids_opt:
            qs = qs.filter(id__in=ids_opt)
        elif limit:
            qs = qs.order_by('id')[:limit]
        rows = list(qs)
        total = len(rows)
        valid = 0
        invalid = []
        for org in rows:
            ok, errors = org.validate_aspects()  # type: ignore[attr-defined]
            if ok:
                valid += 1
            else:
                invalid.append({'id': org.id, 'errors': errors})  # type: ignore[attr-defined]
        summary = {
            'total_scanned': total,
            'valid': valid,
            'invalid': len(invalid),
        }
        if opts['json']:
            self.stdout.write(json.dumps({'summary': summary, 'invalid_details': invalid}, indent=2))
        else:
            self.stdout.write(f"OrgBase aspect validation: scanned={total} valid={valid} invalid={len(invalid)}")
            for item in invalid[:50]:  # safety cap
                self.stdout.write(f" - id={item['id']} errors={item['errors']}")
            if len(invalid) > 50:
                self.stdout.write(f"   ... {len(invalid)-50} more invalid rows not displayed")
        if invalid and opts['fail-on-error']:
            # Non-zero exit signals CI failure.
            raise SystemExit(1)
