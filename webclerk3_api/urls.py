from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from django.conf import settings

import apps.core.wcapi.views as wcapi_views
from apps.core.wcapi.views import RESTModelRouterView
from apps.docs.views_tag import TagHierarchyView  # add import
#CRUD routes for blessed models to wcapi
def wcapi_alias_urlpatterns():
    # Auto-generate <key>-list and <key>-detail aliases that route to wcapi
    patterns = []
    blessed = getattr(settings, "WCAPI_BLESSED_MODELS", {}) or {}
    for key in blessed.keys():
        # e.g., /tag/ and /tag/<pk>/ continue to work, but handled by wcapi
        patterns.append(path(f"{key}/", RESTModelRouterView.as_view(), {"model": key}, name=f"{key}-list"))
        patterns.append(path(f"{key}/<int:pk>/", RESTModelRouterView.as_view(), {"model": key}, name=f"{key}-detail"))
    return patterns

urlpatterns = [
    # Admin
    path('admin/', lambda r: HttpResponse("Admin Dashboard"), name='admin_dashboard'),
    path('admin-django/', admin.site.urls),

    # Include docs routes BEFORE any generic/catch-all routers
    path('', include('apps.docs.urls')),

    # Ensure hierarchy routes are matched before any generic/action routers
    path("tag/<int:pk>/hierarchy", TagHierarchyView.as_view(), name="tag-hierarchy"),
    path("tag/<int:pk>/hierarchy/", TagHierarchyView.as_view(), name="tag-hierarchy-slash"),

    # Core app bundles
    path('', include('apps.core.urls')),
    path('', include('apps.transactions.urls')),

    # WCAPI endpoints
    path('wcapi/get', wcapi_views.WCAPIGetView.as_view(), name='wcapi-get'),
    path('wcapi/query', wcapi_views.WCAPIQueryView.as_view(), name='wcapi-query'),
    path('wcapi/save', wcapi_views.WCAPISaveView.as_view(), name='wcapi-save'),
    path('wcapi/delete', wcapi_views.WCAPIDeleteView.as_view(), name='wcapi-delete'),
]

# Add model alias routes BEFORE the catch-all router
urlpatterns += wcapi_alias_urlpatterns()

# Keep catch-all wcapi router last
urlpatterns += [
    path('<slug:model>/<int:pk>/', wcapi_views.RESTModelRouterView.as_view(), name='model-detail-router'),
    path('<slug:model>/', wcapi_views.RESTModelRouterView.as_view(), name='model-list-router'),
]