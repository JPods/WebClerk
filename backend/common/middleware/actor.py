"""request.actor — who is asking, built once per call and gone with the response.

Bill's WC2 kept an identity object for each server call, cleared on response
(2026-09-23: "define a identity object at each server call that was cleared on response").
The Actor is that object: it holds the Django user — it does not replace or subclass it —
and carries the behaviours every door reads (role, scope, level ceiling, act-as, describe).

It is lazy on purpose. DRF authenticates inside the view, after every Django middleware has
run, so an Actor built here would see an anonymous user on every token-authenticated call.
Built on first read, it sees the authenticated user and any validated act-as. Nothing may
read request.actor before the view: a middleware that did would fix the identity too early.
"""
from django.utils.functional import SimpleLazyObject

from apps.core.services.door import Actor


class ActorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.actor = SimpleLazyObject(lambda: Actor.from_request(request))
        return self.get_response(request)
