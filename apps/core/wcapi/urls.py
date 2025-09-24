from typing import Type
from rest_framework.routers import DefaultRouter

from .registry import all_configs
from .viewsets import WCAPIModelViewSet
from . import register_builtin  # ensure registrations run  # noqa: F401

router = DefaultRouter()

def make_viewset(model_key: str) -> Type[WCAPIModelViewSet]:
    cls_name = model_key.title().replace('/', '_') + "ViewSet"
    return type(cls_name, (WCAPIModelViewSet,), {"model_key": model_key})

for cfg in all_configs():
    basename = (cfg.basename or cfg.key).replace('/', '-')
    router.register(cfg.key, make_viewset(cfg.key), basename=basename)

urlpatterns = [*router.urls]