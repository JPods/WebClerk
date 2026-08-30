"""API endpoint for resolving settings through the scope hierarchy."""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.core.services.setting_resolve import resolve_setting_with_source


class SettingResolveView(APIView):
    """Resolve a setting through the scope hierarchy for the current user.

    GET /wcapi/setting/resolve/?purpose=wc:detail_layout&parent_model=action

    Returns the most specific matching Setting's config, plus which scope matched.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        purpose = request.query_params.get("purpose", "")
        parent_model = request.query_params.get("parent_model", "")

        if not purpose:
            return Response({"status": "fail", "error": "purpose is required"}, status=400)

        user = request.user
        contact_id = getattr(user, "id", 0) or 0
        org_id = 0
        role = ""

        # Try to get org_id and role from user profile
        try:
            profile = getattr(user, "userprofile", None)
            if profile:
                org_id = getattr(profile, "org_id", 0) or 0
                cached_roles = getattr(profile, "cached_roles", None)
                if isinstance(cached_roles, list) and cached_roles:
                    role = cached_roles[0]
        except Exception:
            pass

        config, scope = resolve_setting_with_source(
            purpose=purpose,
            parent_model=parent_model,
            contact_id=contact_id,
            org_id=org_id,
            role=role,
        )

        return Response({
            "status": "success",
            "data": {
                "config": config,
                "scope": scope,
                "purpose": purpose,
                "parent_model": parent_model,
            }
        })
