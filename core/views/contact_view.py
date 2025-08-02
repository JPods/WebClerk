from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from core.models.contact import Contact

class WebContactView(LoginRequiredMixin, TemplateView):
    template_name = 'core/contact.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contact = self.request.user
        
        # No more Django relationships - Universal API handles this
        context['contact'] = contact
        context['is_own_profile'] = True
        
        return context

class ContactDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'core/contact.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contact_id = kwargs.get('contact_id')
        
        # Simple contact lookup - no prefetch needed with Universal API
        contact = get_object_or_404(Contact, id=contact_id)
        
        context['contact'] = contact
        context['is_own_profile'] = (contact.id == self.request.user.id)
        
        return context