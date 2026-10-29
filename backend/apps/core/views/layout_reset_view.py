"""Reset one part of a model's layout to the code default (apps/core/layouts). Staff only.

POST /wcapi/_layout_reset/  {model, part}     part: list, column, detail, form, panel, card, tabs, active
"""
from rest_framework import status
from rest_framework.views import APIView

from apps.core import layouts
from apps.core.services.door import Actor, Refused
from common.api_responses import api_response


class LayoutResetView(APIView):
    http_method_names = ["post", "options", "head"]

    def post(self, request):
        data = request.data or {}
        actor = Actor.from_request(request)
        model, part = data.get('model'), data.get('part')
        try:
            if actor.user is None:
                raise Refused(401, 'authentication_required', 'Sign in to reset a layout.')
            if not model or not part:
                raise Refused(400, 'layout_part_unknown', 'Name the model and the layout part.')
            layout = layouts.reset(model, part, actor=actor)
        except Refused as refused:
            return api_response(success=False, status_code=refused.status,
                                message=refused.message, error={'code': refused.code})
        return api_response(data={'model': model, 'part': part, 'layout': layout},
                            status_code=status.HTTP_200_OK)
