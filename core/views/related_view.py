from typing import Dict, List
from core.models import Contact, Action
#Order, Item
from communications.models import Phone, Email, Address, Domain
from django.http import JsonResponse
from django.views import View
from django.apps import apps

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

def get_executable(name: str) -> str:
    """
    Given a table name, return the name of the executable function
    that can fetch related data for that table.
    """
    return f"get_related_{name}_data"


def get_one_from_many(related_table: str, parent_id: int) -> List[dict]:
    pass


# Loops through all related models for the given parent table.
# Dynamically builds the foreign key filter (e.g., contact_id=..., order_id=...).
# Returns a dictionary with each related model’s data as a list.

def get_related_data(parent_table: str, parent_id: int) -> dict:
    related = {}
    # Map each related key to (app_label, model_name)
    related_models = {
        'actions': ('core', 'Action'),
        'emails': ('communications', 'Email'),
        'phones': ('communications', 'Phone'),
        'addresses': ('communications', 'Address'),
        'domains': ('communications', 'Domain'),
    }
    for key, (app_label, model_name) in related_models.items():
        model = apps.get_model(app_label, model_name)
        model_fields = [f.name for f in model._meta.get_fields()]
        if 'contact_id' in model_fields:
            queryset = model.objects.filter(contact_id=parent_id)
        else:
            queryset = model.objects.filter(refs__links__contacts__contains=[int(parent_id)])
        related[key] = list(queryset.values())
    return related

class RelatedDataView(View):
    def get(self, request):
        parent_table = request.GET.get('parent_table')
        parent_id = request.GET.get('parent_id')
        if not parent_table or not parent_id:
            return JsonResponse({'success': False, 'error': 'parent_table and parent_id required'}, status=400)
        data = get_related_data(parent_table, parent_id)
        return JsonResponse({'success': True, 'data': data})



