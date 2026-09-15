"""
Cloudflare Access authentication middleware.

Authenticates a Django user from Cloudflare Access ONLY after verifying the
signed Cf-Access-Jwt-Assertion token against the team's public keys and the
Access application's AUD tag. The email comes from the verified token, never
from the unsigned Cf-Access-Authenticated-User-Email header (any client can
send that header; trusting it allowed logging in as anyone — 2026-09-15).

Required settings / env (both, or header auth is disabled — fail closed):
  CF_ACCESS_TEAM_DOMAIN  e.g. "jpods.cloudflareaccess.com"
  CF_ACCESS_AUD          Application Audience (AUD) tag from Zero Trust → Access → Applications

Behavior:
  - Already authenticated → no-op
  - Valid token → look up Contact by token email, log in (create role=guest if missing)
  - Missing/invalid token, or settings unset → fall through to normal Django auth

For local dev without Cloudflare: set CF_ACCESS_DEV_EMAIL env var (only works when DEBUG=True).
"""

import logging
import os
import subprocess
import uuid

import jwt
from django.conf import settings
from django.contrib.auth import login

logger = logging.getLogger(__name__)

CF_JWT_HEADER = "HTTP_CF_ACCESS_JWT_ASSERTION"
CF_TEAM_DOMAIN = (getattr(settings, "CF_ACCESS_TEAM_DOMAIN", "") or os.environ.get("CF_ACCESS_TEAM_DOMAIN", "")).strip().rstrip("/")
CF_AUD = (getattr(settings, "CF_ACCESS_AUD", "") or os.environ.get("CF_ACCESS_AUD", "")).strip()
# DEV_EMAIL only honored when DEBUG=True — never in production
DEV_EMAIL = os.environ.get("CF_ACCESS_DEV_EMAIL", "") if getattr(settings, 'DEBUG', False) else ""


_jwks_client = None


def _verified_access_email(request) -> str:
    """Return the email from a verified Cloudflare Access JWT, or "" if absent/invalid/unconfigured."""
    global _jwks_client
    token = request.META.get(CF_JWT_HEADER, "")
    if not token:
        return ""
    if not (CF_TEAM_DOMAIN and CF_AUD):
        logger.warning("Cloudflare Access token received but CF_ACCESS_TEAM_DOMAIN/CF_ACCESS_AUD unset — header auth disabled")
        return ""
    try:
        if _jwks_client is None:
            host = CF_TEAM_DOMAIN if CF_TEAM_DOMAIN.startswith("http") else f"https://{CF_TEAM_DOMAIN}"
            _jwks_client = jwt.PyJWKClient(f"{host}/cdn-cgi/access/certs")
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=CF_AUD,
            issuer=CF_TEAM_DOMAIN if CF_TEAM_DOMAIN.startswith("http") else f"https://{CF_TEAM_DOMAIN}",
        )
    except jwt.PyJWTError as exc:
        logger.warning("Cloudflare Access token rejected: %s", exc)
        return ""
    return (claims.get("email") or "").strip().lower()


class CloudflareAccessMiddleware:
    """Auto-authenticate users via Cloudflare Access email header."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip if user is already authenticated
        if hasattr(request, "user") and request.user.is_authenticated:
            return self.get_response(request)

        email = _verified_access_email(request) or DEV_EMAIL
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

            # Log in without password — email came from a signature-verified Access token
            login(request, contact, backend="django.contrib.auth.backends.ModelBackend")

            # Alice observation — track CF login for behavior analysis
            try:
                _alice_script = "/opt/andi/scripts/alice-observe.py"
                if os.path.exists(_alice_script):
                    subprocess.Popen(
                        ["python3", _alice_script, "--event", "cf_login", "--email", email, "--path", request.path],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    )
            except OSError:
                logger.debug("Alice observe script not available at %s", _alice_script)

        except Exception:
            logger.exception("Cloudflare auth failed for %s", email)

        return self.get_response(request)
