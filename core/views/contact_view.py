from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from core.models.contact import Contact
import httpx

class WebContactView(LoginRequiredMixin, TemplateView):
    template_name = 'core/user.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        return context

class ContactDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'core/contact.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contact_id = kwargs.get('contact_id')
        
        # Simple contact lookup - no prefetch needed with Universal API
        contact = get_object_or_404(contact, id=contact_id)
        
        context['contact'] = contact
        context['is_own_profile'] = (contact.id == self.request.user.id)
        
        return context

    async def fetch_contact_data(self, user_id=None):
        if user_id is None:
            user_id = self.request.user.id

        endpoints = [
            ("addresses", f"/wcapi/get/?table_name=addresses&contact_id={user_id}"),
            ("phones", f"/wcapi/get/?table_name=phones&contact_id={user_id}"),
            ("emails", f"/wcapi/get/?table_name=emails&contact_id={user_id}"),
            ("domains", f"/wcapi/get/?table_name=domains&contact_id={user_id}"),
            ("actions", f"/wcapi/get/?table_name=actions&contact_id={user_id}"),
        ]

        results = {}
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            for key, url in endpoints:
                resp = await client.get(url)
                results[key] = resp.json()
        return results