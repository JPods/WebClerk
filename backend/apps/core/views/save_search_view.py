"""Save Search — a stored search is a Report record, shared by everyone who reads its model.

    purpose = 'search_stored'      what makes it a search and not a print form
    target_model                    what it searches
    config                          the search spec (keyword, filters, ordering, rules...)
    role_required                   empty = everyone who reads the model; a role = that role

A search belongs to no person (Bill, 2026-10-28: "They are not associated with any specific
user"); one name per model. Anyone signed in whose role reads the model may add, replace or
remove one (Bill, same day). Report records otherwise stay an admin's to write.

POST   /wcapi/_save_search/  {name, target_model, keyword?, filters?, ordering?, rules?, role?}
DELETE /wcapi/_save_search/  {id}
"""
from rest_framework import status
from rest_framework.views import APIView

from apps.core.services import access
from apps.core.services.door import Actor, Refused, acts
from apps.core.services.report_registry import REPORT_PURPOSE_SEARCH
from common.api_responses import api_response

#: What a search keeps. ``rules`` rebuild the query builder's rows.
SPEC_KEYS = ('keyword', 'search_fields', 'filters', 'ordering', 'limit', 'relative_period',
             'request_filters', 'request_keyword', 'rules')


def _may_search(actor: Actor, model_key: str) -> None:
    if actor.user is None:
        raise Refused(401, 'authentication_required', 'Sign in to keep a search.')
    if access.is_portal(actor):
        raise Refused(403, 'saved_search_staff_only', 'Searches are kept by company staff.')
    if not access.is_admin(actor) and not (access.block_for(actor, model_key) or {}).get('view'):
        raise Refused(403, 'saved_search_forbidden',
                      f'Your role may not read {model_key} records, so it may not keep searches of them.',
                      {'model': model_key})


@acts
def save_search(actor: Actor, data: dict) -> dict:
    from apps.core.models.report import Report
    name = (data.get('name') or '').strip()
    target_model = (data.get('target_model') or '').strip()
    if not name or not target_model:
        raise Refused(400, 'search_name_and_model', 'Name the search and the model it searches.')
    _may_search(actor, target_model)
    spec = {k: data[k] for k in SPEC_KEYS if data.get(k) is not None}
    report = (Report.objects.filter(name=name, target_model=target_model, purpose=REPORT_PURPOSE_SEARCH)
              .order_by('-dt_modified').first())
    created = report is None
    if created:
        report = Report(name=name, target_model=target_model, purpose=REPORT_PURPOSE_SEARCH,
                        output_type='screen', category='list')
    report.config = spec
    report.role_required = data.get('role', '') or ''
    report.is_active = True
    report.save()
    return {'id': report.id, 'name': report.name, 'target_model': report.target_model,
            'created': created}


@acts
def remove_search(actor: Actor, data: dict) -> dict:
    from apps.core.models.report import Report
    report = Report.objects.filter(pk=data.get('id'), purpose=REPORT_PURPOSE_SEARCH).first()
    if report is None:
        raise Refused(404, 'search_not_found', 'No saved search with that id.')
    _may_search(actor, report.target_model)
    report.delete()
    return {'id': data.get('id'), 'removed': True}


class SaveSearchView(APIView):
    http_method_names = ["post", "delete", "options", "head"]

    def _answer(self, request, verb):
        try:
            result = verb(Actor.from_request(request), request.data or {})
        except Refused as refused:
            return api_response(success=False, status_code=refused.status,
                                message=refused.message, error={'code': refused.code})
        return api_response(data=result, status_code=status.HTTP_200_OK)

    def post(self, request):
        return self._answer(request, save_search)

    def delete(self, request):
        return self._answer(request, remove_search)
