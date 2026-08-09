"""
RESTful range query view.

Converts URL path segments into __gte/__lte filters and delegates to WCAPIGetView.

Usage:
    GET /wcapi/order/dt_created/2026-01-01/2026-01-31/
    GET /wcapi/invoice/total/100/500/
    GET /wcapi/contact/dt_modified/1719792000000/1720396800000/

Equivalent to:
    GET /wcapi/get/?model_name=order&dt_created__gte=2026-01-01&dt_created__lte=2026-01-31
"""
from rest_framework.views import APIView
from rest_framework import status
from common.api_responses import api_response
from apps.core.views.wcapi import WCAPIGetView


class RangeQueryView(APIView):
    """Translate /model/field/from/to/ into standard wcapi filters."""

    http_method_names = ["get", "options", "head"]

    def get(self, request, model_name=None, field=None, from_val=None, to_val=None, **kwargs):
        if not model_name or not field or from_val is None or to_val is None:
            return api_response(
                success=False,
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Usage: /wcapi/<model>/<field>/<from>/<to>/",
                error={"code": "invalid_range_query"},
            )

        # Build a modified request with range filters as query params
        from django.http import QueryDict
        params = request.GET.copy()
        params['model_name'] = model_name
        params[f'{field}__gte'] = from_val
        params[f'{field}__lte'] = to_val

        # Delegate to the standard get view
        view = WCAPIGetView()
        view.request = request
        request.GET = params
        return view._handle(model_name, None, None, request)
