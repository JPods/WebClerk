from typing import Dict, List, Optional, Any
from django.http import JsonResponse
from django.views import View
from django.apps import apps
from django.core.paginator import Paginator, EmptyPage
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json

RELATED_TABLES: Dict[str, List[str]] = {
    'contacts': ['phones', 'emails', 'addresses', 'actions', 'domains'],
}

def get_related_data(
    table_name: str,
    id: int,
    related_tables_dict: Optional[Dict[str, List[str]]] = None,
    pagination: Optional[Dict[str, Dict[str, int]]] = None
) -> dict:
    """
    Fetches all related data for a given contact, returning a single JSON object.
    related_tables_dict: Optional override for which related tables to use.
    pagination: Optional dict of {related_table: {'page': int, 'page_size': int}}
    """
    related = {}
    errors = {}
    related_models = {
        'phones': ('communications', 'Phone'),
        'emails': ('communications', 'Email'),
        'addresses': ('communications', 'Address'),
        'domains': ('communications', 'Domain'),
        'actions': ('core', 'Action'),
    }

    tables_dict = related_tables_dict if related_tables_dict is not None else RELATED_TABLES

    print(f"get_related_data called with table_name={table_name}, id={id}")
    print(f"related_tables_dict={related_tables_dict}, pagination={pagination}")

    for related_table in tables_dict.get(table_name, []):
        print(f"Processing related_table: {related_table}")
        if related_table in related_models:
            app_label, model_name = related_models[related_table]
            print(f"Using model: {app_label}.{model_name}")
            try:
                model = apps.get_model(app_label, model_name)
                queryset = model.objects.filter(**{f"refs__links__{table_name}__contains": [id]})
                print(f"Queryset count for {related_table}: {queryset.count()}")
                # Pagination support
                if pagination and related_table in pagination:
                    page = pagination[related_table].get('page', 1)
                    page_size = pagination[related_table].get('page_size', 20)
                    paginator = Paginator(queryset, page_size)
                    try:
                        page_obj = paginator.page(page)
                        related[related_table] = list(page_obj.object_list.values())
                        related[f"{related_table}_pagination"] = {
                            "page": page,
                            "page_size": page_size,
                            "num_pages": paginator.num_pages,
                            "count": paginator.count,
                        }
                    except EmptyPage:
                        related[related_table] = []
                        related[f"{related_table}_pagination"] = {
                            "page": page,
                            "page_size": page_size,
                            "num_pages": paginator.num_pages,
                            "count": paginator.count,
                            "error": "Page out of range"
                        }
                else:
                    related[related_table] = list(queryset.values())
            except Exception as e:
                print(f"Error processing {related_table}: {e}")
                related[related_table] = []
                errors[related_table] = str(e)
        else:
            print(f"Unknown related table: {related_table}")
            related[related_table] = []
            errors[related_table] = "Unknown related table"
    return {"related": related, "errors": errors}


class RelatedDataAdvancedView(View):
    """
    Django view for returning related data as JSON.
    """
    def post(self, request):
        try:
            body = json.loads(request.body.decode('utf-8'))
            table_name = body.get('table_name')
            record_id = body.get('id')
            related_tables_dict = body.get('related_tables_dict')  # Optional
            pagination = body.get('pagination')  # Optional
            if not table_name or not record_id:
                return JsonResponse({'success': False, 'error': 'table_name and id are required'}, status=400)
            result = get_related_data(
                table_name,
                int(record_id),
                related_tables_dict=related_tables_dict,
                pagination=pagination
            )
            print("Returning related data:", result)
            return JsonResponse({'success': True, 'related': result['related'], 'errors': result['errors']})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    def get(self, request):
        table_name = request.GET.get('table_name')
        record_id = request.GET.get('id')
        related_tables_dict = request.GET.get('related_tables_dict')
        pagination = request.GET.get('pagination')
        if related_tables_dict:
            try:
                related_tables_dict = json.loads(related_tables_dict)
            except Exception:
                related_tables_dict = None
        if pagination:
            try:
                pagination = json.loads(pagination)
            except Exception:
                pagination = None
        if not table_name or not record_id:
            return JsonResponse({'success': False, 'error': 'table_name and id are required'}, status=400)
        try:
            result = get_related_data(
                table_name,
                int(record_id),
                related_tables_dict=related_tables_dict,
                pagination=pagination
            )
            print("Returning related data:", result)
            return JsonResponse({'success': True, 'related': result['related'], 'errors': result['errors']})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

class RelatedDataView(View):
    def get(self, request):
        table_name = request.GET.get('table_name')
        record_id = request.GET.get('id')
        if not table_name or not record_id:
            return JsonResponse({'success': False, 'error': 'table_name and id are required'}, status=400)
        try:
            result = get_related_data(table_name, int(record_id))
            return JsonResponse({'success': True, 'related': result['related'], 'errors': result['errors']})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)