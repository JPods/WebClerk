# path: apps/core/views/contact_view.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import TemplateView
from apps.core.models.contact import Contact
import httpx

# --- RECOMMENDED: Import your role-based access utility ---
# from common.role_access import get_role_settings, can_user_view

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
        
    # Existing: Simple contact lookup - no prefetch needed with Universal API
    contact = get_object_or_404(Contact, id=contact_id)
        
    context['contact'] = contact
    user_id = getattr(self.request.user, 'id', None)
    context['is_own_profile'] = (contact.id == user_id)
        
        # ADD: Optionally, filter fields in contact based on role's allowed "view" fields from settings.
        # Example: Only include fields in can_user_view('contacts', user.role)

        return context

    async def fetch_contact_data(self, user_id=None):
        if user_id is None:
            user_id = getattr(self.request.user, 'id', None)

        # Existing: Fetch related records for the contact via async HTTP calls to the Universal API.
        endpoints = [
            ("addresses", f"/wcapi/get/?model_name=address&contact_id={user_id}"),
            ("phones", f"/wcapi/get/?model_name=phone&contact_id={user_id}"),
            ("emails", f"/wcapi/get/?model_name=email&contact_id={user_id}"),
            ("domains", f"/wcapi/get/?model_name=domain&contact_id={user_id}"),
            ("actions", f"/wcapi/get/?model_name=action&contact_id={user_id}"),
        ]

        results = {}
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            for key, url in endpoints:
                resp = await client.get(url)
                results[key] = resp.json()
        return results

        # ADD: Optionally, filter each related record's fields based on role's allowed "view" fields from settings.
        # Example: For each record in results[key], only include fields in can_user_view(key, user.role)