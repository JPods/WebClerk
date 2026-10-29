"""Select lists — read and change one model field's list (select_lists.py).

A login flagged is_staff changes lists (Bill, 2026-10-29: support, not police). The browser
calls this when a save comes back value_not_listed and the person says yes, and from the
select-list editor.

POST /wcapi/_selectlist/  {model, field, add: value, label?}       one value joins the list
POST /wcapi/_selectlist/  {model, field, options: [{value, label}]} rename, remove, reorder
"""
from rest_framework import status
from rest_framework.views import APIView

from apps.core.services import select_lists
from apps.core.services.door import Actor, Refused
from common.api_responses import api_response


class SelectListView(APIView):
    http_method_names = ["post", "options", "head"]

    def post(self, request):
        data = request.data or {}
        actor = Actor.from_request(request)
        model, field = data.get('model'), data.get('field')
        try:
            if actor.user is None:
                raise Refused(401, 'authentication_required', 'Sign in to change a list.')
            if not model or not field:
                raise Refused(400, 'list_invalid', 'Name the model and the field.')
            if 'add' in data:
                options = select_lists.add_value(model, field, data['add'], actor=actor,
                                                 label=data.get('label'))
            else:
                options = select_lists.replace_list(model, field, data.get('options'), actor=actor)
        except Refused as refused:
            return api_response(success=False, status_code=refused.status,
                                message=refused.message, error={'code': refused.code})
        return api_response(data={'model': model, 'field': field, 'options': options},
                            status_code=status.HTTP_200_OK)
