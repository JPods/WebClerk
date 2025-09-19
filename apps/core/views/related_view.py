# path: apps/core/views/related_view.py
from typing import Dict, List, Optional, Any
from django.http import JsonResponse
from django.views import View
from django.apps import apps
from django.core.paginator import Paginator, EmptyPage
import json
from apps.core.services.view_edit_access import get_view_edit_fields
from apps.core.services.wcapi_registry import normalize_table_key, ALLOWED_TABLE_KEYS, to_model_name

RELATED_TABLES: Dict[str, List[str]] = {
    # 'addresses' retained for backward compatibility (maps to Location model)
    'contacts': ['phones', 'emails', 'addresses', 'locations', 'actions', 'domains', 'sales_orders', 'orders', 'orgs'],
    'orgs': ['contacts', 'domains', 'locations'],  # basic reverse sets
    'sales_orders': ['contacts', 'orgs', 'customers', 'sales_order_lines'],  # canonical new naming
    'invoices': ['contacts', 'orgs', 'customers', 'invoice_lines'],
    'purchase_orders': ['contacts', 'orgs', 'vendors', 'purchase_order_lines'],
    'proposals': ['contacts', 'orgs', 'customers', 'proposal_line'],
    'orders': ['contacts', 'orgs', 'orderlines'],  # legacy naming (mapped to same models)
}

def get_related_data(
    table_key: str,
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
        'sales_orders': ('transactions', 'SalesOrder'),
        'sales_order_lines': ('transactions', 'SalesOrderLine'),
        'orders': ('transactions', 'SalesOrder'),  # legacy alias
        'orgs': ('orgs', 'OrgBase'),
        'customers': ('orgs', 'Customer'),
        'vendors': ('orgs', 'Vendor'),
        'contacts': ('core', 'Contact'),
        'invoices': ('transactions', 'Invoice'),
        'invoice_lines': ('transactions', 'InvoiceLine'),
        'purchase_orders': ('transactions', 'PurchaseOrder'),
        'purchase_order_lines': ('transactions', 'PurchaseOrderLine'),
        'proposal_line': ('transactions', 'ProposalLine'),
        'proposals': ('transactions', 'Proposal'),

    }

    tables_dict = related_tables_dict if related_tables_dict is not None else RELATED_TABLES

    print(f"get_related_data called with model/table_key={table_key}, id={id}")
    print(f"related_tables_dict={related_tables_dict}, pagination={pagination}")

    # Optional forward-ref hydrate (headers and contacts authoritative for some buckets):
    if table_key in ('contacts', 'sales_orders', 'orders', 'invoices', 'purchase_orders', 'proposals'):
        try:
            model_lookup = {
                'contacts': ('core', 'Contact'),
                'sales_orders': ('transactions', 'SalesOrder'),
                'invoices': ('transactions', 'Invoice'),
                'purchase_orders': ('transactions', 'PurchaseOrder'),
                'proposals': ('transactions', 'Proposal'),
                'orders': ('transactions', 'SalesOrder'),
            }
            app_label, model_name = model_lookup[table_key]
            base_model = apps.get_model(app_label, model_name)
            base_obj = base_model.objects.filter(id=id).only('refs').first()
        except Exception as e:  # pragma: no cover - defensive
            base_obj = None
            errors[f'{table_key}_fetch'] = str(e)
        if base_obj and getattr(base_obj, 'refs', None):
            raw_links = (base_obj.refs or {}).get('links', {})  # type: ignore[attr-defined]
            # Normalize singular/alias keys to canonical buckets for consistency
            links = dict(raw_links)
            # common singular to plural
            if 'item' in raw_links and 'items' not in links:
                links['items'] = raw_links['item']
            if 'contact' in raw_links and 'contacts' not in links:
                links['contacts'] = raw_links['contact']
            if 'address' in raw_links and 'addresses' not in links:
                links['addresses'] = raw_links['address']
            if 'phone' in raw_links and 'phones' not in links:
                links['phones'] = raw_links['phone']
            if 'email' in raw_links and 'emails' not in links:
                links['emails'] = raw_links['email']
            if 'vendor' in raw_links and 'vendors' not in links:
                links['vendors'] = raw_links['vendor']
            # Line bucket aliases
            if 'sales_order_line' in raw_links and 'sales_order_lines' not in links:
                links['sales_order_lines'] = raw_links['sales_order_line']
            if 'invoice_line' in raw_links and 'invoice_lines' not in links:
                links['invoice_lines'] = raw_links['invoice_line']
            if 'purchase_order_line' in raw_links and 'purchase_order_lines' not in links:
                links['purchase_order_lines'] = raw_links['purchase_order_line']
            if 'proposal_lin' in raw_links and 'proposal_line' not in links:
                links['proposal_line'] = raw_links['proposal_lin']
            forward_models = {
                'emails': ('communications', 'Email'),
                'phones': ('communications', 'Phone'),
                'locations': ('communications', 'Location'),
                'addresses': ('communications', 'Location'),
                'domains': ('communications', 'Domain'),
                'actions': ('core', 'Action'),
                'sales_orders': ('transactions', 'SalesOrder'),  # for a contact -> sales_orders
                'invoices': ('transactions', 'Invoice'),
                'purchase_orders': ('transactions', 'PurchaseOrder'),
                'proposals': ('transactions', 'Proposal'),
                'orders': ('transactions', 'SalesOrder'),  # legacy
                'orgs': ('orgs', 'OrgBase'),
                'customers': ('orgs', 'Customer'),
                'vendors': ('orgs', 'Vendor'),
                # Accept forward line links too (optional; reverse by parent_id already handled elsewhere)
                'sales_order_lines': ('transactions', 'SalesOrderLine'),
                'invoice_lines': ('transactions', 'InvoiceLine'),
                'purchase_order_lines': ('transactions', 'PurchaseOrderLine'),
                'proposal_line': ('transactions', 'ProposalLine'),
                'contacts': ('core', 'Contact'),  # for an order -> contacts aggregated via seeding
            }
            # Helper: flatten a heterogeneous list of ids or dicts into ordered id ints
            def _flatten_ids(raw_list: Any) -> list[int]:
                flat: list[int] = []
                if not isinstance(raw_list, list):
                    return flat
                for elem in raw_list:
                    if isinstance(elem, int):
                        flat.append(elem)
                    elif isinstance(elem, dict):
                        # If elem has an 'id' key, prefer it; else take any int values
                        if 'id' in elem and isinstance(elem['id'], int):
                            flat.append(elem['id'])
                        else:
                            for v in elem.values():
                                if isinstance(v, int):
                                    flat.append(v)
                    # silently ignore other types
                return flat
            for bucket, (app_label, model_name) in forward_models.items():
                raw = links.get(bucket) or []
                id_list = _flatten_ids(raw)
                if not id_list:
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

    for related_table in tables_dict.get(table_key, []):
        print(f"Processing related_table: {related_table}")
        if related_table in related_models:
            app_label, model_name = related_models[related_table]
            print(f"Using model: {app_label}.{model_name}")
            try:
                # If this bucket was already hydrated via forward refs above,
                # skip running a reciprocal queryset to avoid overwriting it.
                if related_table in related:
                    print(f"Skipping {related_table} - already hydrated via forward refs")
                    continue
                # Skip reciprocal query if we already hydrated via forward refs for this bucket
                if table_key == 'contacts' and (related_table == 'addresses' and 'locations' in related or related_table in related):
                    continue
                model = apps.get_model(app_label, model_name)
                # Reciprocal filter logic:
                if table_key == 'contacts':
                    queryset = model.objects.none()  # forward already hydrated
                elif table_key in ('sales_orders', 'orders', 'invoices', 'purchase_orders') and related_table in ('contacts', 'orgs', 'customers', 'vendors'):
                    queryset = model.objects.none()  # forward already hydrated
                elif table_key in ('sales_orders', 'orders') and related_table in ('sales_order_lines', 'orderlines'):
                    # child lines by parent id
                    queryset = model.objects.filter(parent_id=id)
                elif table_key == 'invoices' and related_table == 'invoice_lines':
                    queryset = model.objects.filter(parent_id=id)
                elif table_key == 'purchase_orders' and related_table == 'purchase_order_lines':
                    queryset = model.objects.filter(parent_id=id)
                elif table_key == 'proposals' and related_table == 'proposal_line':
                    queryset = model.objects.filter(parent_id=id)
                elif table_key == 'orgs' and related_table == 'contacts':
                    # contacts forward links contain org ids in refs.links.orgs
                    contact_model = apps.get_model('core', 'Contact')
                    queryset = contact_model.objects.filter(refs__links__orgs__contains=[id])
                else:
                    queryset = model.objects.filter(**{f"refs__links__{table_key}__contains": [id]})
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
            # Accept model_name (singular)
            raw_name = body.get('model_name')
            table_key = normalize_table_key(raw_name) if raw_name else None
            record_id = body.get('id')
            related_tables_dict = body.get('related_tables_dict')  # Optional
            pagination = body.get('pagination')  # Optional
            # Enforce singular model_name usage
            if raw_name and raw_name.strip().lower() in ALLOWED_TABLE_KEYS:
                expected = to_model_name(normalize_table_key(raw_name))
                return JsonResponse({'success': False, 'error': f"Use singular model_name='{expected}'"}, status=400)
            if not table_key or not record_id:
                return JsonResponse({'success': False, 'error': 'model_name and id are required'}, status=400)
            result = get_related_data(
                table_key,
                int(record_id),
                related_tables_dict=related_tables_dict,
                pagination=pagination
            )
            print("Returning related data:", result)
            return JsonResponse({'success': True, 'related': result['related'], 'errors': result['errors']})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    def get(self, request):
        raw_name = request.GET.get('model_name')
        table_key = normalize_table_key(raw_name) if raw_name else None
        record_id = request.GET.get('id')
        related_tables_dict = request.GET.get('related_tables_dict')
        pagination = request.GET.get('pagination')
        # Enforce singular model_name usage
        if raw_name and raw_name.strip().lower() in ALLOWED_TABLE_KEYS:
            expected = to_model_name(normalize_table_key(raw_name))
            return JsonResponse({'success': False, 'error': f"Use singular model_name='{expected}'"}, status=400)
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
        if not table_key or not record_id:
            return JsonResponse({'success': False, 'error': 'model_name and id are required'}, status=400)
        try:
            result = get_related_data(
                table_key,
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
        raw_name = request.GET.get('model_name')
        table_key = normalize_table_key(raw_name) if raw_name else None
        record_id = request.GET.get('id')
        # Enforce singular model_name usage
        if raw_name and raw_name.strip().lower() in ALLOWED_TABLE_KEYS:
            expected = to_model_name(normalize_table_key(raw_name))
            return JsonResponse({'success': False, 'error': f"Use singular model_name='{expected}'"}, status=400)
        if not table_key or not record_id:
            return JsonResponse({'success': False, 'error': 'model_name and id are required'}, status=400)
        try:
            result = get_related_data(table_key, int(record_id))
            user_role = getattr(request.user, 'role', 'PUBLIC')
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