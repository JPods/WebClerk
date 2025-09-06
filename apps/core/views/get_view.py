# path: apps/core/views/get_view.py
from django.http import JsonResponse  # legacy (remove after full migration)
from rest_framework.views import APIView
from rest_framework import permissions
from django.apps import apps
from django.forms.models import model_to_dict
from apps.core.views.related_view import get_related_data
from apps.core.services.view_edit_access import filter_record_for_role
from common.api_responses import api_response

TABLE_APP_MAP = {
    'contacts': 'core',
    'actions': 'core',
    'settings': 'core',
    'templates': 'core',
    'pending': 'core',
    'emails': 'communications',
    'phones': 'communications',
    'locations': 'communications',
    'addresses': 'communications',  # legacy alias for locations
    'domains': 'communications',
    'documents': 'docs',
    'qas': 'docs',
    'tags': 'docs',
    'linkages': 'docs',
    # products
    'items': 'products',  # apps.products.models.item.Item
    # transactions
    'sales_orders': 'transactions',        # SalesOrder model
    'sales_order_lines': 'transactions',    # SalesOrderLine model (special-case name below)
    'proposals': 'transactions',
    'proposal_lines': 'transactions',
    'invoices': 'transactions',
    'invoice_lines': 'transactions',
    'purchase_orders': 'transactions',
    'purchase_order_lines': 'transactions',
    'work_orders': 'transactions',
    'work_order_lines': 'transactions',
    'requisitions': 'transactions',
    'requisition_lines': 'transactions',
    'purchase_receipts': 'transactions',
   
    # orgs
    'orgs': 'orgs',                        # maps to OrgBase model
    'customers': 'orgs',                   # maps to CustomerOrg model
    'vendors': 'orgs',                     # maps to VendorOrg model
    'reps': 'orgs',                        # maps to RepOrg model
    'employees': 'orgs',                   # maps to EmployeeOrg model
    'manufacturers': 'orgs',               # maps to ManufacturerOrg model
    # Add more as needed; prefer adding here to avoid broad app scan cost
}

class OpenReadOrAuthenticated(permissions.BasePermission):
    """Allow unauthenticated read/query when WCAPI_OPEN_READ enabled and JWT not forced."""
    def has_permission(self, request, view):  # pragma: no cover (simple gate)
        from django.conf import settings
        if request.method == 'GET':
            if getattr(settings, 'WCAPI_OPEN_READ', False) and not getattr(settings, 'WCAPI_JWT_ONLY', False):
                return True
        return bool(request.user and request.user.is_authenticated)


class WcapiGetView(APIView):
    """GET access with optional open-read dev mode (set WCAPI_OPEN_READ=1)."""
    permission_classes = [OpenReadOrAuthenticated]

    def _sanitize(self, value):  # pragma: no cover - straightforward
        """Recursively coerce non-JSON-serializable objects to primitives/strings.

        - Allowed primitives: None, bool, int, float, str
        - dict/list traversed
        - datetime/date converted to isoformat
        - other objects -> str(o)
        """
        import datetime, decimal
        from django.db import models as dj_models
        if value is None or isinstance(value, (bool, int, float, str)):
            return value
        if isinstance(value, (datetime.date, datetime.datetime)):
            return value.isoformat()
        if isinstance(value, decimal.Decimal):
            return float(value)
        if isinstance(value, dict):
            return {k: self._sanitize(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._sanitize(v) for v in value]
        if isinstance(value, dj_models.Model):  # collapse model ref to pk or string
            # prefer primary key if available
            pk = getattr(value, 'pk', None)
            return pk if pk is not None else str(value)
        return str(value)

    def get(self, request):  # noqa: C901 (simple flow)
        from django.conf import settings
        require_jwt = getattr(settings, 'WCAPI_JWT_ONLY', False)
        open_read = getattr(settings, 'WCAPI_OPEN_READ', False)
        is_jwt = bool(getattr(request, 'auth', None)) or request.META.get('HTTP_AUTHORIZATION','').startswith('Bearer ')
        if not request.user.is_authenticated and not open_read:
            return api_response(success=False, status_code=401, message='Authentication required', error={'code':'not_authenticated','details':'Authentication required'})
        if require_jwt and not is_jwt and not (open_read and not request.user.is_authenticated):
            return api_response(success=False, status_code=401, message='JWT required (missing Bearer token)', error={'code':'jwt_required','details':'JWT required (missing Bearer token)'})

        table_name = request.GET.get('table_name')
        record_id = request.GET.get('id')
        user_role = getattr(request.user, 'role', 'PUBLIC')
        if not table_name:
            return api_response(success=False, status_code=400, message='Missing table_name', error={'code':'missing_table_name','details':'Missing table_name'})
        app_label = TABLE_APP_MAP.get(table_name, 'core')
        # Basic plural -> ModelName heuristic with explicit special cases.
        if table_name == 'addresses':
            model_name = 'Location'  # legacy alias
        elif table_name in ('sales_order_lines', 'orderlines'):
            model_name = 'SalesOrderLine'
        elif table_name == 'orders':
            model_name = 'SalesOrder'
        elif table_name == 'proposals':
            model_name = 'Proposal'
        elif table_name == 'proposal_lines':
            model_name = 'ProposalLine'
        elif table_name == 'invoices':
            model_name = 'Invoice'
        elif table_name == 'invoice_lines':
            model_name = 'InvoiceLine'
        elif table_name == 'purchase_orders':
            model_name = 'PurchaseOrder'
        elif table_name == 'purchase_order_lines':
            model_name = 'PurchaseOrderLine'
        elif table_name == 'work_orders':
            model_name = 'Workorder'
        elif table_name == 'work_order_lines':
            model_name = 'WorkorderLine'
        elif table_name == 'requisitions':
            model_name = 'Requisition'
        elif table_name == 'requisition_lines':
            model_name = 'RequisitionLine'
        elif table_name == 'purchase_receipts':
            model_name = 'PurchaseReceipt'
        elif table_name == 'orgs':
            model_name = 'OrgBase'
        elif table_name == 'customers':
            model_name = 'CustomerOrg'
        elif table_name == 'vendors':
            model_name = 'VendorOrg'
        elif table_name == 'reps':
            model_name = 'RepOrg'
        elif table_name == 'employees':
            model_name = 'EmployeeOrg'
        elif table_name == 'manufacturers':
            model_name = 'ManufacturerOrg'
        else:
            model_name = table_name.rstrip('s').capitalize()
        try:
            model = apps.get_model(app_label, model_name)
        except LookupError:
            return api_response(success=False, status_code=400, message='Model not found', error={'code':'unknown_table','details':f'Model not found for {table_name}'})
        if record_id:
            try:
                obj = model.objects.get(id=record_id)
            except model.DoesNotExist:  # type: ignore[attr-defined]
                return api_response(success=False, status_code=404, message='Record not found', error={'code':'not_found','details':'Record not found'})
            record = model_to_dict(obj)
            filtered_record = filter_record_for_role(record, table_name, user_role, 'view')
            related_result = get_related_data(table_name, int(record_id))
            safe_record = {k: self._sanitize(v) for k, v in filtered_record.items()}
            safe_related = {rk: [ {sk: self._sanitize(sv) for sk, sv in r.items()} for r in rv ] for rk, rv in related_result.get('related', {}).items()} if related_result.get('related') else {}
            payload = {
                'table_name': table_name,
                'record': safe_record,
            }
            if safe_related:
                payload['related'] = safe_related
            if related_result.get('errors'):
                payload['related_errors'] = related_result.get('errors')
            return api_response(data=payload)
        # list
        queryset = model.objects.all()  # type: ignore[attr-defined]
        raw_records = [
            filter_record_for_role(model_to_dict(obj), table_name, user_role, 'view')
            for obj in queryset
        ]
        safe_records = [
            {k: self._sanitize(v) for k, v in rec.items()}
            for rec in raw_records
        ]
        payload = {
            'table_name': table_name,
            'results': safe_records,
            'total': len(safe_records),
            'limit': None,
            'offset': 0,
        }
        return api_response(data=payload)