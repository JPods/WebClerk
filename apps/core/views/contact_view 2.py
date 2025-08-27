<<<<<<< HEAD:core/views/contact_view.py
# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/core/views/contact_view.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from core.models.contact import Contact
import httpx
=======
from rest_framework.views import APIView
from rest_framework import status, permissions, generics
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiResponse
from ..serializers import ContactSerializer, RegisterSerializer, LoginSerializer, VerifyEmailSerializer
from ..models import Contact
from apps.core.utils import get_accessible_fields
from django.core.mail import send_mail
from django.conf import settings
>>>>>>> 01558f6ebce5d18d828e022158343627fc8162d8:apps/core/views/contact_view.py

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
        context['is_own_profile'] = (contact.id == self.request.user.id)
        
        # ADD: Optionally, filter fields in contact based on role's allowed "view" fields from settings.
        # Example: Only include fields in can_user_view('contacts', user.role)

        return context

    async def fetch_contact_data(self, user_id=None):
        if user_id is None:
            user_id = self.request.user.id

        # Existing: Fetch related records for the contact via async HTTP calls to the Universal API.
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

        # ADD: Optionally, filter each related record's fields based on role's allowed "view" fields from settings.
        # Example: For each record in results[key], only include fields in can_user_view(key, user.role)