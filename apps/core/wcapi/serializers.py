from typing import Type
from django.db import models
from rest_framework import serializers

def make_model_serializer(model: Type[models.Model]) -> Type[serializers.ModelSerializer]:
    meta = type("Meta", (), {"model": model, "fields": "__all__"})
    name = f"{model.__name__}AutoSerializer"
    return type(name, (serializers.ModelSerializer,), {"Meta": meta})