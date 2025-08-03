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
    id_record = request.GET.get('id')
    query = request.GET.get('query')
    model = MODEL_MAP.get(table_name)
    if not model:
        return JsonResponse({'success': False, 'message': 'Invalid table_name'})

    # --- Role check: customers cannot get another customer's record (stub for future) ---
    # user = request.user
    # if table_name == 'customers' and id_record:
    #     # if not user.is_staff and not user.is_superuser and int(id_record) != user.customer.id:
    #     #     return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)
    #     pass

    # --- Query support (stub) ---
    if query:
        # TODO: Implement advanced query using Django/PostgreSQL search
        return JsonResponse({'success': False, 'message': 'Advanced query not yet implemented'})

    # --- Single record by ID ---
    if id_record:
        try:
            record = model.objects.get(id=id_record)
            data = record.__dict__.copy()
            data.pop('_state', None)
            return JsonResponse({'success': True, 'data': data})
        except model.DoesNotExist:
            return JsonResponse({'success': False, 'message': f'{table_name} record not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})

    # --- All records (note: for some tables, restrict in future) ---
    # For example, customers should only see their own records, but items can be public.
    records = model.objects.all()
    data = [obj.__dict__.copy() for obj in records]
    for d in data:
        d.pop('_state', None)
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
    
