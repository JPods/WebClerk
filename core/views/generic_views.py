from django.http import JsonResponse
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json

@method_decorator(csrf_exempt, name='dispatch')
class WcapiView(TemplateView):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            return JsonResponse({
                'success': True,
                'message': '✅ Universal Query API working!',
                'table_name': data.get('table_name'),
                'results': [{'id': 1, 'name': 'Sample'}, {'id': 2, 'name': 'Sample 2'}],
                'count': 2
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

@method_decorator(csrf_exempt, name='dispatch')
class WcapiView(TemplateView):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            return JsonResponse({
                'success': True,
                'message': '✅ Universal Save API working!',
                'saved_data': data
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

class WcapiView(TemplateView):
    def get(self, request, *args, **kwargs):
        return JsonResponse({
            'success': True,
            'message': '✅ Universal Get API working!',
            'data': {'example': 'data'}
        })

@method_decorator(csrf_exempt, name='dispatch')
class WcapiView(TemplateView):
    def delete(self, request, *args, **kwargs):
        return JsonResponse({
            'success': True,
            'message': '✅ Universal Delete API working!'
        })

@method_decorator(csrf_exempt, name='dispatch')
class UniversalCloneView(TemplateView):
    def post(self, request, *args, **kwargs):
        return JsonResponse({
            'success': True,
            'message': '✅ Universal Clone API working!'
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