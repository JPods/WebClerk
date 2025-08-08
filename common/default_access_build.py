from django.views import View
from django.http import JsonResponse
from django.apps import apps
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json

# Example: Define which roles can edit which tables
ROLE_TABLE_PERMISSIONS = {
    'admin': ['contacts', 'emails', 'phones', 'addresses', 'domains'],
    'manager': ['contacts', 'emails', 'phones'],
    'user': ['contacts'],
    # etc.
}

@method_decorator(csrf_exempt, name='dispatch')
class SaveView(View):
    def post(self, request):
        try:
            table_name = request.GET.get('table_name')
            record_id = request.GET.get('id')
            data = json.loads(request.body)
            user_role = getattr(request.user, 'role', 'user')  # Adjust as needed

            # Permission check
            allowed_tables = ROLE_TABLE_PERMISSIONS.get(user_role, [])
            if table_name not in allowed_tables:
                return JsonResponse({'success': False, 'message': 'Permission denied.'})

            # Dynamic model lookup
            model = apps.get_model('core', table_name.capitalize())
            if not model:
                return JsonResponse({'success': False, 'message': 'Invalid table name.'})

            # Get or create the record
            if record_id:
                obj = model.objects.get(id=record_id)
            else:
                obj = model()

            # Update fields
            for field, value in data.items():
                if hasattr(obj, field):
                    setattr(obj, field, value)
            obj.save()

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})