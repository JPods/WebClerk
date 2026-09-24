"""The REST channel — the one HTTP shape for every model (Bill, 2026-09-24: REST only).

    GET    /wcapi/<model>/            get (a list; criteria in the query string)
    GET    /wcapi/<model>/<id>/       get (one record)
    POST   /wcapi/<model>/            save (create)
    PUT    /wcapi/<model>/<id>/       save (update)
    PATCH  /wcapi/<model>/<id>/       save (update)
    DELETE /wcapi/<model>/<id>/       delete

The HTTP method names the verb; the path names the model and the record. Every method ends
in the same door as every other channel — ``save_record``, ``delete_record`` — with its
hooks (services/verbs.py). A command is ``POST /wcapi/<model>/<id>/<command>/`` and runs
``verbs.run_command``; a gateway's webhook is ``POST /wcapi/<model>/_receive/<provider>/``,
the one route the public reaches. Plan: Allie
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
        from apps.core.services.door import Actor, Refused
        from apps.core.services.get import read
        params = {k: (v if len(v) > 1 else v[0]) for k, v in request.query_params.lists()
                  if k not in ('model_name', 'id')}
        try:
            data = read(Actor.from_request(request), model_name, record_id, params)
        except Refused as refused:
            return api_response(success=False, status_code=refused.status,
                                message=refused.message, error=refused.as_error())
        return api_response(data=data)

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


class CommandChannelView(SaveWcapiView):
    """POST /wcapi/<model>/<id>/<command>/ — a command on one record (pay, refund, …)."""

    http_method_names = ['post', 'options']
    permission_classes = [AllowAny]          # the command decides who may (verbs.run_command)

    def post(self, request, model_name: str, record_id: int, command: str):
        from apps.core.services.door import Actor
        payload = {k: v for k, v in (request.data or {}).items()
                   if k not in ('id', 'model_name')} if isinstance(request.data, dict) else {}
        return _command_response(Actor.from_request(request), command, model_name, record_id,
                                 payload)


class ReceiveChannelView(SaveWcapiView):
    """POST /wcapi/<model>/_receive/<provider>/ — a payment provider's event. Public: the
    provider has no login; the receive command confirms the event with the provider before
    it records anything (plan §11.7d)."""

    http_method_names = ['post']
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, model_name: str, provider: str):
        import json
        from apps.core.services.door import Actor
        try:
            body = json.loads(request.body.decode('utf-8') or '{}')
        except (ValueError, UnicodeDecodeError):
            return api_response(success=False, status_code=400, message='The event is not JSON.',
                                error={'code': 'invalid_json'})
        return _command_response(Actor.anonymous(source=f'receive:{provider}'), 'receive',
                                 model_name, None, {'_provider': provider, '_body': body})


def _command_response(actor, command, model_name, record_id, payload):
    from apps.core.services.door import Refused
    from apps.core.services.verbs import VERBS, run_command
    if command not in VERBS:
        return api_response(success=False, status_code=404,
                            message=f'{command} is not a command.',
                            error={'code': 'unknown_command', 'details': sorted(VERBS)})
    try:
        result = run_command(actor, command, model_name, record_id, payload)
    except Refused as refused:
        return api_response(success=False, status_code=refused.status,
                            message=refused.message, error=refused.as_error())
    data = {'result': result}
    if record_id is not None:
        # After the commit, and after anything the command did then (a gateway's answer).
        from django.forms.models import model_to_dict
        from apps.core.services.door import resolve_model
        model_cls = resolve_model(model_name)[0]
        obj = model_cls.objects.filter(pk=record_id).first()
        if obj is not None:
            data['record'] = model_to_dict(obj, fields=[f.name for f in obj._meta.concrete_fields])
    return api_response(data=data)
