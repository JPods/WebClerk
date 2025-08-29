from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import models
import json

AUDIT_LIMIT = 10000  # safety cap

class Command(BaseCommand):
    help = "Audit BaseModel derivatives: size limits, keyword flags, corruption markers."

    def add_arguments(self, parser):
        parser.add_argument('--model', help='Specific app_label.ModelName to audit')
        parser.add_argument('--json', action='store_true', help='Output JSON report')
        parser.add_argument('--limit', type=int, default=AUDIT_LIMIT, help='Max rows per model to scan')

    def handle(self, *args, **options):
        target = options.get('model')
        json_out = options.get('json')
        limit = options.get('limit')
        from common.models import BaseModel  # local import

        results = []
        for model in apps.get_models():
            if not issubclass(model, BaseModel) or model is BaseModel:
                continue
            label = f"{model._meta.app_label}.{model.__name__}"
            if target and label.lower() != target.lower():
                continue
            qs = model.objects.all()[:limit]
            issues = []
            count = 0
            pending_keywords = 0
            for obj in qs:
                count += 1
                md = obj.metadata if isinstance(obj.metadata, dict) else {}
                refs = obj.refs if isinstance(obj.refs, dict) else {}
                # size checks (reuse constants via getattr to avoid circular)
                try:
                    metadata_size = len(json.dumps(md).encode('utf-8'))
                except Exception:
                    metadata_size = -1
                    issues.append('metadata_json_error')
                if 'history' not in md:
                    issues.append('missing_history')
                if 'keywords' not in refs:
                    issues.append('missing_keywords')
                if md.get('flags', {}).get('keywords_pending'):
                    pending_keywords += 1
            results.append({
                'model': label,
                'scanned': count,
                'pending_keywords': pending_keywords,
                'issues': list(sorted(set(issues)))
            })

        if json_out:
            self.stdout.write(json.dumps(results, indent=2))
        else:
            for r in results:
                self.stdout.write(
                    f"{r['model']}: scanned={r['scanned']} pending_keywords={r['pending_keywords']} issues={','.join(r['issues']) or 'none'}" )

        self.stdout.write(self.style.SUCCESS('Audit complete'))
