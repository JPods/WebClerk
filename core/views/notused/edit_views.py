from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import UpdateView
from django.contrib import messages
from core.models import Contact

@method_decorator(login_required, name='dispatch')
class EditContactView(UpdateView):
    model = Contact
    template_name = 'core/edit_contact.html'
    fields = [
        'name_first', 'name_last', 'name_middle', 'name_prefix', 'name_suffix',
        'company', 'title', 'department', 'email'
    ]
    
    def get_object(self):
        # Get contact ID from URL parameter using contact_id convention
        contact_id = self.kwargs.get('contact_id')
        
        if contact_id:
            # Edit specific contact: /edit-contact/123/
            contact = get_object_or_404(Contact, id=contact_id)
            
            # Check permissions - users can only edit their own contact unless they're staff
            if contact != self.request.user and not self.request.user.is_staff:
                contact = self.request.user  # Fallback to own profile
                
        else:
            # Edit current user profile: /edit-contact/
            contact = self.request.user
            
        return contact
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contact = self.get_object()
        
        context.update({
            'contact_id': contact.id,  # Universal API convention
            'page_title': f'Edit Contact: {contact.get_full_name()}',
            'api_url': f'/wcapi/get/?table_name=contacts&id={contact.id}',
            'is_own_profile': contact == self.request.user,
        })
        
        return context
    
    def get_success_url(self):
        contact = self.get_object()
        messages.success(self.request, f'Contact {contact.get_full_name()} updated successfully!')
        
        # Redirect to contact detail page using contact_id
        if contact == self.request.user:
            return '/contact/'
        else:
            return f'/contact/{contact.id}/'