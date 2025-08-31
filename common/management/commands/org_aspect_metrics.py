from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import connection
from statistics import mean
import json

ASPECT_FIELDS = [
    'contacts','locations','domains','phones','emails','relations','financial','docs','connections','data','metrics','gl_accounts'
]

class Command(BaseCommand):
    help = "Report per-aspect item counts & estimated JSON sizes for OrgBase table."

    def add_arguments(self, parser):
        parser.add_argument('--json', action='store_true', help='Output JSON instead of text table')
        parser.add_argument('--limit', type=int, default=0, help='Limit number of org rows sampled (0 = all)')

    def handle(self, *args, **opts):
        from apps.orgs.models import OrgBase
        limit = opts['limit']
        qs = OrgBase.objects.all().only('id', *ASPECT_FIELDS)
        if limit:
            qs = qs[:limit]
        rows = list(qs)
        totals = {}
        per_org = []
        for org in rows:
            aspects = {}
            for f in ASPECT_FIELDS:
                val = getattr(org, f)
                count = len(val) if isinstance(val, list) else (len(val.keys()) if isinstance(val, dict) else 0)
                size_bytes = len(json.dumps(val).encode('utf-8')) if val is not None else 0
                aspects[f] = {'count': count, 'bytes': size_bytes}
                agg = totals.setdefault(f, {'counts': [], 'sizes': []})
                agg['counts'].append(count)
                agg['sizes'].append(size_bytes)
            per_org.append({'id': org.id, 'aspects': aspects})
        summary = {}
        for f, agg in totals.items():
            if not agg['counts']:
                continue
            summary[f] = {
                'orgs_with_data': sum(1 for c in agg['counts'] if c),
                'avg_count': round(mean(agg['counts']),2),
                'p95_count': _percentile(agg['counts'], 95),
                'max_count': max(agg['counts']),
                'avg_bytes': round(mean(agg['sizes']),1),
                'p95_bytes': _percentile(agg['sizes'], 95),
                'max_bytes': max(agg['sizes']),
            }
        output = {'total_orgs': len(rows), 'summary': summary}
        if opts['json']:
            self.stdout.write(json.dumps(output, indent=2))
        else:
            self.stdout.write(f"OrgBase aspect metrics (orgs sampled={len(rows)})")
            for f, data in sorted(summary.items()):
                self.stdout.write(
                    f"{f}: count(avg={data['avg_count']} p95={data['p95_count']} max={data['max_count']}) "
                    f"bytes(avg={data['avg_bytes']} p95={data['p95_bytes']} max={data['max_bytes']})"
                )


def _percentile(values, p):
    if not values:
        return 0
    vals = sorted(values)
    k = (len(vals)-1) * (p/100)
    f = int(k)
    c = min(f+1, len(vals)-1)
    if f == c:
        return vals[f]
    return vals[f] + (vals[c]-vals[f]) * (k-f)
