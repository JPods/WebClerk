"""The REST channel — the one HTTP shape for every model (Bill, 2026-09-24: REST only).

    GET    /wcapi/<model>/            get (a list; criteria in the query string)
    GET    /wcapi/<model>/<id>/       get (one record)
    POST   /wcapi/<model>/            save (create)
    PUT    /wcapi/<model>/<id>/       save (update)
    PATCH  /wcapi/<model>/<id>/       save (update)
    DELETE /wcapi/<model>/<id>/       delete

The HTTP method names the verb; the path names the model and the record. Every method ends
in the same door as every other channel — ``save_record``, ``delete_record`` — with its
hooks (services/verbs.py). Commands (convert, receive, pay, …) will be
``POST /wcapi/<model>/<id>/<command>/``. Plan: Allie
``readmes/assessments/2026-09-24-one-route-per-verb.md``.
"""
from __future__ import annotations

from rest_framework.permissions import AllowAny

from apps.core.services.verbs import METHOD_VERBS
from common.decorators import allow_write
from common.api_responses import api_response
from apps.core.views.save_view import SaveWcapiView


@allow_write
class ModelChannelView(SaveWcapiView):
    """Each method checks who is asking itself: a get may be public, a save or a delete may
    not — the door decides, not a permission class in front of it."""

    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'options', 'head']
    permission_classes = [AllowAny]

    def get(self, request, model_name: str, record_id=None):
        # Read-door step 2 makes get a verb like the others; until then the read channel
        # answers, told the model and the record by the path.
        from apps.core.views.wcapi import WCAPIGetView
        request.query_params._mutable = True
        request.query_params['model_name'] = model_name
        if record_id is not None:
            request.query_params['id'] = str(record_id)
        request.query_params._mutable = False
        return WCAPIGetView().get(request)

    def post(self, request, model_name: str, record_id=None):
        if record_id is not None:
            return _wrong_method('POST', model_name, record_id)
        return self.save(request, model_name, None)

    def put(self, request, model_name: str, record_id=None):
        if record_id is None:
            return _wrong_method('PUT', model_name, None)
        return self.save(request, model_name, record_id)

    patch = put

    def delete(self, request, model_name: str, record_id=None):
        if record_id is None:
            return _wrong_method('DELETE', model_name, None)
        from apps.core.views.wcapi import delete_response
        return delete_response(request, model_name, record_id)


def _wrong_method(method: str, model_name: str, record_id):
    where = f'/wcapi/{model_name}/' + (f'{record_id}/' if record_id is not None else '')
    hint = ('POST /wcapi/<model>/ creates; PUT or PATCH /wcapi/<model>/<id>/ updates; '
            'DELETE /wcapi/<model>/<id>/ deletes.')
    return api_response(success=False, status_code=405,
                        message=f'{method} {where} is not a verb. {hint}',
                        error={'code': 'method_not_allowed',
                               'details': {'method': method, 'path': where,
                                           'verbs': METHOD_VERBS}})
