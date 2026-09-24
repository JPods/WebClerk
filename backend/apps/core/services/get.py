"""The get service — get is a verb like save and delete (read-door step 2, REST).

    GET /wcapi/<model>/        read_records: criteria in the query string
    GET /wcapi/<model>/<id>/   read_record

Same structure as every verb: code before → user before → base → code after → user after
(services/verbs.py). The base is the one read channel (``WCAPIGetView``: visibility first,
then criteria, paging, projection). A command, a task or Alice reads through ``read`` with
an actor and a mapping — no request — and gets what the web gets.

The reader still speaks "request" inside; ``_ReadRequest`` is what it is given — the
actor rides along, so every ``Actor.from_request`` inside answers with it. Moving the
reader's 34 methods off the request is later, mechanical work; the verb, its hooks and its
callers do not change when it happens.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from django.http import QueryDict

from apps.core.services import verbs
from apps.core.services.behaviours import HookContext
from apps.core.services.door import Actor, Refused, resolve_model


class _Anonymous:
    is_authenticated = False
    is_staff = False
    is_superuser = False
    pk = None
    id = None


@dataclass
class _ReadRequest:
    wc_actor: Actor
    query_params: QueryDict
    META: dict = field(default_factory=dict)
    body: bytes = b''
    content_type: str = ''
    path: str = ''

    @property
    def user(self):
        return self.wc_actor.user or _Anonymous()

    @property
    def GET(self):
        return self.query_params


def read(actor: Actor, model_key: str, record_id=None,
         params: Optional[Mapping[str, Any]] = None) -> dict:
    """One record (``record_id``) or a page of records (criteria in ``params``).

    Returns the payload the channel sends; raises ``Refused`` with the reader's status,
    code and message.
    """
    _cls, model_key, _norm = resolve_model(model_key)
    query = QueryDict(mutable=True)
    for key, value in (params or {}).items():
        if isinstance(value, (list, tuple)):
            query.setlist(key, [str(v) for v in value])
        elif value is not None:
            query[key] = str(value)
    query['model_name'] = model_key
    if record_id is not None:
        query['id'] = str(record_id)

    ctx = HookContext(actor=actor, verb='get', model_key=model_key, obj=None,
                      data={'id': record_id, **dict(params or {})})
    verbs.before(ctx)
    result = _base(actor, model_key, record_id, query)
    ctx.data['result'] = result
    verbs.after(ctx)
    return ctx.data['result']


def _base(actor: Actor, model_key: str, record_id, query: QueryDict) -> dict:
    from apps.core.views.wcapi import WCAPIGetView
    request = _ReadRequest(wc_actor=actor, query_params=query,
                           path=f'/wcapi/{model_key}/' + (f'{record_id}/' if record_id else ''))
    reader = WCAPIGetView()
    if actor.kind == 'public':
        response = reader._public(request, model_key, record_id)
    else:
        response = reader._handle(model_key, record_id, None, request)
    body = response.data if isinstance(response.data, dict) else {}
    if response.status_code >= 400:
        error = body.get('error') or {}
        code = error.get('code') if isinstance(error, dict) else None
        raise Refused(response.status_code, code or 'read_refused',
                      body.get('message') or body.get('detail') or 'Read refused',
                      error.get('details') if isinstance(error, dict) else error)
    return body.get('data') if 'data' in body else body
