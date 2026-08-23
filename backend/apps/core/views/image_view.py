"""
Image Library View — serves images through Alice's resolution pipeline.

GET /wcapi/image/{model}/{ida}/tn.png
GET /wcapi/image/{model}/{ida}/display.png
GET /wcapi/image/{model}/{ida}/hires.png

Returns PNG bytes with cache headers. Falls through:
  local → remote library → placeholder.
"""

from django.http import HttpResponse, HttpResponseNotFound
from rest_framework.views import APIView

from apps.core.services.image_library import resolve_image, VALID_SIZES


class ImageView(APIView):
    """Serve images from the library pipeline."""

    # Allow unauthenticated access for images (public catalog use)
    authentication_classes = []
    permission_classes = []

    def get(self, request, model_name: str, ida: str, size: str):
        # Strip .png extension if present
        size = size.replace('.png', '')

        if size not in VALID_SIZES:
            return HttpResponseNotFound(
                f"Unknown size '{size}'. Use: {', '.join(sorted(VALID_SIZES))}"
            )

        result = resolve_image(model_name, ida, size)

        if not result.get('bytes'):
            return HttpResponseNotFound('Image not found')

        response = HttpResponse(
            result['bytes'],
            content_type=result.get('content_type', 'image/png'),
        )

        # Cache headers — images don't change often
        if result['source'] == 'local':
            response['Cache-Control'] = 'public, max-age=86400'  # 24h
        elif result['source'] == 'placeholder':
            response['Cache-Control'] = 'public, max-age=3600'   # 1h (may get a real image soon)
        else:
            response['Cache-Control'] = 'public, max-age=43200'  # 12h

        response['X-Image-Source'] = result.get('source', 'unknown')
        return response
