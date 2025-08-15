from django.views import View
"""
WcapiView provides a generic API interface for CRUD operations on several models via HTTP methods.
Attributes:
    MODEL_MAP (dict): Maps string table names to their corresponding Django model classes.
Methods:
    get(request):
        Handles GET requests. Retrieves a single record by 'id' or all records for a given 'table_name'.
        Returns JSON response with data or error message.
    connect(request):
        Handles custom CONNECT requests. Retrieves all records for a given 'table_name' from HTTP headers.
        Returns JSON response with data or error message.
    delete(request):
        Handles DELETE requests. Deletes a record by 'id' for a given 'table_name'.
        Returns JSON response with success or error message and deleted data.
    head(request):
        Handles HEAD requests. Retrieves all records for a given 'table_name' from HTTP headers.
        Returns JSON response with data or error message.
    help(request):
        Provides a help message for the wcapi endpoint.
        Returns JSON response with a help message.
    manage(request):
        Handles custom MANAGE requests. Retrieves all records for a given 'table_name' from GET or POST data.
        Returns JSON response with data or error message.
    options(request):
        Handles OPTIONS requests. Retrieves all records for a given 'table_name' from HTTP headers.
        Returns JSON response with data or error message.
    patch(request):
        Handles PATCH requests. Retrieves all records for a given 'table_name' from PATCH data.
        Returns JSON response with data or error message.
    post(request):
        Handles POST requests. Retrieves all records for a given 'table_name' from POST data.
        Returns JSON response with data or error message.
    put(request):
        Handles PUT requests. Retrieves all records for a given 'table_name' from PUT data.
        Returns JSON response with data or error message.
    trace(request):
        Handles TRACE requests. Retrieves all records for a given 'table_name' from HTTP headers.
        Returns JSON response with data or error message.
Notes:
    - The API currently uses __dict__ for serialization, which may expose internal fields.
    - Role-based field filtering is planned for future implementation.
    - Only models listed in MODEL_MAP are accessible via this API.
"""
from django.http import JsonResponse
from core.models import Contact, Action  # Only core models here
from communications.models import Phone, Domain, Email, Address  # Communications models here


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


class WcapiView(View):

    def get(self, request):
        print("=== WcapiView CALLED ===")  # <--- Add this line
        table_name = request.GET.get('table_name')
        record_id = request.GET.get('id')
        template_name = request.GET.get('template_name')
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



