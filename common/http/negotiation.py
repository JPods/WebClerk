from rest_framework.negotiation import BaseContentNegotiation
from rest_framework.renderers import JSONRenderer

class JSONOnlyNegotiation(BaseContentNegotiation):
    """
    Always select JSONRenderer, ignoring Accept headers.
    """
    def select_renderer(self, request, renderers, format_suffix=None):
        for renderer in renderers:
            if isinstance(renderer, JSONRenderer) or renderer.media_type == "application/json":
                return (renderer, renderer.media_type)
        # Fallback to first renderer (should be JSON per settings)
        return (renderers[0], renderers[0].media_type)