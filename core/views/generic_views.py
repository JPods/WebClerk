# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/core/views/generic_views.py
from django.http import JsonResponse
import json
from django.views.generic import TemplateView
from core.services.view_edit_access import filter_json_response




@filter_json_response(lambda request, *a, **k: request.GET.get('table_name'), access_type="view")
class WcapiView(TemplateView):
    def get(self, request, *args, **kwargs):
        return JsonResponse({
            'success': True,
            'message': '✅ Universal Get API working!',
            'data': {'example': 'data'}
        })


class WcapiView(TemplateView):
    def delete(self, request, *args, **kwargs):
        return JsonResponse({
            'success': True,
            'message': '✅ Universal Delete API working!'
        })


class WcapiView(TemplateView):
    template_name = 'core/universal_manage.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        table_name = self.kwargs.get('table_name', 'unknown')
        
        context.update({
            'table_name': table_name,
            'page_title': f'Manage {table_name.title()}',
        })
        
        return context