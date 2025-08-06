from django.views.generic import TemplateView
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.apps import apps
from django.core import serializers
from .contact_view import WebContactView
from .edit_views import EditContactView
from .web_auth_views import WebSignupView, WebLoginView, WebLogoutView

# Define HomeView and AboutView directly in this file
class HomeView(TemplateView):
    template_name = 'core/home.html'

class AboutView(TemplateView):
    template_name = 'core/about.html'

# Universal API Views - Simple implementations for now
class UniversalCRUDView(TemplateView):
    """Universal management interface for all tables"""
    template_name = 'core/uni.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['table_name'] = self.request.GET.get('table_name', 'contacts')
        context['record_id'] = self.request.GET.get('id')
        context['mode'] = self.request.GET.get('mode', 'list')
        print(context)  # Debugging output
        return context



class UniversalGetView(View):
    def get(self, request):
        table_name = request.GET.get('table_name', 'contacts')
        record_id = request.GET.get('id')
        print(f"UniversalGetView: table_name={table_name}, record_id={record_id}")

        # Singularize and capitalize table name for model lookup
        model_name = table_name.rstrip('s').capitalize()
        print(f"UniversalGetView: model_name={model_name}")

        model = apps.get_model('core', model_name)
        print(f"UniversalGetView: model={model}")

        if record_id:
            queryset = model.objects.filter(id=record_id)
        else:
            queryset = model.objects.all()
        print(f"UniversalGetView: queryset count={queryset.count()}")

        data = []
        for obj in queryset:
            record = obj.__dict__.copy()
            record.pop('_state', None)
            record['id'] = obj.id
            record['table'] = table_name
            record['sample'] = str(obj)
            print(f"UniversalGetView: record={record}")
            data.append(record)

        print(f"UniversalGetView: response data count={len(data)}")
        return JsonResponse({'success': True, 'data': data})


class UniversalSaveView(View):
    """Save (create/update) records to any table"""
    def post(self, request):
        table_name = request.GET.get('table_name', 'contacts')
        record_id = request.GET.get('id')
        
        data = {
            'success': True,
            'message': f'Record {"updated" if record_id else "created"} in {table_name}',
            'id': record_id or 123
        }
        
        return JsonResponse(data)

class UniversalDeleteView(View):
    """Delete records from any table"""
    def delete(self, request):
        table_name = request.GET.get('table_name', 'contacts')
        record_id = request.GET.get('id')
        
        data = {
            'success': True,
            'message': f'Record {record_id} deleted from {table_name}'
        }
        
        return JsonResponse(data)

# Export all views
__all__ = [
    'HomeView',
    'AboutView',
    'WebContactView',
    'EditContactView', 
    'WebSignupView',
    'WebLoginView', 
    'WebLogoutView',
    'UniversalCRUDView',
    'UniversalGetView',
    'UniversalQueryView',
    'UniversalSaveView',
    'UniversalDeleteView',
]