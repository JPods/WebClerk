from django.urls import path
from apps.core.wcapi.views_query import RESTOpenQueryView, RESTSavedSetView
from apps.core.wcapi.views import RESTModelRouterView

urlpatterns = [
    # Open-query run and save
    path("wcapi/<str:model>/_query", RESTOpenQueryView.as_view(), name="wcapi-open-query"),
    path("wcapi/<str:model>/_query/save", RESTOpenQueryView.as_view(), {"action": "save"}, name="wcapi-open-query-save"),

    # Saved sets
    path("wcapi/<str:model>/_sets", RESTSavedSetView.as_view(), name="wcapi-saved-sets"),
    path("wcapi/<str:model>/_sets/<str:ident>", RESTSavedSetView.as_view(), name="wcapi-saved-sets-item"),

    # Catch-all model router (covers push and other actions)
    path("wcapi/<str:model>", RESTModelRouterView.as_view(), name="wcapi-model-root"),
    path("wcapi/<str:model>/<path:extra>", RESTModelRouterView.as_view(), name="wcapi-model-extra"),
]