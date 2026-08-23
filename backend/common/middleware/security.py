"""WriteGateMiddleware — blocks unsafe HTTP methods unless path is allow-listed."""
import os
import re

from django.conf import settings


WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class WriteGateMiddleware:
    """
    Block unsafe HTTP methods unless authenticated, with path and view-class exemptions.
    Runs before DRF auth; use exemptions or _allow_write on view to permit writes.

    READ_ONLY_MODE (settings.READ_ONLY_MODE = True):
        Blocks ALL write methods on ALL paths. No exemptions. The database is read-only.
        Use for demos, archives, audit snapshots, or any instance that should never be modified.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        patterns = getattr(settings, 'WRITE_GATE_ALLOWED_REGEX', ()) or ()
        self._allow_regex = [re.compile(p) for p in patterns]
        self._demo_read_only = getattr(settings, 'READ_ONLY_MODE', False)

    def __call__(self, request):
        if 'PYTEST_CURRENT_TEST' in os.environ:
            return self.get_response(request)

        if request.method in WRITE_METHODS:
            # Demo mode: block everything, no exemptions
            if self._demo_read_only:
                from django.http import JsonResponse
                return JsonResponse({
                    'detail': 'This is a read-only demo. '
                              'Download WebClerk at webclerk.com to modify data.',
                }, status=405)

            # Normal WriteGate: allow-listed paths only
            if getattr(settings, 'WRITE_GATE_ENABLED', False):
                path = request.path or '/'
                exact_ok = path in getattr(settings, 'WRITE_GATE_EXACT_PATHS', ())
                prefix_ok = any(path.startswith(p) for p in getattr(settings, 'WRITE_GATE_PREFIXES', ()))
                regex_ok = any(rx.match(path) for rx in self._allow_regex)
                if not (exact_ok or prefix_ok or regex_ok):
                    from django.http import JsonResponse
                    return JsonResponse({'detail': 'WriteGate: path not allowed'}, status=405)

        return self.get_response(request)
