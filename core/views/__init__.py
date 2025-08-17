# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/core/views/__init__.py
from .contact_view import WebContactView
# from .edit_views import EditContactView  # Disabled: edit_views.py not found
from .auth_views import SignupView, WebLoginView, WebLogoutView
from core.services.wcapi import (
    WcapiView,
)
from django.views.generic import TemplateView


# Define HomeView and AboutView directly in this file
class HomeView(TemplateView):
    template_name = 'home.html'

class AboutView(TemplateView):
    template_name = 'about.html'

# # Universal API Views - Simple implementations for now
# class WcapiView(TemplateView):
#     """Universal management interface for all tables"""
#     template_name = 'core/uni.html'
    






# class WcapiView(View):
#     """Save (create/update) records to any table"""
#     def post(self, request):
#         table_name = request.GET.get('table_name', 'contacts')
#         record_id = request.GET.get('id')
        
#         data = {
#             'success': True,
#             'message': f'Record {"updated" if record_id else "created"} in {table_name}',
#             'id': record_id or 123
#         }
        
#         return JsonResponse(data)

# class WcapiView(View):
#     """Delete records from any table"""
#     def delete(self, request):
#         table_name = request.GET.get('table_name', 'contacts')
#         record_id = request.GET.get('id')
        
#         data = {
#             'success': True,
#             'message': f'Record {record_id} deleted from {table_name}'
#         }
        
#         return JsonResponse(data)



# Export all views
__all__ = [
    'HomeView',
    'AboutView',
    'WebContactView',
    'EditContactView', 
    'SignupView',
    'WebLoginView', 
    'WebLogoutView',
    'WcapiView',
    'WcapiView',
    'WcapiView',
    'WcapiView',
    'WcapiView',
]