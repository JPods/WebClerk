"""SecretGuardMiddleware — Alice refuses to store a password typed into a shared record.

Every JSON write (POST/PUT/PATCH) is scanned with apps.core.utils.secret_guard before
any view runs: notes, comments, actions, documents, Alice chat, feedback, bundles.
A hit returns 422 with a message that tells the user what happened and what to do.
Nothing is stored and the value is never logged.

Exempt on purpose — these are the places a password is supposed to go, and they hash it:
  - login/token endpoints and password-change endpoints
  - keys that ARE the password field of a password form (password, new_password, ...)

Multipart bodies (file uploads) are not scanned here; Andi's nightly sweep covers stored
text that arrives by any path this gate does not see.
"""
import json
import logging

from django.http import JsonResponse

from apps.core.utils.secret_guard import correction, scan_obj

logger = logging.getLogger("secret_guard")

SCANNED_METHODS = {"POST", "PUT", "PATCH"}
EXEMPT_PATH_PARTS = ("/token", "login", "password", "/logout")
PASSWORD_FORM_KEYS = {
    "password", "password1", "password2", "new_password", "new_password1", "new_password2",
    "old_password", "current_password", "confirm_password", "password_confirm",
}


def _strip_password_form_keys(obj):
    if isinstance(obj, dict):
        return {k: _strip_password_form_keys(v) for k, v in obj.items()
                if str(k).lower() not in PASSWORD_FORM_KEYS}
    if isinstance(obj, list):
        return [_strip_password_form_keys(v) for v in obj]
    return obj


class SecretGuardMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method in SCANNED_METHODS and not any(p in request.path.lower() for p in EXEMPT_PATH_PARTS):
            blocked = self._check(request)
            if blocked is not None:
                return blocked
        return self.get_response(request)

    def _check(self, request):
        ctype = (request.META.get("CONTENT_TYPE") or "").lower()
        if "json" not in ctype:
            return None
        try:
            body = json.loads(request.body or b"{}")
        except (ValueError, UnicodeDecodeError):
            return None  # malformed JSON is the view's problem, not a secret
        findings = scan_obj(_strip_password_form_keys(body))
        if not findings:
            return None
        user = getattr(request, "user", None)
        logger.warning(
            "[SecretGuard] blocked path=%s user=%s findings=%s",
            request.path, getattr(user, "pk", None),
            [{"field": p, "kind": f.kind, "label": f.label, "length": f.length} for p, f in findings],
        )
        message = correction([f for _, f in findings], where="WebClerk records")
        return JsonResponse({
            "success": False,
            "status": "fail",
            "code": 422,
            "message": message,
            "error": {
                "code": "secret_detected",
                "details": message,
                "fields": sorted({p for p, _ in findings}),
            },
        }, status=422)
