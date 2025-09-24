from rest_framework import permissions
from apps.docs.models.tag import Tag
from apps.core.wcapi.registry import ModelConfig, register

# Simplified registration: auto-serializer (fields="__all__"), WCAPI router handles CRUD
register(ModelConfig(
    key="tag",
    model=Tag,
    search_fields=("name", "purpose"),
    ordering=("-dt_modified",),
    permission_classes=(permissions.IsAuthenticated,),
))