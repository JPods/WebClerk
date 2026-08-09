"""
Save Search endpoint — saves the current query as a personal or shared search.

Personal:  Saved to UserProfile.prefs.search[] (user's favorites)
Shared:    Saved as a Report record (admin only, role-visible)

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
from django.utils import timezone
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

        # Build the search spec (same shape everywhere)
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

        if scope == "shared":
            return self._save_as_report(request, name, model_name, search_spec, data)
        else:
            return self._save_to_prefs(request, name, model_name, search_spec)

    def _save_to_prefs(self, request, name, model_name, search_spec):
        """Save to UserProfile.prefs.search[] — personal bookmark."""
        try:
            profile = request.user.profile
        except Exception:
            return api_response(
                success=False,
                status_code=status.HTTP_400_BAD_REQUEST,
                message="No user profile found",
            )

        prefs = profile.prefs if isinstance(profile.prefs, dict) else {}
        searches = prefs.get("search", [])
        if not isinstance(searches, list):
            searches = []

        # Replace if same name+model exists, otherwise append
        entry = {
            "name": name,
            "model_name": model_name,
            "dt_saved": int(timezone.now().timestamp() * 1000),
            **search_spec,
        }

        replaced = False
        for i, existing in enumerate(searches):
            if isinstance(existing, dict) and existing.get("name") == name and existing.get("model_name") == model_name:
                searches[i] = entry
                replaced = True
                break

        if not replaced:
            searches.append(entry)

        prefs["search"] = searches
        type(profile).objects.filter(pk=profile.pk).update(prefs=prefs)

        return api_response(
            data={"saved": entry, "scope": "personal", "count": len(searches)},
            status_code=status.HTTP_200_OK,
        )

    def _save_as_report(self, request, name, model_name, search_spec, data):
        """Save as a Report record — shared, admin only."""
        if not (request.user.is_superuser or request.user.is_staff):
            return api_response(
                success=False,
                status_code=status.HTTP_403_FORBIDDEN,
                message="Only admin users can create shared searches",
                error={"code": "saved_search_admin_required"},
            )

        from apps.core.models.report import Report

        # Update existing or create new
        report, created = Report.objects.update_or_create(
            name=name,
            model_name=model_name,
            defaults={
                "config": search_spec,
                "output_type": data.get("output_type", "screen"),
                "category": data.get("category", "list"),
                "role_required": data.get("role", ""),
                "description": data.get("description", ""),
                "is_active": True,
            },
        )

        return api_response(
            data={
                "id": report.id,
                "name": report.name,
                "model_name": report.model_name,
                "scope": "shared",
                "created": created,
            },
            status_code=status.HTTP_200_OK,
        )
