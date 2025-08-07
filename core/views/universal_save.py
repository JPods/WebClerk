import json
from django.http import JsonResponse
from django.views import View
from django.apps import apps

class UniversalSaveView(View):
    def put(self, request):
        table_name = request.GET.get('table_name')
        record_id = request.GET.get('id')
        if not table_name or not record_id:
            return JsonResponse({'success': False, 'message': 'Missing table_name or id'}, status=400)

        model = apps.get_model('core', table_name.rstrip('s').capitalize())
        try:
            obj = model.objects.get(id=record_id)
        except model.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Record not found'}, status=404)

        # Parse incoming data
        data = json.loads(request.body)

        # Pre-save hook
        if hasattr(obj, 'save_before') and callable(getattr(obj, 'save_before')):
            result = obj.save_before(data)
            if result is False:
                return JsonResponse({'success': False, 'message': 'save_before failed'}, status=400)

        # Update fields
        for field, value in data.items():
            setattr(obj, field, value)

        # Post-save hook (before actual save, in case you want to modify fields)
        if hasattr(obj, 'save_after') and callable(getattr(obj, 'save_after')):
            result = obj.save_after(data)
            if result is False:
                return JsonResponse({'success': False, 'message': 'save_after failed'}, status=400)

        obj.save()
        return JsonResponse({'success': True, 'id': obj.id})