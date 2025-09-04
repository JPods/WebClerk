# path: apps/core/views/related_view.py
from typing import Dict, List, Optional, Any
from django.http import JsonResponse
from django.views import View
from django.apps import apps
from django.core.paginator import Paginator, EmptyPage
import json
from apps.core.services.view_edit_access import get_view_edit_fields

RELATED_TABLES: Dict[str, List[str]] = {
    # 'addresses' retained for backward compatibility (maps to Location model)
    'contacts': ['phones', 'emails', 'addresses', 'locations', 'actions', 'domains', 'orders', 'orgs'],
    'orgs': ['contacts', 'domains', 'locations'],  # basic reverse sets
    'orders': ['contacts', 'orgs', 'orderlines'],  # expose forward-linked contacts/org + child order lines
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
        'addresses': ('communications', 'Location'),
        'locations': ('communications', 'Location'),
        'domains': ('communications', 'Domain'),
        'actions': ('core', 'Action'),
        'orders': ('transactions', 'Order'),
        'orgs': ('orgs', 'OrgBase'),
        'contacts': ('core', 'Contact'),
        'orderlines': ('transactions', 'OrderLine'),
    }

    tables_dict = related_tables_dict if related_tables_dict is not None else RELATED_TABLES

    print(f"get_related_data called with table_name={table_name}, id={id}")
    print(f"related_tables_dict={related_tables_dict}, pagination={pagination}")

    # Optional forward-ref hydrate (contacts & orders authoritative for some buckets):
    if table_name in ('contacts', 'orders'):
        try:
            model_lookup = {
                'contacts': ('core', 'Contact'),
                'orders': ('transactions', 'Order'),
            }
            app_label, model_name = model_lookup[table_name]
            base_model = apps.get_model(app_label, model_name)
            base_obj = base_model.objects.filter(id=id).only('refs').first()
        except Exception as e:  # pragma: no cover - defensive
            base_obj = None
            errors[f'{table_name}_fetch'] = str(e)
        if base_obj and getattr(base_obj, 'refs', None):
            links = (base_obj.refs or {}).get('links', {})  # type: ignore[attr-defined]
            forward_models = {
                'emails': ('communications', 'Email'),
                'phones': ('communications', 'Phone'),
                'locations': ('communications', 'Location'),
                'domains': ('communications', 'Domain'),
                'actions': ('core', 'Action'),
                'orders': ('transactions', 'Order'),  # for a contact -> orders
                'orgs': ('orgs', 'OrgBase'),
                'contacts': ('core', 'Contact'),  # for an order -> contacts aggregated via seeding
            }
            for bucket, (app_label, model_name) in forward_models.items():
                id_list = links.get(bucket) or []
                if not isinstance(id_list, list) or not id_list:
                    continue
                try:
                    model = apps.get_model(app_label, model_name)
                    qs = model.objects.filter(id__in=id_list)
                    # preserve original ordering from forward refs
                    obj_map = {getattr(o, 'id', None): o for o in qs if getattr(o, 'id', None) is not None}  # type: ignore[attr-defined]
                    ordered = [obj_map[i] for i in id_list if i in obj_map]
                    related[bucket] = [getattr(o, 'to_dict', lambda: o.__dict__)() if hasattr(o, 'to_dict') else {k: v for k, v in o.__dict__.items() if not k.startswith('_')} for o in ordered]
                except Exception as e:  # pragma: no cover
                    errors[bucket] = f"forward_ref_error: {e}"

    for related_table in tables_dict.get(table_name, []):
        print(f"Processing related_table: {related_table}")
        if related_table in related_models:
            app_label, model_name = related_models[related_table]
            print(f"Using model: {app_label}.{model_name}")
            try:
                # Skip reciprocal query if we already hydrated via forward refs for this bucket
                if table_name == 'contacts' and (related_table == 'addresses' and 'locations' in related or related_table in related):
                    continue
                model = apps.get_model(app_label, model_name)
                # Reciprocal filter logic:
                if table_name == 'contacts':
                    queryset = model.objects.none()  # forward already hydrated
                elif table_name == 'orders' and related_table in ('contacts', 'orgs'):
                    queryset = model.objects.none()  # forward already hydrated
                elif table_name == 'orders' and related_table == 'orderlines':
                    # child lines by parent id
                    queryset = model.objects.filter(parent_id=id)
                elif table_name == 'orgs' and related_table == 'contacts':
                    # contacts forward links contain org ids in refs.links.orgs
                    contact_model = apps.get_model('core', 'Contact')
                    queryset = contact_model.objects.filter(refs__links__orgs__contains=[id])
                else:
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
            user_role = request.user.role  # or however you get the user's role
            filtered = filter_related_data(result['related'], user_role)
            return JsonResponse({'success': True, 'data': filtered, 'errors': result['errors']})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

def filter_safe_fields(record, allowed_fields):
    safe = {}
    for k, v in record.items():
        if k == "uuid":
            continue
        if k.startswith("dt_"):
            continue  # Or convert to string if you want to display
        if k in allowed_fields:
            safe[k] = v
    return safe

def filter_related_data(related_data, user_role):
    filtered_related = {}
    for related_table, records in related_data.items():
        allowed = get_view_edit_fields(related_table, user_role, "view")
        filtered_related[related_table] = [
            filter_safe_fields(r, allowed) for r in records
        ]
    return filtered_related