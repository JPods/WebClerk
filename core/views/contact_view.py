from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.http import JsonResponse
from core.models import Contact

@method_decorator(login_required, name='dispatch')
class WebContactView(TemplateView):
    template_name = 'core/contact.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get contact ID from URL parameter using id_contact convention
        id_contact = self.kwargs.get('id_contact')
        
        if id_contact:
            # View specific contact: /contact/123/
            contact = get_object_or_404(Contact, id=id_contact)
            
            # Check permissions - users can only view their own contact unless they're staff
            if contact != self.request.user and not self.request.user.is_staff:
                contact = self.request.user  # Fallback to own profile
                
        else:
            # View current user profile: /contact/
            contact = self.request.user
        
        context.update({
            'contact': contact,  # This fixes your template variable error!
            'id_contact': contact.id,  # Universal API convention
            'page_title': f'Contact: {contact.get_full_name()}',
            'api_url': f'/WCapi/get/?table_name=contacts&id={contact.id}',
            'is_own_profile': contact == self.request.user,
        })
        
        return context
    
    def get(self, request, *args, **kwargs):
        # Handle API format requests
        if request.GET.get('format') == 'json':
            id_contact = self.kwargs.get('id_contact', request.user.id)
            contact = get_object_or_404(Contact, id=id_contact)
            
            # Check permissions for API access
            if contact != request.user and not request.user.is_staff:
                return JsonResponse({'error': 'Permission denied'}, status=403)
            
            # Return Universal API compliant JSON
            return JsonResponse({
                'table_name': 'contacts',
                'id': contact.id,
                'id_contact': contact.id,  # Universal API convention
                'data': {
                    'id': contact.id,
                    'email': contact.email,
                    'name_first': contact.name_first,
                    'name_last': contact.name_last,
                    'name_middle': contact.name_middle,
                    'name_prefix': contact.name_prefix,
                    'name_suffix': contact.name_suffix,
                    'company': contact.company,
                    'title': contact.title,
                    'department': contact.department,
                    'role': contact.role,
                    'is_active': contact.is_active,
                    'is_staff': contact.is_staff,
                    'date_joined': contact.date_joined.isoformat(),
                    'last_login': contact.last_login.isoformat() if contact.last_login else None,
                    'metadata': contact.metadata,
                },
                'api_urls': {
                    'update': f'/WCapi/save/?table_name=contacts&id={contact.id}',
                    'delete': f'/WCapi/delete/?table_name=contacts&id={contact.id}',
                    'clone': f'/WCapi/clone/?table_name=contacts&id={contact.id}',
                    'emails': f'/WCapi/emails/manage/?id_contact={contact.id}',
                    'phones': f'/WCapi/phones/manage/?id_contact={contact.id}',
                    'domains': f'/WCapi/domains/manage/?id_contact={contact.id}',
                    'addresses': f'/WCapi/addresses/manage/?id_contact={contact.id}',
                }
            })
        
        return super().get(request, *args, **kwargs)