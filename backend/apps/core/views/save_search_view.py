"""Save Search — a stored search is a Report record.

    purpose = 'search_stored'      what makes it a search and not a print form
    config                          the search spec (keyword, filters, ordering...)
    model_name                      what it searches
    config.owner_user_id            set = personal to that user; absent = shared
    role_required                   which role a shared search is visible to

Personal and shared differ only in who can see them. Both are records, so both
can be listed, edited, exported and carried in a bundle — a search kept in a
user's prefs blob could do none of that.

POST /wcapi/save-search/
{
    "name": "Active customers in my territory",
    "model_name": "customer",
    "keyword": "active",
    "filters": {"status": "active", "rep_id": 5},
    "ordering": "-dt_created",
    "scope": "personal"  // or "shared"
}
"""
from rest_framework.views import APIView
from rest_framework import status

from apps.core.services.report_registry import REPORT_PURPOSE_SEARCH
from common.api_responses import api_response


class SaveSearchView(APIView):
    http_method_names = ["post", "options", "head"]

    def post(self, request):
        if not request.user or not request.user.is_authenticated:
            return api_response(
                success=False,
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Authentication required",
            )

        data = request.data or {}
        name = (data.get("name") or "").strip()
        model_name = (data.get("model_name") or "").strip()
        scope = (data.get("scope") or "personal").strip().lower()

        if not name or not model_name:
            return api_response(
                success=False,
                status_code=status.HTTP_400_BAD_REQUEST,
                message="name and model_name are required",
            )

        search_spec = {
            "keyword": data.get("keyword"),
            "search_fields": data.get("search_fields", []),
            "filters": data.get("filters", {}),
            "ordering": data.get("ordering"),
            "limit": data.get("limit"),
            "relative_period": data.get("relative_period"),
            "request_filters": data.get("request_filters"),
            "request_keyword": data.get("request_keyword"),
        }

        if scope == "shared" and not (request.user.is_superuser or request.user.is_staff):
            return api_response(
                success=False,
                status_code=status.HTTP_403_FORBIDDEN,
                message="Only admin users can create shared searches",
                error={"code": "saved_search_admin_required"},
            )

        from apps.core.models.report import Report

        owner_id = None if scope == "shared" else request.user.pk
        if owner_id is not None:
            search_spec["owner_user_id"] = owner_id

        # A user's own search and a shared one of the same name are different
        # records; ownership is part of the identity.
        lookup = {
            "name": name,
            "model_name": model_name,
            "purpose": REPORT_PURPOSE_SEARCH,
        }
        existing = Report.objects.filter(**lookup)
        existing = (existing.filter(config__owner_user_id=owner_id) if owner_id is not None
                    else existing.exclude(config__has_key="owner_user_id"))
        report = existing.order_by("-dt_modified").first()

        defaults = {
            "config": search_spec,
            "output_type": data.get("output_type", "screen"),
            "category": data.get("category", "list"),
            "role_required": data.get("role", ""),
            "description": data.get("description", ""),
            "is_active": True,
        }

        if report is None:
            report = Report.objects.create(**lookup, **defaults)
            created = True
        else:
            for field, value in defaults.items():
                setattr(report, field, value)
            report.save()
            created = False

        return api_response(
            data={
                "id": report.id,
                "name": report.name,
                "model_name": report.model_name,
                "scope": "personal" if owner_id is not None else "shared",
                "created": created,
            },
            status_code=status.HTTP_200_OK,
        )
