from django.views.generic import TemplateView
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.apps import apps
from django.core import serializers
from django.forms.models import model_to_dict
from django.db.models import Q
from core.views.related_view import get_related_data


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

class WcapiView(View):
    
    
    def get(self, request):
        table_name = request.GET.get('table_name')
        record_id = request.GET.get('id')
        
        # print(f"WcapiView: table_name={table_name}, record_id={record_id}, contact_id={contact_id}")

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
        print(f"WcapiView: app_label={app_label}, model_name={model_name}")

        model = apps.get_model(app_label, model_name)
        print(f"WcapiView: model={model}")

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
            print(f"WcapiView: No valid contact_id for {table_name}, returning empty queryset.")
            queryset = model.objects.none()
        print(f"WcapiView: queryset count={queryset.count()}")

        data = []
        for obj in queryset:
            record = obj.__dict__.copy()
            record.pop('_state', None)
            record['id'] = obj.id
            record['table'] = table_name
            record['sample'] = str(obj)
            print(f"WcapiView: record={record}")
            data.append(record)

        print(f"WcapiView: response data count={len(data)}")
        return JsonResponse({'success': True, 'data': data})
