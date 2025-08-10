from typing import Dict, List
from django.http import JsonResponse
from django.views import View
from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist
from core.models import Contact, Action
from communications.models import Phone, Email, Address, Domain

RELATED_TABLES: Dict[str, List[str]] = {
    'contacts': ['phones', 'emails', 'addresses', 'actions', 'domains'],
}

RELATED_MODELS: Dict[str, List[type]] = {
    'contacts': [Phone, Email, Address, Domain, Action],
}

def get_related_data(contact: Contact) -> dict:
    """
    Fetches all related data for a given contact, returning a single JSON object.
    """
    related = {}
    related_models = {
        'phones': ('communications', 'Phone'),
        'emails': ('communications', 'Email'),
        'addresses': ('communications', 'Address'),
        'domains': ('communications', 'Domain'),
        'actions': ('core', 'Action'),
    }

    for related_table in RELATED_TABLES.get('contacts', []):
        if related_table in related_models:
            app_label, model_name = related_models[related_table]
            model = apps.get_model(app_label, model_name)
            model_fields = [f.name for f in model._meta.get_fields()]
            if 'contact_id' in model_fields:
                queryset = model.objects.filter(contact_id=contact.id)
            else:
                queryset = model.objects.filter(refs__links__contacts__contains=[contact.id])
            related[related_table] = list(queryset.values())
        else:
            related[related_table] = []

    # Get all fields from the Contact model dynamically
    contact_data = {
        field.name: getattr(contact, field.name)
        for field in contact._meta.get_fields()
        if field.concrete and not field.many_to_many
    }
    contact_data['related'] = related

    return contact_data

class RelatedDataView(View):
    def get(self, request, contact_id=None, contact_email=None):
        if not contact_id and not contact_email:
            return JsonResponse(
                {'success': False, 'error': 'contact_id or contact_email is required'},
                status=400
            )

        try:
            if contact_id:
                contact = Contact.objects.get(id=int(contact_id))
            else:
                contact = Contact.objects.get(email=contact_email)
        except ObjectDoesNotExist:
            return JsonResponse(
                {'success': False, 'error': 'Contact not found'},
                status=404
            )
        except ValueError:
            return JsonResponse(
                {'success': False, 'error': 'Invalid contact_id'},
                status=400
            )

        data = get_related_data(contact)
        return JsonResponse({'success': True, 'data': data})