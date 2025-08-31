from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import connection
import json
from typing import List, Tuple

THRESHOLDS = [0.30, 0.60, 0.75]

class Command(BaseCommand):
    help = "Report JSON envelope size utilization across BaseModel descendants (metadata/refs/prefs/comments)."

    def add_arguments(self, parser):
        parser.add_argument('--model', help='Restrict to app_label.ModelName (optional)')
        parser.add_argument('--limit', type=int, default=50, help='Max rows per model to sample (default 50)')
        parser.add_argument('--order', default='desc', choices=['asc','desc'], help='Order by utilization (desc default)')
        parser.add_argument('--field', default='metadata', choices=[
            'metadata','refs','prefs','comments',
            'contacts','locations','domains','phones','emails','relations','financial','docs','access','data','metrics','gl_accounts'
        ], help='Field to analyze (default metadata)')
        parser.add_argument('--json', action='store_true', help='Output JSON for machine aggregation')

    def handle(self, *args, **options):
        target_model = options['model']
        limit = options['limit']
        order = options['order']
        field = options['field']
        as_json = options['json']

        models_to_scan = []
        for model in apps.get_models():
            # Heuristic: look for feature_flags including 'core' and field attr
            if hasattr(model, 'feature_flags') and 'core' in getattr(model, 'feature_flags') and hasattr(model, field):
                if target_model:
                    full_name = f"{model._meta.app_label}.{model.__name__}"  # type: ignore[attr-defined]
                    if full_name.lower() != target_model.lower():
                        continue
                models_to_scan.append(model)

        if not models_to_scan:
            self.stdout.write(self.style.WARNING('No matching models found.'))
            return

        report = []
        for model in models_to_scan:
            table = model._meta.db_table  # type: ignore[attr-defined]
            max_size = _max_size_for_field(field)
            with connection.cursor() as cur:
                # size in bytes using PG octet_length(jsonb::text)
                cur.execute(f"""
                    SELECT id, octet_length({field}::text) AS size_bytes
                    FROM {table}
                    WHERE {field} IS NOT NULL
                    ORDER BY size_bytes {'DESC' if order=='desc' else 'ASC'}
                    LIMIT %s
                """, [limit])
                rows: List[Tuple[int,int]] = cur.fetchall()
            sizes = [r[1] for r in rows]
            if not sizes:
                continue
            max_seen = max(sizes)
            avg = sum(sizes)/len(sizes)
            utilization = max_seen / max_size if max_size else 0
            threshold_cross = [t for t in THRESHOLDS if max_seen >= max_size * t]
            entry = {
                'model': f"{model._meta.app_label}.{model.__name__}",  # type: ignore[attr-defined]
                'field': field,
                'rows_sampled': len(sizes),
                'max_bytes': max_seen,
                'avg_bytes': int(avg),
                'max_size_cap': max_size,
                'utilization_pct': round(utilization*100,1),
                'crossed_thresholds': threshold_cross,
            }
            report.append(entry)

        if as_json:
            self.stdout.write(json.dumps(report, indent=2))
        else:
            for r in report:
                self.stdout.write(
                    f"{r['model']}.{r['field']}: max={r['max_bytes']}B avg={r['avg_bytes']}B cap={r['max_size_cap']} ({r['utilization_pct']}%) thresholds={','.join(str(int(t*100))+'%' for t in r['crossed_thresholds'])}"  # noqa: E501
                )


def _max_size_for_field(field: str) -> int:
    from common import models as common_models  # lazy import
    # Reuse existing caps for core envelopes; provide heuristic caps for org aspects.
    ORG_DEFAULT_CAP = 65536  # 64KB heuristic soft governance target per aspect
    return {
        'metadata': common_models.MAX_METADATA_SIZE,
        'refs': common_models.MAX_REFS_SIZE,
        'prefs': common_models.MAX_PREFS_SIZE,
        'comments': common_models.MAX_METADATA_SIZE,
        # OrgBase aspect heuristic caps (can later promote to constants on model)
        'contacts': ORG_DEFAULT_CAP,
        'locations': ORG_DEFAULT_CAP,
        'domains': 16384,     # typically tiny list
        'phones': 8192,
        'emails': 16384,
        'relations': 32768,
        'financial': 65536,
        'docs': 32768,
        'access': 8192,
        'data': 32768,
        'metrics': 65536,
        'gl_accounts': 16384,
    }.get(field, ORG_DEFAULT_CAP)
