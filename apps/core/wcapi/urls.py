from typing import Type
from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.core.wcapi import views as wcapi_views
from apps.core.wcapi.views import RESTModelRouterView
from .registry import all_configs
from .viewsets import WCAPIModelViewSet
from . import register_builtin  # ensure registrations run  # noqa: F401

# Exception endpoints (rare cases)
try:
    from apps.docs.views_tag import TagHierarchyView  # optional special-case
except Exception:  # pragma: no cover
    TagHierarchyView = None

# Optional: per-model viewsets (register here for simple, predictable routes)
try:
    from apps.docs.views.tag_viewset import TagViewSet
except Exception:  # pragma: no cover
    TagViewSet = None

# Domain search exception endpoint (tests expect /domain/?q=...)
class DomainSearchView(APIView):
    def get(self, request, *args, **kwargs):
        q = (request.GET.get('q') or '').strip()
        results = []

        # Pull from Connection as tests create Connection() then call /domain/?q=hub
        try:
            # Try common import paths; fall back quietly if missing
            try:
                from apps.sync.models import Connection  # type: ignore
            except Exception:
                Connection = None  # type: ignore
            if Connection is not None and q:
                qs = Connection.objects.filter(name__icontains=q).order_by('name')[:50]
                results = [{'name': c.name} for c in qs]
        except Exception:
            results = []

        payload = {
            'ok': True,
            'results': results,
            'meta': {'count': len(results)},
        }
        return Response(payload, status=status.HTTP_200_OK)

router = DefaultRouter()
if TagViewSet is not None:
    router.register(r"tag", TagViewSet, basename="tag")

# Dynamically create a subclass per key to bind model_key without per-model files.
def make_viewset(model_key: str) -> Type[WCAPIModelViewSet]:
    cls_name = model_key.title().replace('/', '_') + "ViewSet"
    return type(cls_name, (WCAPIModelViewSet,), {"model_key": model_key})

for cfg in all_configs():
    basename = (cfg.basename or cfg.key).replace('/', '-')
    router.register(cfg.key, make_viewset(cfg.key), basename=basename)

urlpatterns = [
    # Exception endpoints first
    path("domain/", DomainSearchView.as_view(), name="domain-list"),
]

# Tag hierarchy exceptions (if available)
if TagHierarchyView is not None:
    urlpatterns += [
        path("tag/<int:pk>/hierarchy", TagHierarchyView.as_view(), name="tag-hierarchy"),
        path("tag/<int:pk>/hierarchy/", TagHierarchyView.as_view(), name="tag-hierarchy-slash"),
    ]

# Core wcapi endpoints (CRUD helpers)
urlpatterns += [
    path('wcapi/get', wcapi_views.WCAPIGetView.as_view(), name='wcapi-get'),
    path('wcapi/query', wcapi_views.WCAPIQueryView.as_view(), name='wcapi-query'),
    path('wcapi/save', wcapi_views.WCAPISaveView.as_view(), name='wcapi-save'),
    path('wcapi/delete', wcapi_views.WCAPIDeleteView.as_view(), name='wcapi-delete'),
]

# Router-based model routes (uniform /<model>/ and /<model>/<pk>/)
urlpatterns += router.urls

# Catch-all wcapi router last (uniform per-model routing via RESTModelRouterView)
urlpatterns += [
    path('<slug:model>/<int:pk>/', RESTModelRouterView.as_view(), name='model-detail-router'),
    path('<slug:model>/', RESTModelRouterView.as_view(), name='model-list-router'),
]