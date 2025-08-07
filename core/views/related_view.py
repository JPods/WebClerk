from typing import Dict, List
from core.models import Contact, Action
#Order, Item
from communications.models import Phone, Email, Address, Domain
from django.http import JsonResponse
from django.views import View

RELATED_TABLES: Dict[str, List[str]] = {
    #'customers': ['contacts', 'orders'],
    'contacts': ['phones', 'emails', 'addresses', 'actions', 'domains'],
    #'orders': ['items', 'payments', 'shipments'],
    #'items': ['categories', 'suppliers'],
    # Add more as needed
}

RELATED_MODELS: Dict[str, List[type]] = {
    'contacts': [Phone, Email, Address, Domain, Action],
    #'orders': [Item],
    # etc.
}

# Loops through all related models for the given parent table.
# Dynamically builds the foreign key filter (e.g., contact_id=..., order_id=...).
# Returns a dictionary with each related model’s data as a list.

def get_related_data(parent_table: str, parent_id: int) -> dict:
    """
    Given a parent table name and parent id, return a dict of related records
    using the RELATED_MODELS mapping.
    """
    results = {}
    related_models = RELATED_MODELS.get(parent_table, [])
    for model in related_models:
        # Assumes all related models have a ForeignKey to the parent named 'contact_id', 'order_id', etc.
        # Build the filter key dynamically
        fk_field = f"{parent_table.rstrip('s')}_id"
        queryset = model.objects.filter(**{fk_field: parent_id})
        results[model.__name__.lower() + 's'] = list(queryset.values())
    return results

class RelatedDataView(View):
    def get(self, request):
        parent_table = request.GET.get('parent_table')
        parent_id = request.GET.get('parent_id')
        if not parent_table or not parent_id:
            return JsonResponse({'success': False, 'error': 'parent_table and parent_id required'}, status=400)
        data = get_related_data(parent_table, parent_id)
        return JsonResponse({'success': True, 'data': data})



