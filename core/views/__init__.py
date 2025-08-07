from django.views.generic import TemplateView
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.apps import apps
from django.core import serializers
from django.forms.models import model_to_dict
from .contact_view import WebContactView
from .edit_views import EditContactView
from .web_auth_views import WebSignupView, WebLoginView, WebLogoutView
from django.db.models import Q
from core.views.related_view import get_related_data


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
        contact_id = record_id or request.GET.get('contact_id')
        print(f"UniversalGetView: table_name={table_name}, record_id={record_id}, contact_id={contact_id}")

        # Special case: related data
        if table_name == "related" and contact_id:
            # parent_table and parent_id are the expected args for get_related_data
            data = get_related_data("contacts", int(contact_id))
            return JsonResponse({'success': True, 'data': data})

        if table_name == "contacts" and record_id:
            # Get the contact
            from core.models import Contact
            try:
                contact = Contact.objects.get(id=record_id)
                # Use your model's to_dict or Django's model_to_dict
                contact_json = contact.to_dict() if hasattr(contact, 'to_dict') else model_to_dict(contact)
            except Contact.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Contact not found'}, status=404)

            # Get related data using your library function
            related = get_related_data("contacts", int(record_id))

            # Return both
            return JsonResponse({
                'success': True,
                'contact': contact_json,
                'related': related,
            })

        # Get app label from map, default to 'core'
        app_label = TABLE_APP_MAP.get(table_name, 'core')
        if table_name == "addresses":
            model_name = "Address"
        else:
            model_name = table_name.rstrip('s').capitalize()
        print(f"UniversalGetView: app_label={app_label}, model_name={model_name}")

        model = apps.get_model(app_label, model_name)
        print(f"UniversalGetView: model={model}")

        # Build queryset
        queryset = model.objects.all()
        if record_id:
            queryset = queryset.filter(id=record_id)
        if contact_id and contact_id.isdigit():
            if hasattr(model, 'contact_id'):
                queryset = queryset.filter(contact_id=contact_id)
            elif table_name in ['actions', 'emails', 'phones', 'addresses', 'domains']:
                queryset = queryset.filter(**{'refs__links__contacts__contains': [int(contact_id)]})
        elif table_name in ['actions', 'emails', 'phones', 'addresses', 'domains']:
            print(f"UniversalGetView: No valid contact_id for {table_name}, returning empty queryset.")
            queryset = model.objects.none()
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


class SaveView(View):
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

# Table to app mapping
TABLE_APP_MAP = {
    'contacts': 'core',
    'actions': 'core',
    'emails': 'communications',
    'phones': 'communications',
    'addresses': 'communications',
    'domains': 'communications',
    # Add more as needed
}

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
    'SaveView',
    'UniversalDeleteView',
]