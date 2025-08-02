from django.views.generic import TemplateView
from django.http import JsonResponse, HttpResponse
from django.views import View
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
    template_name = 'core/universal_manage.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['table_name'] = self.request.GET.get('table_name', 'contacts')
        context['record_id'] = self.request.GET.get('id')
        context['mode'] = self.request.GET.get('mode', 'list')
        return context

class UniversalGetView(View):
    """Get records from any table"""
    def get(self, request):
        table_name = request.GET.get('table_name', 'contacts')
        record_id = request.GET.get('id')
        
        # Placeholder response - replace with real database queries
        if record_id:
            data = {
                'success': True,
                'data': {'id': record_id, 'table': table_name, 'sample': 'data'}
            }
        else:
            data = {
                'success': True,
                'data': [
                    {'id': 1, 'table': table_name, 'sample': 'record 1'},
                    {'id': 2, 'table': table_name, 'sample': 'record 2'},
                ]
            }
        
        return JsonResponse(data)

class UniversalQueryView(View):
    """Query/search records from any table"""
    def get(self, request):
        table_name = request.GET.get('table_name', 'contacts')
        search = request.GET.get('search', '')
        
        data = {
            'success': True,
            'data': [
                {'id': 1, 'table': table_name, 'search_result': f'Match for: {search}'},
            ],
            'total': 1
        }
        
        return JsonResponse(data)

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