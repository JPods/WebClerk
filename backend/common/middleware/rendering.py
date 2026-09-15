"""EnsureRenderedMiddleware — forces TemplateResponse rendering before downstream access."""
from django.utils.deprecation import MiddlewareMixin


class EnsureRenderedMiddleware(MiddlewareMixin):
    """Ensure TemplateResponse/DRF Response objects are rendered before other
    middlewares access response.content.

    Place this before Django's CommonMiddleware to avoid ContentNotRenderedError
    when that middleware sets Content-Length.
    """

    def process_response(self, request, response):  # pragma: no cover
        try:
            if hasattr(response, 'render') and getattr(response, '_is_rendered', False) is False:
                response.render()  # type: ignore[attr-defined]
        except Exception:
            pass
        return response
