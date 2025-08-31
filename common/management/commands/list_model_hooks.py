from django.core.management.base import BaseCommand
from django.apps import apps
import json


class Command(BaseCommand):
    help = (
        "List BaseModel subclasses and whether each universal hook is overridden "
        "(custom) or still using the BaseModel default."
    )

    def add_arguments(self, parser):
        parser.add_argument('--app', type=str, default='', help='Filter to a single app label')
        parser.add_argument('--json', action='store_true', help='Output machine-readable JSON')

    def handle(self, *args, **options):
        target_app = options.get('app') or ''
        rows = []
        try:
            from common.models import BaseModel  # local import to avoid circulars
        except Exception as e:  # pragma: no cover - defensive
            self.stderr.write(f"Unable to import BaseModel: {e}")
            return
        for model in apps.get_models():
            if not issubclass(model, BaseModel) or model is BaseModel:
                continue
            if target_app and model._meta.app_label != target_app:  # type: ignore[attr-defined]
                continue
            def status(fn_name: str) -> str:
                fn = getattr(model, fn_name, None)
                if not fn:
                    return 'missing'
                qual = getattr(fn, '__qualname__', '')
                if qual.startswith('BaseModel.'):
                    return 'default'
                return 'custom'
            row = {
                'app': model._meta.app_label,  # type: ignore[attr-defined]
                'model': model.__name__,
                'pre_save_hook': status('pre_save_hook'),
                'api_validate_payload': status('api_validate_payload'),
                'post_save_hook': status('post_save_hook'),
            }
            rows.append(row)
        if options.get('json'):
            self.stdout.write(json.dumps(rows, indent=2))
            return
        # human table
        if not rows:
            self.stdout.write('No BaseModel subclasses found (or filtered out).')
            return
        header = f"{'App':15} {'Model':30} pre_save_hook  api_validate_payload  post_save_hook"
        self.stdout.write(header)
        self.stdout.write('-' * len(header))
        for r in sorted(rows, key=lambda x: (x['app'], x['model'])):
            self.stdout.write(
                f"{r['app'][:15]:15} {r['model'][:30]:30} {r['pre_save_hook'][:10]:13} {r['api_validate_payload'][:10]:20} {r['post_save_hook'][:10]:13}"
            )
