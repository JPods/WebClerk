from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from core.models import Contact

class WebContactView(LoginRequiredMixin, TemplateView):
    template_name = 'core/contact.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contact = self.request.user
        
        # Add related data using select_related and prefetch_related for efficiency
        try:
            contact = Contact.objects.prefetch_related(
                'emails', 'phones', 'domains', 'addresses', 'actions'
            ).get(id=contact.id)
        except:
            # Fallback if prefetch fails
            contact = self.request.user
        
        context['contact'] = contact
        context['is_own_profile'] = True
        
        return context

class ContactDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'core/contact.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contact_id = kwargs.get('contact_id')
        
        try:
            contact = Contact.objects.prefetch_related(
                'emails', 'phones', 'domains', 'addresses', 'actions'
            ).get(id=contact_id)
        except Contact.DoesNotExist:
            contact = get_object_or_404(Contact, id=contact_id)
        
        context['contact'] = contact
        context['is_own_profile'] = (contact.id == self.request.user.id)
        
        return context
    