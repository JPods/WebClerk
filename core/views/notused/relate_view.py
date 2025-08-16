from typing import Dict, List
from django.http import JsonResponse
from django.views import View
from django.apps import apps
from core.services.view_edit_access import get_view_edit_fields

# Define which related tables to fetch for each parent table
RELATED_TABLES: Dict[str, List[str]] = {
    'contacts': ['phones', 'emails', 'addresses', 'actions', 'domains'],
    # Add more as needed
}

# Map each related key to (app_label, model_name)
RELATED_MODELS: Dict[str, tuple] = {
    'actions': ('core', 'Action'),
    'emails': ('communications', 'Email'),
    'phones': ('communications', 'Phone'),
    'addresses': ('communications', 'Location'),
    'domains': ('communications', 'Domain'),
}

def get_related_data(parent_table: str, parent_id: int) -> dict:
    """
    Fetches all related data for a given parent record (e.g., contact).
    Returns a dictionary with each related model’s data as a list.
    """
    data = {}
    for related_table in RELATED_TABLES.get(parent_table, []):
        if related_table in RELATED_MODELS:
            app_label, model_name = RELATED_MODELS[related_table]
            model = apps.get_model(app_label, model_name)
            # Try to filter by <parent_table>_id (e.g., contact_id)
            fk_field = f"{parent_table.rstrip('s')}_id"
            if fk_field in [f.name for f in model._meta.get_fields()]:
                queryset = model.objects.filter(**{fk_field: parent_id})
            else:
                # Fallback: try to find by refs or other logic if needed
                queryset = model.objects.none()
            data[related_table] = list(queryset.values())
        else:
            data[related_table] = []
    return data

def filter_fields(record, allowed_fields):
    """Return a dict with only the allowed fields from record."""
    return {k: v for k, v in record.items() if k in allowed_fields}

class RelatedDataView(View):
    def get(self, request):
        parent_table = request.GET.get('parent_table')
        parent_id = request.GET.get('parent_id')
        user_role = request.user.role  # or however you get the user's role
        if not parent_table or not parent_id:
            return JsonResponse({'success': False, 'error': 'parent_table and parent_id required'}, status=400)
        try:
            parent_id = int(parent_id)
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Invalid parent_id'}, status=400)
        data = get_related_data(parent_table, parent_id)
        # QQQ add table_name to every data
        for key in data:
            for item in data[key]:
                item['table_name'] = key

        filtered_related = {}
        for related_table, records in data.items():
            allowed = get_view_edit_fields(related_table, user_role, "view")
            filtered_related[related_table] = [
                filter_fields(r, allowed) for r in records
            ]

        return JsonResponse({'success': True, 'data': filtered_related})