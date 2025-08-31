# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/core/views/get_view.py
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.apps import apps
from django.forms.models import model_to_dict
from apps.core.views.related_view import get_related_data
from apps.core.services.view_edit_access import filter_record_for_role

TABLE_APP_MAP = {
    'contacts': 'core',
    'actions': 'core',
    'emails': 'communications',
    'phones': 'communications',
    'locations': 'communications',
    'domains': 'communications',
    # Add more as needed
}

class WcapiGetView(APIView):
    """JWT-protected GET access to single/list records with basic role filtering."""
    permission_classes = [IsAuthenticated]

    def get(self, request):  # noqa: C901 (simple flow)
        from django.conf import settings
        require_jwt = getattr(settings, 'WCAPI_JWT_ONLY', False)
        is_jwt = bool(getattr(request, 'auth', None))
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
        if require_jwt and not is_jwt:
            return JsonResponse({'success': False, 'error': 'JWT required (missing Bearer token)'}, status=401)

        table_name = request.GET.get('table_name')
        record_id = request.GET.get('id')
        user_role = getattr(request.user, 'role', 'PUBLIC')
        if not table_name:
            return JsonResponse({'success': False, 'error': 'Missing table_name'}, status=400)
        app_label = TABLE_APP_MAP.get(table_name, 'core')
        model_name = 'Location' if table_name == 'addresses' else table_name.rstrip('s').capitalize()
        try:
            model = apps.get_model(app_label, model_name)
        except LookupError:
            return JsonResponse({'success': False, 'error': f'Model not found for {table_name}'}, status=400)
        if record_id:
            try:
                obj = model.objects.get(id=record_id)
            except model.DoesNotExist:  # type: ignore[attr-defined]
                return JsonResponse({'success': False, 'error': 'Record not found'}, status=404)
            record = model_to_dict(obj)
            filtered_record = filter_record_for_role(record, table_name, user_role, 'view')
            related_result = get_related_data(table_name, int(record_id))
            return JsonResponse({'success': True, 'data': filtered_record, 'related': related_result.get('related', {}), 'errors': related_result.get('errors', {})})
        # list
        queryset = model.objects.all()  # type: ignore[attr-defined]
        data = [
            filter_record_for_role(model_to_dict(obj), table_name, user_role, 'view')
            for obj in queryset
        ]
        return JsonResponse({'success': True, 'data': data})