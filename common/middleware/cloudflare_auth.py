"""
Cloudflare Access authentication middleware.

Reads the Cf-Access-Authenticated-User-Email header set by Cloudflare Access
and auto-authenticates the Django user. No password needed.

Place after django.contrib.auth.middleware.AuthenticationMiddleware in MIDDLEWARE.

Behavior:
  - If CF header present and user already authenticated → no-op
  - If CF header present and user anonymous → look up Contact by email, log in
  - If CF header present and no Contact exists → create one (role=guest)
  - If no CF header → fall through to normal Django auth (password, session, etc.)

For local dev without Cloudflare: set CF_ACCESS_DEV_EMAIL env var to simulate.
"""

import logging
import os
import uuid

from django.contrib.auth import login

logger = logging.getLogger(__name__)

CF_EMAIL_HEADER = "HTTP_CF_ACCESS_AUTHENTICATED_USER_EMAIL"
DEV_EMAIL = os.environ.get("CF_ACCESS_DEV_EMAIL", "")


class CloudflareAccessMiddleware:
    """Auto-authenticate users via Cloudflare Access email header."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip if user is already authenticated
        if hasattr(request, "user") and request.user.is_authenticated:
            return self.get_response(request)

        email = request.META.get(CF_EMAIL_HEADER, "") or DEV_EMAIL
        if not email:
            return self.get_response(request)

        email = email.strip().lower()

        try:
            from apps.core.models import Contact
            contact = Contact.objects.filter(email=email).first()

            if not contact:
                contact = Contact.objects.create_user(
                    email=email,
                    name_first="",
                    name_last="",
                    role="guest",
                )
                contact.uuid = uuid.uuid4()
                contact.save(update_fields=["uuid"])
                logger.info("Cloudflare auth: created contact %s for %s", contact.id, email)

            # Log in without password — Cloudflare already verified the email
            login(request, contact, backend="django.contrib.auth.backends.ModelBackend")

        except Exception:
            logger.exception("Cloudflare auth failed for %s", email)

        return self.get_response(request)
