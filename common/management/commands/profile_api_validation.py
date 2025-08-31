from django.core.management.base import BaseCommand
from django.apps import apps
import time
import statistics
import json


def percentile(data, pct):
    if not data:
        return 0.0
    k = (len(data) - 1) * pct
    f = int(k)
    c = min(f + 1, len(data) - 1)
    if f == c:
        return float(data[f])
    d0 = data[f] * (c - k)
    d1 = data[c] * (k - f)
    return float(d0 + d1)


class Command(BaseCommand):
    help = (
        "Profile api_validate_payload latency for BaseModel descendants. "
        "Executes N iterations per model with empty payload (or sample payload JSON if provided)."
    )

    def add_arguments(self, parser):
        parser.add_argument('--iterations', type=int, default=50, help='Iterations per model (default 50)')
        parser.add_argument('--app', type=str, default='', help='Filter by app label')
        parser.add_argument('--model', type=str, default='', help='Filter by model class name (case sensitive)')
        parser.add_argument('--json', action='store_true', help='JSON output')

    def handle(self, *args, **options):
        iters = max(1, options['iterations'])
        target_app = options.get('app') or ''
        target_model = options.get('model') or ''
        rows = []
        try:
            from common.models import BaseModel  # local import
        except Exception as e:  # pragma: no cover
            self.stderr.write(f"Import error BaseModel: {e}")
            return
        for model in apps.get_models():
            if not issubclass(model, BaseModel) or model is BaseModel:
                continue
            if target_app and model._meta.app_label != target_app:  # type: ignore[attr-defined]
                continue
            if target_model and model.__name__ != target_model:
                continue
            if not hasattr(model, 'api_validate_payload'):
                continue
            times = []
            for _ in range(iters):
                try:
                    inst = model()
                except Exception:
                    break  # cannot instantiate for profiling
                start = time.perf_counter()
                try:
                    inst.api_validate_payload({}, False)  # type: ignore[attr-defined]
                except Exception:
                    pass
                end = time.perf_counter()
                times.append((end - start) * 1000.0)  # ms
            if not times:
                continue
            times.sort()
            row = {
                'app': model._meta.app_label,  # type: ignore[attr-defined]
                'model': model.__name__,
                'iterations': len(times),
                'avg_ms': statistics.fmean(times),
                'p95_ms': percentile(times, 0.95),
                'max_ms': max(times),
                'min_ms': min(times),
                'custom': not getattr(model.api_validate_payload, '__qualname__', '').startswith('BaseModel.'),  # type: ignore[attr-defined]
            }
            rows.append(row)
        if options.get('json'):
            self.stdout.write(json.dumps(rows, indent=2))
            return
        if not rows:
            self.stdout.write('No models profiled.')
            return
        header = f"{'App':15} {'Model':30} avg_ms  p95_ms  max_ms  custom"
        self.stdout.write(header)
        self.stdout.write('-' * len(header))
        for r in sorted(rows, key=lambda x: (x['app'], x['model'])):
            self.stdout.write(
                f"{r['app'][:15]:15} {r['model'][:30]:30} {r['avg_ms']:.3f} {r['p95_ms']:.3f} {r['max_ms']:.3f} {str(r['custom']):6}"
            )
