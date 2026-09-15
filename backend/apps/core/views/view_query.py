"""
ViewQueryView — query PostgreSQL VIEWs directly for DataBrowser display.

Registered VIEWs are defined in the 'wc-views' Setting.
Returns paginated results with standard sort/filter support.
Read-only — all writes go through the source model.
"""
import json
import logging
from django.db import connection
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from common.api_responses import api_response

logger = logging.getLogger('console')

# Safe sort/filter characters — prevent SQL injection
SAFE_FIELD = set('abcdefghijklmnopqrstuvwxyz_0123456789')


def _safe_field(name: str) -> bool:
    """Only allow lowercase alphanumeric + underscore field names."""
    return bool(name) and all(c in SAFE_FIELD for c in name)


def _get_view_config(view_name: str) -> dict | None:
    """Look up a VIEW definition from the wc-views Setting."""
    from apps.core.models import Setting
    try:
        s = Setting.objects.filter(ida='wc-views', is_active=True).first()
        if not s or not isinstance(s.config, dict):
            return None
        views = s.config.get('views', {})
        return views.get(view_name)
    except Exception:
        return None


def _get_view_columns(view_name: str) -> list[str]:
    """Get column names from the VIEW via information_schema."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = %s ORDER BY ordinal_position",
            [view_name]
        )
        return [row[0] for row in cursor.fetchall()]


class ViewQueryView(APIView):
    """Query a registered PostgreSQL VIEW with pagination, sort, filter."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        view_name = request.query_params.get('view', '').strip().lower()
        if not view_name or not _safe_field(view_name):
            return api_response(error={'code': 'invalid_view', 'details': 'Missing or invalid view name'}, status_code=400)

        # Check registry
        config = _get_view_config(view_name)
        if not config:
            return api_response(error={'code': 'unknown_view', 'details': f'View "{view_name}" not registered in wc-views'}, status_code=404)

        # Get actual columns from the VIEW
        try:
            columns = _get_view_columns(view_name)
        except Exception as e:
            return api_response(error={'code': 'view_error', 'details': str(e)}, status_code=500)

        if not columns:
            return api_response(error={'code': 'view_error', 'details': f'View "{view_name}" has no columns or does not exist'}, status_code=404)

        # Pagination
        limit = min(int(request.query_params.get('limit', 200)), 1000)
        offset = int(request.query_params.get('offset', 0))

        # Sort
        sort_field = request.query_params.get('sort', config.get('default_sort', 'id'))
        sort_dir = request.query_params.get('dir', 'asc').upper()
        if sort_dir not in ('ASC', 'DESC'):
            sort_dir = 'ASC'
        if not _safe_field(sort_field) or sort_field not in columns:
            sort_field = 'id' if 'id' in columns else columns[0]

        # Search/keyword filter
        keyword = request.query_params.get('keyword', '').strip()

        # Build query
        where_clauses = []
        params = []

        if keyword:
            # Search across text columns
            text_cols = [c for c in columns if c in ('title', 'status', 'purpose', 'detail_text', 'source_model', 'icon')]
            if text_cols:
                or_parts = [f"CAST({c} AS TEXT) ILIKE %s" for c in text_cols]
                where_clauses.append(f"({' OR '.join(or_parts)})")
                params.extend([f'%{keyword}%'] * len(text_cols))

        # Simple field filters from query params
        for key, val in request.query_params.items():
            if key in ('view', 'limit', 'offset', 'sort', 'dir', 'keyword', 'format'):
                continue
            # Support field=value and field__gt, field__lt etc.
            parts = key.split('__')
            field = parts[0]
            if not _safe_field(field) or field not in columns:
                continue
            op = parts[1] if len(parts) > 1 else 'eq'
            if op == 'eq':
                where_clauses.append(f"{field} = %s")
                params.append(val)
            elif op == 'gt':
                where_clauses.append(f"{field} > %s")
                params.append(val)
            elif op == 'lt':
                where_clauses.append(f"{field} < %s")
                params.append(val)
            elif op == 'gte':
                where_clauses.append(f"{field} >= %s")
                params.append(val)
            elif op == 'lte':
                where_clauses.append(f"{field} <= %s")
                params.append(val)
            elif op == 'in':
                values = val.split(',')
                placeholders = ','.join(['%s'] * len(values))
                where_clauses.append(f"{field} IN ({placeholders})")
                params.extend(values)

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        # Count
        count_sql = f"SELECT COUNT(*) FROM {view_name} {where_sql}"
        # Data
        data_sql = f"SELECT * FROM {view_name} {where_sql} ORDER BY {sort_field} {sort_dir} LIMIT %s OFFSET %s"

        try:
            with connection.cursor() as cursor:
                cursor.execute(count_sql, params)
                total = cursor.fetchone()[0]

                cursor.execute(data_sql, params + [limit, offset])
                col_names = [desc[0] for desc in cursor.description]
                rows = [dict(zip(col_names, row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f'[ViewQuery] Error querying {view_name}: {e}')
            return api_response(error={'code': 'query_error', 'details': str(e)}, status_code=500)

        return api_response(data={
            'results': rows,
            'count': len(rows),
            'total': total,
            'limit': limit,
            'offset': offset,
            'view': view_name,
            'columns': columns,
            'config': config,
        })
