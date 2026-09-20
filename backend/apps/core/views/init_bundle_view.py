"""Serve the recommended set — what WC_HQ publishes to installations.

    GET /wcapi/get/bundle_gls.json          chart of accounts + posting-role map
    GET /wcapi/get/bundle_reports.json      report, form, print and tally definitions
    GET /wcapi/get/bundle_settings.json     layouts, select lists, configuration
    GET /wcapi/get/bundle_init.json         everything a new database starts from

    GET /wcapi/init-bundle/                 the shipped file, unchanged (db_init)

No authentication. These carry system configuration only — no business data.
What goes in each bundle is declared once, in
apps/core/services/bundle_catalogue.py.

On webclerk.com these are packed live from the HQ database, so the
recommendation is current. Any other installation answers from its shipped
init-bundle.json, so a company HQ can serve its own locations without
running a packer.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings as dj_settings
from django.http import JsonResponse
from django.views import View

logger = logging.getLogger(__name__)

BUNDLE_PATH = Path(__file__).resolve().parent.parent.parent.parent / 'init-bundle.json'


def _is_hq() -> bool:
    """Whether this installation publishes bundles of its own.

    WC_HQ packs live from its database. Everyone else serves the shipped file.
    """
    return bool(getattr(dj_settings, 'WCHQ_IS_HQ', False))


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
            return JsonResponse({'error': 'Failed to read init-bundle'}, status=500)


class NamedBundleView(View):
    """Serve one named bundle from the catalogue."""

    def get(self, request, name: str):
        from apps.core.services.bundle_catalogue import CATALOGUE

        spec = CATALOGUE.get(name)
        if spec is None:
            return JsonResponse(
                {'error': f'Unknown bundle "{name}". '
                          f'Known: {", ".join(sorted(CATALOGUE))}.'},
                status=404,
            )

        try:
            payload = spec.pack() if _is_hq() else self._from_shipped_file(spec)
        except Exception as exc:
            logger.exception('[INIT_BUNDLE] could not pack bundle "%s"', name)
            return JsonResponse({'error': f'Failed to pack bundle: {exc}'}, status=500)

        if payload is None:
            return JsonResponse(
                {'error': 'init-bundle.json not found — run pack_init_bundle first'},
                status=404,
            )

        payload = {
            'version': '1.0',
            'bundle': name,
            'description': spec.description,
            'source': 'wchq' if _is_hq() else 'shipped',
            'dt_exported': datetime.now(timezone.utc).isoformat(),
            **payload,
        }
        for key in ('settings', 'reports', 'gl_accounts'):
            if key in payload:
                payload[f'{key}_count'] = len(payload[key])
        return JsonResponse(payload, safe=False)

    def _from_shipped_file(self, spec):
        """The subset of the shipped bundle this named bundle covers."""
        if not BUNDLE_PATH.exists():
            return None
        with open(BUNDLE_PATH) as f:
            shipped = json.load(f)

        if spec.name == 'init':
            return {k: shipped.get(k, []) for k in ('settings', 'reports', 'gl_accounts')
                    if k in shipped}
        if spec.name == 'reports':
            return {'reports': shipped.get('reports', [])}
        if spec.name == 'settings':
            return {'settings': shipped.get('settings', [])}
        if spec.name == 'gls':
            company = [s for s in shipped.get('settings', [])
                       if s.get('purpose') == 'wc:company_profile'
                       and (s.get('config') or {}).get('gl_defaults')]
            for rec in company:
                rec['config'] = {'gl_defaults': rec['config']['gl_defaults']}
            return {'gl_accounts': shipped.get('gl_accounts', []), 'settings': company}
        return {}
