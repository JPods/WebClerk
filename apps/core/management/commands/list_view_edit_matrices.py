from django.core.management.base import BaseCommand
from apps.core.models.setting import Setting
from django.utils import timezone
import json

class Command(BaseCommand):
    help = "List active view_edit matrices grouped by table_name"

    def add_arguments(self, parser):
        parser.add_argument('--table', dest='table', help='Filter by table_name (optional)')
        parser.add_argument('--role', dest='role', help='Filter to show only specific role rules (optional)')
        parser.add_argument('--pretty', action='store_true', help='Pretty print JSON')

    def handle(self, *args, **options):
        table = options.get('table')
        role = options.get('role')
        pretty = options.get('pretty')
        qs = Setting.objects.filter(purpose='view_edit', is_active=True)
        if table:
            qs = qs.filter(table_name=table)
        qs = qs.order_by('table_name', '-modified_dt')

        grouped = {}
        for s in qs:
            grouped.setdefault(s.table_name, {'id': s.id, 'modified_dt': s.modified_dt, 'data': s.data or {}})

        if role:
            # Filter each matrix to only requested role (case-insensitive)
            role_upper = role.upper()
            for tbl, meta in grouped.items():
                data = meta['data']
                selected = data.get(role_upper) or data.get('PUBLIC') or {}
                meta['data'] = {role_upper: selected}

        def serialize(obj):
            if hasattr(obj, 'isoformat'):
                return obj.isoformat()
            return obj

        if not grouped:
            self.stdout.write(self.style.WARNING('No active view_edit settings found.'))
            return

        if pretty:
            out = json.dumps(grouped, default=serialize, indent=2)
        else:
            out = json.dumps(grouped, default=serialize)
        self.stdout.write(out)
