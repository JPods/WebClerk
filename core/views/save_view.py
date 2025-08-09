from urllib import request
from django.http import JsonResponse
from django.views import View
from django.apps import apps
from django.views.decorators.csrf import csrf_exempt
from core import tasks  # Import your tasks module
from core.models import Contact  # or your dynamic model logic

ALLOWED_NESTED_KEYS = {
    # Limit the size and branching of what can be saved
    'refs': {'tags'},
    'prefs': {'theme', 'lang'},
    'metadata': {'notes'},
}


class SaveView(View):
    def post(self, request):
        import json
        try:
            data = json.loads(request.body)
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Invalid JSON: {e}'}, status=400)

        table_name = data.get('table_name')
        record_id = data.get('id')
        if not table_name or not record_id:
            return JsonResponse({'success': False, 'message': 'Missing table_name or id'}, status=400)

        model = apps.get_model('core', table_name.rstrip('s').capitalize())
        try:
            obj = model.objects.get(id=record_id)
        except model.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Record not found'}, status=404)

        nested_fields = ['refs', 'prefs', 'metadata']

        for field, value in data.items():
            if field in nested_fields and hasattr(obj, field):
                allowed_keys = ALLOWED_NESTED_KEYS.get(field, set())
                current = getattr(obj, field) or {}
                if isinstance(current, str):
                    try:
                        current = json.loads(current)
                    except Exception:
                        current = {}
                if isinstance(value, dict):
                    for k, v in value.items():
                        if k in allowed_keys:
                            current[k] = v
                setattr(obj, field, current)
            elif hasattr(obj, field):
                setattr(obj, field, value)

        obj.save()
        return JsonResponse({'success': True, 'id': obj.id})