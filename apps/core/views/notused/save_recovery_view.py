from django.http import JsonResponse
from django.views import View
from django.apps import apps
from django.views.decorators.csrf import csrf_exempt
from django.utils.text import capfirst
import json
from apps.core import tasks

ALLOWED_NESTED_KEYS = {
    'refs': {'tags'},
    'prefs': {'theme', 'lang'},
    'metadata': {'notes'},
}

def find_model_for_table(table_name: str):
    """
    Search across all installed apps to find the model corresponding to the table name.
    """
    model_name = capfirst(table_name.rstrip('s'))
    for app_config in apps.get_app_configs():
        try:
            model = apps.get_model(app_config.label, model_name)
            return model
        except LookupError:
            continue
    return None

class WcapiView(View):
    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            return JsonResponse({'success': False, 'message': f'Invalid JSON: {e}'}, status=400)

        table_name = data.get('table_name')
        record_id = data.get('id', None)

        if not table_name:
            return JsonResponse({'success': False, 'message': 'Missing table_name'}, status=400)

        model = find_model_for_table(table_name)
        if not model:
            return JsonResponse({'success': False, 'message': f'No model found for table_name: {table_name}'}, status=400)

        # Determine if this is a create or update
        is_update = bool(record_id) and str(record_id) not in ('0', 'null', 'None')

        if is_update:
            try:
                obj = model.objects.get(id=record_id)
            except model.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Record not found'}, status=404)
        else:
            obj = model()  # Create new instance

        # Call pre-save task asynchronously
        tasks.save_pre.delay(table_name, data)

        nested_fields = ['refs', 'prefs', 'metadata']
        for field, value in data.items():
            if field in nested_fields and hasattr(obj, field):
                allowed_keys = ALLOWED_NESTED_KEYS.get(field, set())
                current = getattr(obj, field) or {}
                if isinstance(current, str):
                    try:
                        current = json.loads(current)
                    except json.JSONDecodeError:
                        current = {}
                if isinstance(value, dict):
                    for k, v in value.items():
                        if k in allowed_keys:
                            current[k] = v
                setattr(obj, field, current)
            elif field not in ('table_name', 'id') and hasattr(obj, field):
                setattr(obj, field, value)

        try:
            obj.save()
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Failed to save: {e}'}, status=500)

        # Call post-save task asynchronously
        tasks.save_post.delay(table_name, data)

        return JsonResponse({'success': True, 'id': obj.id})