from django.views import View
from django.http import JsonResponse
from core.models import Contact, Action, Phone, Domain, Email, Address  # Import only allowed models

MODEL_MAP = {
    'contacts': Contact,
    'actions': Action,
    'phones': Phone,
    'domains': Domain,
    'emails': Email,
    'addresses': Address,
    # Add other allowed models
}

# We need to replace "__dict__" with our role based field filtering in the future.QQQ


class UniversalCRUDView(View):

    def get(self, request):
        print("=== UniversalCRUDView CALLED ===")  # <--- Add this line
        table_name = request.GET.get('table_name')
        record_id = request.GET.get('id')
        model = MODEL_MAP.get(table_name)
        if not model:
            return JsonResponse({'success': False, 'message': 'Invalid table_name'})

        if record_id:
            try:
                record = model.objects.get(id=record_id)
                data = record.__dict__.copy()
                data.pop('_state', None)
                return JsonResponse({'success': True, 'data': data})
            except model.DoesNotExist:
                return JsonResponse({'success': False, 'message': f'{table_name} record not found'})
            except Exception as e:
                return JsonResponse({'success': False, 'message': str(e)})

        records = model.objects.all().values()
        data = list(records)
        return JsonResponse({'success': True, 'data': data})
    
    
    
    def connect(self, request):
        table_name = request.META.get('HTTP_TABLE_NAME')
        model = MODEL_MAP.get(table_name)
        if not model:
            return JsonResponse({'success': False, 'message': 'Invalid table_name'})
        data = list(model.objects.all().values())
        return JsonResponse({'success': True, 'data': data})

    def delete(self, request):
        table_name = request.GET.get('table_name')
        record_id = request.GET.get('id')
        model = MODEL_MAP.get(table_name)
        if not model:
            return JsonResponse({'success': False, 'message': 'Invalid table_name'})

        if not record_id:
            return JsonResponse({'success': False, 'message': 'No id provided'})

        try:
            record = model.objects.get(id=record_id)
            data = record.__dict__.copy()
            data.pop('_state', None)
            record.delete()
            return JsonResponse({'success': True, 'message': f'{table_name} record deleted', 'data': data})
        except model.DoesNotExist:
            return JsonResponse({'success': False, 'message': f'{table_name} record not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    

    def head(self, request):
        table_name = request.META.get('HTTP_TABLE_NAME')
        model = MODEL_MAP.get(table_name)
        if not model:
            return JsonResponse({'success': False, 'message': 'Invalid table_name'})
        data = list(model.objects.all().values())
        return JsonResponse({'success': True, 'data': data})    

    # Help page for wcapi - could be a static page, duplicate of options and root? QQQ
    def help(self, request):
        return JsonResponse({'success': True, 'message': 'Help page for wcapi'})

    def manage(self, request):
        table_name = request.GET.get('table_name') or request.POST.get('table_name')
        model = MODEL_MAP.get(table_name)
        if not model:
            return JsonResponse({'success': False, 'message': 'Invalid table_name'})
        data = list(model.objects.all().values())
        return JsonResponse({'success': True, 'data': data})

    def options(self, request):
        table_name = request.META.get('HTTP_TABLE_NAME')
        model = MODEL_MAP.get(table_name)
        if not model:
            return JsonResponse({'success': False, 'message': 'Invalid table_name'})
        data = list(model.objects.all().values())
        return JsonResponse({'success': True, 'data': data})        

    def patch(self, request):
        table_name = request.PATCH.get('table_name')
        model = MODEL_MAP.get(table_name)
        if not model:
            return JsonResponse({'success': False, 'message': 'Invalid table_name'})
        data = list(model.objects.all().values())
        return JsonResponse({'success': True, 'data': data})    
    
    def post(self, request):
        table_name = request.POST.get('table_name')
        model = MODEL_MAP.get(table_name)
        if not model:
            return JsonResponse({'success': False, 'message': 'Invalid table_name'})
        data = list(model.objects.all().values())
        return JsonResponse({'success': True, 'data': data})
    
    def put(self, request):
        table_name = request.PUT.get('table_name')
        model = MODEL_MAP.get(table_name)
        if not model:
            return JsonResponse({'success': False, 'message': 'Invalid table_name'})
        data = list(model.objects.all().values())
        return JsonResponse({'success': True, 'data': data})

    def trace(self, request):
        table_name = request.META.get('HTTP_TABLE_NAME')
        model = MODEL_MAP.get(table_name)
        if not model:
            return JsonResponse({'success': False, 'message': 'Invalid table_name'})
        data = list(model.objects.all().values())
        return JsonResponse({'success': True, 'data': data})
    
    

