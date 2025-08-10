from urllib import request
from django.http import JsonResponse
from django.views import View
from django.apps import apps
from core import tasks

ALLOWED_NESTED_KEYS = {
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
        record_id = data.get('id', None)
        if not table_name:
            return JsonResponse({'success': False, 'message': 'Missing table_name'}, status=400)

        model = apps.get_model('core', table_name.rstrip('s').capitalize())

        # Determine if this is a create or update
        is_create = not record_id or str(record_id) in ('0', 'null', 'None')

        if is_create:
            obj = model()
        else:
            try:
                obj = model.objects.get(id=record_id)
            except model.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Record not found'}, status=404)

        nested_fields = ['refs', 'prefs', 'metadata']

        # Call pre-save task asynchronously
        tasks.save_pre.delay(table_name, data)

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
            elif hasattr(obj, field) and field not in ['id', 'table_name']:
                setattr(obj, field, value)

        obj.save()

        # Call post-save task asynchronously
        tasks.save_post.delay(table_name, data)

        return JsonResponse({'success': True, 'id': obj.id})