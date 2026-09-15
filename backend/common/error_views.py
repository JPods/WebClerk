"""Custom 404/500 handlers returning unified envelope.

Add to root urls.py:
handler404 = 'common.error_views.error_404'
handler500 = 'common.error_views.error_500'
"""
from django.http import HttpRequest
from django.http import JsonResponse


def error_404(request: HttpRequest, exception):  # pragma: no cover (framework hook)
    payload = {
        'status': 'fail',
        'error': {'code': 'not_found', 'details': 'Not found'},
        'code': 404,
        'message': 'Not found',
        'data': None,
    }
    return JsonResponse(payload, status=404)


def error_500(request: HttpRequest):  # pragma: no cover
    payload = {
        'status': 'error',
        'error': {'code': 'server_error', 'details': 'Server error'},
        'code': 500,
        'message': 'Server error',
        'data': None,
    }
    return JsonResponse(payload, status=500)
