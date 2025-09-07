# path: apps/core/views/generic_views.py
from django.http import JsonResponse
from django.views.generic import TemplateView




class WcapiView(TemplateView):
    """Simple placeholder view used in docs/tests."""
    def get(self, request, *args, **kwargs):
        return JsonResponse({'success': True, 'message': 'Universal API placeholder', 'data': {'example': 'data'}})

    def delete(self, request, *args, **kwargs):
        return JsonResponse({'success': True, 'message': 'Universal API delete placeholder'})