"""
Form Library endpoint — serves the catalog of form Report records
and handles checkout/submit operations.

GET  /wcapi/sync/form-library/                → catalog of available forms
GET  /wcapi/sync/form-library/?model=customer  → forms for one model
POST /wcapi/sync/form-library/checkout/        → check out a form by uuid
POST /wcapi/sync/form-library/submit/          → submit a form back to library

The library source of truth is Andi/Alice. Local installations check out
forms on demand. Each checked-out form carries its library original in
config.library_original for restore. Users can edit locally, save as new,
or submit improvements back.

LastChecked: 2026-08-07 | WhereUsed: ReportsDialog | WhoCreated: Bill+Claude
"""
from __future__ import annotations

import logging
import time

import requests as http_requests
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView

from apps.core.models import Report
from apps.sync.models.connection import Connection
from apps.sync.models.bundle import Bundle
from common.api_responses import api_response

logger = logging.getLogger(__name__)


def _valid_sync_key(request):
    """Check if the request carries a valid X-Sync-Key header."""
    key = request.headers.get('X-Sync-Key', '')
    if not key:
        return False
    for conn in Connection.objects.filter(status='active', is_active=True):
        conn_key = (conn.config or {}).get('key', '')
        if conn_key and conn_key == key:
            return True
    return False


class FormLibraryCatalogView(APIView):
    """GET — return catalog of form reports available in the local library.

    On Andi, this is the full library. On local installations, this returns
    what's available locally. The React UI calls Andi's endpoint directly
    for the canonical catalog.

    Auth: X-Sync-Key header (machine-to-machine) or Django session/JWT.
    """
    # Use default DRF auth (JWT/session) for browser users.
    # X-Sync-Key checked manually in get() for machine-to-machine.
    permission_classes = [AllowAny]

    def get(self, request):
        if not (request.user and request.user.is_authenticated) and not _valid_sync_key(request):
            return api_response(success=False, status_code=401, error={'code': 'not_authenticated', 'details': 'Authentication required'})

        model_filter = request.query_params.get('model', '')
        source = request.query_params.get('source', '')

        # If source=library, proxy the request to the library server (Andi)
        if source == 'library':
            return self._proxy_to_library(model_filter)

        qs = Report.objects.filter(is_active=True, category='form')
        if model_filter:
            qs = qs.filter(model_name=model_filter)

        catalog = []
        for r in qs.order_by('model_name', 'name'):
            cfg = r.config or {}
            # Form data may be in config.form (PrintLayout) or directly in config (rows/fields)
            form = cfg.get('form', {})
            if isinstance(form, dict) and (form.get('rows') or form.get('fields')):
                rows = form.get('rows', [])
                fields = form.get('fields', {})
            else:
                rows = cfg.get('rows', [])
                fields = cfg.get('fields', {})
            catalog.append({
                'id': r.id,
                'uuid': str(r.uuid),
                'ida': r.ida,
                'name': r.name,
                'model_name': r.model_name,
                'description': r.description,
                'category': r.category,
                'row_count': len(rows),
                'field_count': len(fields),
                'dt_modified': r.dt_modified,
                'version': r.version,
            })

        return api_response(data={
            'forms': catalog,
            'total': len(catalog),
            'source': 'local',
        })

    def _proxy_to_library(self, model_filter):
        """Proxy the catalog request to the library server (Andi) via Connection."""
        conn = Connection.objects.filter(name='Mac-Andi', is_active=True).first()
        if not conn:
            return api_response(success=False, status_code=400, error={'code': 'no_library_connection_configur', 'details': 'No library connection configured'})

        cfg = conn.config or {}
        endpoint = cfg.get('endpoint', '')
        key = cfg.get('key', '')
        if not endpoint or not key:
            return api_response(success=False, status_code=400, error={'code': 'library_connection_missing_end', 'details': 'Library connection missing endpoint or key'})

        # Build the library URL from the receive endpoint
        # endpoint is like http://192.168.1.114/wcapi/sync/receive/
        # we need       http://192.168.1.114/wcapi/sync/form-library/
        base = endpoint.rsplit('/receive', 1)[0]
        library_url = f'{base}/form-library/'

        params = {}
        if model_filter:
            params['model'] = model_filter

        try:
            resp = http_requests.get(
                library_url,
                params=params,
                headers={'X-Sync-Key': key},
                timeout=10,
            )
        except http_requests.RequestException as e:
            return api_response(success=False, status_code=502, error={'code': 'library_error', 'details': f'Library connection failed: {e}'})

        if resp.status_code != 200:
            return api_response(success=False, status_code=502, error={'code': 'library_error', 'details': f'Library returned {resp.status_code}'})

        data = resp.json().get('data', resp.json())
        data['source'] = 'library'
        return api_response(data=data)


class FormLibraryCheckoutView(APIView):
    """POST — check out a form from the library connection.

    Body: { "uuid": "...", "connection_id": N }

    Pulls the form from the remote library (via the Connection endpoint),
    saves it locally as a Report with config.library_original preserving
    the canonical version for restore.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        uuid_str = request.data.get('uuid')
        form_data = request.data.get('form_data')

        if not uuid_str:
            return api_response(success=False, status_code=400, error={'code': 'uuid_is_required', 'details': 'uuid is required'})

        if not form_data:
            return api_response(success=False, status_code=400, error={'code': 'form_data_is_required', 'details': 'form_data is required'})

        # Check if we already have this form locally
        existing = Report.objects.filter(uuid=uuid_str).first()

        config = form_data.get('config', {})
        # Preserve the library original for restore
        config['library_original'] = {
            'form': config.get('form', {}),
            'checked_out_at': int(time.time() * 1000),
            'source_uuid': uuid_str,
        }

        if existing:
            # Update existing — keep local edits in place, update library_original
            existing_config = existing.config or {}
            existing_config['library_original'] = config['library_original']
            existing.config = existing_config
            existing.save(update_fields=['config', 'dt_modified', 'version'])
            action = 'updated'
        else:
            # Create new local report from library
            existing = Report.objects.create(
                uuid=uuid_str,
                ida=form_data.get('ida', ''),
                name=form_data.get('name', ''),
                model_name=form_data.get('model_name', ''),
                description=form_data.get('description', ''),
                category=form_data.get('category', 'form'),
                output_type=form_data.get('output_type', 'screen'),
                config=config,
            )
            action = 'created'

        # Record the checkout as a Bundle
        connection = Connection.objects.filter(
            name='Mac-Andi', is_active=True
        ).first()
        if connection:
            Bundle.objects.create(
                connection=connection,
                direction='pull',
                status='success',
                config={
                    'action': 'form_checkout',
                    'form_uuid': uuid_str,
                    'form_name': existing.name,
                },
                payload={'uuid': uuid_str},
                response={'action': action, 'local_id': existing.id},
            )

        return api_response(data={
            'action': action,
            'report_id': existing.id,
            'uuid': str(existing.uuid),
            'name': existing.name,
        })


class FormLibrarySubmitView(APIView):
    """POST — submit a local form improvement back to the library.

    Body: { "report_id": N }

    Packages the local Report record as a Bundle and sends it upstream.
    For now (just us), this creates the Bundle record — Andi picks it up.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        report_id = request.data.get('report_id')
        if not report_id:
            return api_response(success=False, status_code=400, error={'code': 'report_id_is_required', 'details': 'report_id is required'})

        try:
            report = Report.objects.get(id=report_id, is_active=True)
        except Report.DoesNotExist:
            return api_response(success=False, status_code=404, error={'code': 'report_not_found', 'details': 'Report not found'})

        connection = Connection.objects.filter(
            name='Mac-Andi', is_active=True
        ).first()
        if not connection:
            return api_response(success=False, status_code=400, error={'code': 'no_wc_hq_connection_configured', 'details': 'No WC_HQ connection configured'})

        # Package the form as a bundle
        payload = {
            'uuid': str(report.uuid),
            'ida': report.ida,
            'name': report.name,
            'model_name': report.model_name,
            'description': report.description,
            'category': report.category,
            'config': report.config,
        }

        bundle = Bundle.objects.create(
            connection=connection,
            direction='push',
            status='pending',
            config={
                'action': 'form_submission',
                'form_uuid': str(report.uuid),
                'form_name': report.name,
                'submitted_by': request.user.username if request.user else 'unknown',
            },
            payload=payload,
        )

        return api_response(data={
            'bundle_id': bundle.id,
            'status': 'submitted',
            'uuid': str(report.uuid),
            'name': report.name,
        })


class FormLibraryRestoreView(APIView):
    """POST — restore a form to its library original.

    Body: { "report_id": N }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        report_id = request.data.get('report_id')
        if not report_id:
            return api_response(success=False, status_code=400, error={'code': 'report_id_is_required', 'details': 'report_id is required'})

        try:
            report = Report.objects.get(id=report_id, is_active=True)
        except Report.DoesNotExist:
            return api_response(success=False, status_code=404, error={'code': 'report_not_found', 'details': 'Report not found'})

        config = report.config or {}
        library_original = config.get('library_original', {})
        original_form = library_original.get('form')

        if not original_form:
            return api_response(success=False, status_code=400, error={'code': 'no_library_original_found__thi', 'details': 'No library original found — this form was not checked out from the library'})

        config['form'] = original_form
        report.config = config
        report.save(update_fields=['config', 'dt_modified', 'version'])

        return api_response(data={
            'report_id': report.id,
            'name': report.name,
            'restored': True,
        })
