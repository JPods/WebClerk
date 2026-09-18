"""AutoEnvelopeMiddleware — wraps JSON responses in the canonical ApiEnvelope."""
import json
from typing import Any, Dict

from django.utils.deprecation import MiddlewareMixin

from common.api_responses import build_api_envelope
from common.middleware.helpers import (
    _should_skip_envelope,
    _record_skip,
    is_exempt_path,
)


class AutoEnvelopeMiddleware(MiddlewareMixin):
    """Ensure every JSON response conforms to the canonical ApiEnvelope structure."""

    _SCHEMA_PATH_PREFIXES = ('/api/schema/', '/api/swagger/', '/api/redoc/', '/wcapi/schema/', '/wcapi/swagger/', '/wcapi/redoc/')

    def _is_json_response(self, response) -> bool:
        try:
            ctype = response.get('Content-Type', '')
        except Exception:
            ctype = ''
        return 'application/json' in ctype or hasattr(response, 'data')

    def _extract_payload(self, response):
        try:
            payload = getattr(response, 'data', None)
        except Exception:
            payload = None
        if payload is not None:
            return payload
        try:
            body = response.content.decode('utf-8')
            return json.loads(body) if body else {}
        except Exception:
            return None

    def _already_enveloped(self, response, payload) -> bool:
        if getattr(response, '_api_enveloped', False):
            return True
        if not isinstance(payload, dict):
            return False
        keys = set(payload.keys())
        return {'status', 'code', 'data'}.issubset(keys)

    def _split_payload(self, payload: Any, status_code: int):
        """Return (message, data, error) tuples derived from bare DRF payloads."""
        if not isinstance(payload, dict):
            return '', payload, None

        data_copy: Dict[str, Any] = dict(payload)

        message = str(data_copy.pop('message', '') or '')

        raw_error = data_copy.pop('error', None)
        errors_list = data_copy.pop('errors', None)
        if raw_error is None and errors_list is not None:
            raw_error = {'code': 'validation_error', 'details': errors_list}

        detail = data_copy.pop('detail', None)
        if status_code >= 400:
            if raw_error is None and detail is not None:
                err_code = data_copy.pop('code', None) or 'detail'
                raw_error = {'code': err_code, 'details': detail}
            if not message and detail is not None:
                message = str(detail)
        elif detail is not None:
            data_copy['detail'] = detail

        error = self._normalize_error(raw_error)
        if not message and isinstance(error, dict):
            details = error.get('details')
            if isinstance(details, str):
                message = details
        elif not message and isinstance(raw_error, str):
            message = raw_error

        data_payload = data_copy if data_copy else None
        return message, data_payload, error

    @staticmethod
    def _normalize_error(raw: Any):
        if raw in (None, ''):
            return None
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, (list, tuple)):
            return {'code': 'error_list', 'details': list(raw)}
        return {'code': str(raw), 'details': None}

    def _write_payload(self, response, payload: Dict[str, Any]):
        try:
            setattr(response, 'data', payload)
        except Exception:
            pass
        try:
            response.content = json.dumps(payload).encode('utf-8')
            response['Content-Type'] = 'application/json'
        except Exception:
            pass
        setattr(response, '_api_enveloped', True)

    def process_response(self, request, response):  # pragma: no cover (integration focused)
        try:
            path = getattr(request, 'path', '') or ''

            if any(path.startswith(p) for p in self._SCHEMA_PATH_PREFIXES):
                return response

            skip_envelope, skip_reason = _should_skip_envelope(request, response)
            if skip_envelope:
                if skip_reason:
                    _record_skip(path, skip_reason, getattr(response, 'status_code', 200))
                return response

            if is_exempt_path(path):
                return response

            if not self._is_json_response(response):
                return response

            payload = self._extract_payload(response)
            if payload is None:
                return response

            status_code = getattr(response, 'status_code', 200)

            if self._already_enveloped(response, payload):
                return response

            message, data_payload, error = self._split_payload(payload, status_code)

            envelope = build_api_envelope(data=data_payload, message=message, status_code=status_code, error=error)
            self._write_payload(response, envelope)
            return response
        except Exception:
            return response
