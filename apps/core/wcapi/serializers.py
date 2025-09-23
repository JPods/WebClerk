from typing import Type
from django.db import models
from rest_framework import serializers

def make_model_serializer(model: Type[models.Model]) -> Type[serializers.ModelSerializer]:
    class AutoSerializer(serializers.ModelSerializer):
        class Meta:
            model = model
            fields = "__all__"
    AutoSerializer.__name__ = f"{model.__name__}AutoSerializer"
    return AutoSerializer