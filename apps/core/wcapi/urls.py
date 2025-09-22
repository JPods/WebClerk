from django.urls import path
from apps.core.wcapi.views_query import RESTOpenQueryView, RESTSavedSetView

urlpatterns = [
    # Open query: run or save
    path("wcapi/<str:model>/_query", RESTOpenQueryView.as_view(), name="wcapi-open-query"),
    path("wcapi/<str:model>/_query/<str:action>", RESTOpenQueryView.as_view(), name="wcapi-open-query-action"),
    # Saved sets
    path("wcapi/<str:model>/_sets", RESTSavedSetView.as_view(), name="wcapi-saved-sets"),
    path("wcapi/<str:model>/_sets/<str:ident>", RESTSavedSetView.as_view(), name="wcapi-saved-sets-item"),
]