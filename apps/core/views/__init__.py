from apps.core.views.save_view import SaveWcapiView
from apps.core.views.choices import ChoiceCatalogView

# Alias for backward compatibility
WcapiView = SaveWcapiView

# # Universal API Views - Simple implementations for now
# class WcapiView(TemplateView):
#     """Universal management interface for all tables"""
#     template_name = 'core/uni.html'
    






# class WcapiView(View):
#     """Save (create/update) records to any table"""
#     def post(self, request):
#         table-name = request.GET.get('table-name', 'contacts')
#         record_id = request.GET.get('id')
        
#         data = {
#             'success': True,
#             'message': f'Record {"updated" if record_id else "created"} in {table-name}',
#             'id': record_id or 123
#         }
        
#         return JsonResponse(data)

# class WcapiView(View):
#     """Delete records from any table"""
#     def delete(self, request):
#         table-name = request.GET.get('table-name', 'contacts')
#         record_id = request.GET.get('id')
        
#         data = {
#             'success': True,
#             'message': f'Record {record_id} deleted from {table-name}'
#         }
        
#         return JsonResponse(data)



# Export all views
__all__ = [
    'WcapiView',
    'ChoiceCatalogView',
]