from django.views import View
from django.http import JsonResponse
from core.models import Contact, Action  # Import only allowed models

MODEL_MAP = {
    'contacts': Contact,
    'actions': Action,
    # Add other allowed models
}

class UniversalGetView(View):
    def get(self, request):
        table_name = request.GET.get('table_name')
        model = MODEL_MAP.get(table_name)
        if not model:
            return JsonResponse({'success': False, 'message': 'Invalid table_name'})
        data = list(model.objects.all().values())
        return JsonResponse({'success': True, 'data': data})