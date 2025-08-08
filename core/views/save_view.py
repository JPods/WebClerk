import json
from urllib import request
from django.http import JsonResponse
from django.views import View
from django.apps import apps
from django.views.decorators.csrf import csrf_exempt
from core import tasks  # Import your tasks module
from core.models import Contact  # or your dynamic model logic


class SaveView(View):
    def post(self, request):
        table_name = request.GET.get('table_name')
        record_id = request.GET.get('id')
        print("Request body:", request.body)

        if not table_name or not record_id:
            return JsonResponse({'success': False, 'message': 'Missing table_name or id'}, status=400)

        model = apps.get_model('core', table_name.rstrip('s').capitalize())
        try:
            obj = model.objects.get(id=record_id)
        except model.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Record not found'}, status=404)

        # Parse JSON body
        try:
            data = json.loads(request.body)
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Invalid JSON: {e}'}, status=400)

        # Loop through each field in the body and set it on the object
        for field, value in data.items():
            if hasattr(obj, field):
                setattr(obj, field, value)

        obj.save()
        return JsonResponse({'success': True, 'id': obj.id})