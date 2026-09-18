"""Serve the current init-bundle as JSON.

WCHQ endpoint: GET /wcapi/init-bundle/
New WC3 instances call this to fetch the latest approved baseline
(Settings + Reports) during db_init.

No authentication required — init-bundles contain no business data,
only system configuration (layouts, select lists, coaching, reports).
"""
import json
import logging
from pathlib import Path

from django.http import JsonResponse
from django.views import View

logger = logging.getLogger(__name__)

BUNDLE_PATH = Path(__file__).resolve().parent.parent.parent.parent / 'init-bundle.json'


class InitBundleView(View):
    """Serve init-bundle.json for db_init consumers."""

    def get(self, request):
        if not BUNDLE_PATH.exists():
            return JsonResponse(
                {'error': 'init-bundle.json not found — run pack_init_bundle first'},
                status=404,
            )
        try:
            with open(BUNDLE_PATH) as f:
                bundle = json.load(f)
            return JsonResponse(bundle, safe=False)
        except Exception as e:
            logger.error(f'[INIT_BUNDLE] Failed to serve bundle: {e}')
            return JsonResponse(
                {'error': 'Failed to read init-bundle'},
                status=500,
            )
