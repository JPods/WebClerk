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

class UniversalGetView(View):
    def connect(self, request):
        table_name = request.META.get('HTTP_TABLE_NAME')
        model = MODEL_MAP.get(table_name)
        if not model:
            return JsonResponse({'success': False, 'message': 'Invalid table_name'})
        data = list(model.objects.all().values())
        return JsonResponse({'success': True, 'data': data})

    def delete(self, request):
        table_name = request.DELETE.get('table_name')
        model = MODEL_MAP.get(table_name)
        if not model:
            return JsonResponse({'success': False, 'message': 'Invalid table_name'})
        data = list(model.objects.all().values())
        return JsonResponse({'success': True, 'data': data})
    
    def get(self, request):
        table_name = request.GET.get('table_name')
        model = MODEL_MAP.get(table_name)
        if not model:
            return JsonResponse({'success': False, 'message': 'Invalid table_name'})
        data = list(model.objects.all().values())
        return JsonResponse({'success': True, 'data': data})

    def head(self, request):
        table_name = request.META.get('HTTP_TABLE_NAME')
        model = MODEL_MAP.get(table_name)
        if not model:
            return JsonResponse({'success': False, 'message': 'Invalid table_name'})
        data = list(model.objects.all().values())
        return JsonResponse({'success': True, 'data': data})    
    # Help page for WCapi - could be a static page, duplicate of options and root? QQQ
    def help(self, request):
        return JsonResponse({'success': True, 'message': 'Help page for WCapi'})

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
    
    
    




# Similar implementations would be needed for UniversalCRUDView, UniversalQueryView, UniversalSaveView, and UniversalDeleteView
    
