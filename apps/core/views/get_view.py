# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/core/views/get_view.py
from django.views import View
from django.http import JsonResponse
from django.apps import apps
from django.forms.models import model_to_dict
from apps.core.views.related_view import get_related_data
from apps.core.services.view_edit_access import filter_record_for_role

TABLE_APP_MAP = {
    'contacts': 'core',
    'actions': 'core',
    'emails': 'communications',
    'phones': 'communications',
    'addresses': 'communications',
    'domains': 'communications',
    # Add more as needed
}

class WcapiGetView(View):
    def get(self, request):
        """
        Handles GET requests to retrieve records from a specified table.

        Args:
            request (HttpRequest): The HTTP request object containing query parameters:
                - table_name (str): The name of the table/model to query (required).
                - id (str, optional): The ID of a specific record to retrieve.

        Returns:
            JsonResponse: 
                - If 'id' is provided: Returns a JSON response with the filtered record data, 
                  related data, and any errors. If the record is not found, returns a 404 error.
                - If 'id' is not provided: Returns a JSON response with a list of all filtered records.
                - If 'table_name' is missing or invalid: Returns a 400 error with an appropriate message.

        Notes:
            - User role is determined from the request and used to filter the returned data.
            - Related data is merged into the single record response.
            - Uses TABLE_APP_MAP to resolve the Django app label for the model.
        """
        table_name = request.GET.get('table_name')
        record_id = request.GET.get('id')
        #QQQ need to add roles  
        user_role = getattr(request.user, "role", "PUBLIC")

        if not table_name:
            return JsonResponse({'success': False, 'error': 'Missing table_name'}, status=400)

        app_label = TABLE_APP_MAP.get(table_name, 'core')
        model_name = "Location" if table_name == "addresses" else table_name.rstrip('s').capitalize()
        try:
            model = apps.get_model(app_label, model_name)
        except LookupError:
            return JsonResponse({'success': False, 'error': f'Model not found for {table_name}'}, status=400)

        if record_id:
            # Single record
            try:
                obj = model.objects.get(id=record_id)
            except model.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Record not found'}, status=404)
            record = model_to_dict(obj)
            #QQQ removed filter by role for development
            filtered_record = filter_record_for_role(record, table_name, user_role, "view")
            related_result = get_related_data(table_name, int(record_id))
            related_data = related_result.get('related', {})
            errors = related_result.get('errors', {})

            # NEST related_data under a 'data' key in filtered_record
            return JsonResponse({
                'success': True,
                'data': filtered_record,      # main record only
                'related': related_data,      # top-level related data
                'errors': errors
            })
        else:
            # List all records
            queryset = model.objects.all()
            data = [
                filter_record_for_role(model_to_dict(obj), table_name, user_role, "view")
                for obj in queryset
            ]
            return JsonResponse({'success': True, 'data': data})