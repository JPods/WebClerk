from rest_framework import permissions
from apps.docs.models.tag import Tag
from apps.docs.serializers.tag_serializers import TagSerializer, TagDetailSerializer
from apps.core.wcapi.registry import ModelConfig, register
from apps.core.wcapi.viewsets import WCAPIModelViewSet

class TagViewSet(WCAPIModelViewSet):
    model_key = "tag"
    permission_classes = [permissions.IsAuthenticated]
    ordering = ["-dt_modified"]

# Register config
register(ModelConfig(
    key="tag",
    model=Tag,
    list_serializer=TagSerializer,
    detail_serializer=TagDetailSerializer,
    search_fields=("name", "purpose"),
    ordering=("-dt_modified",),
    permission_classes=(permissions.IsAuthenticated,),
    viewset_cls=TagViewSet,
))