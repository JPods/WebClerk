from __future__ import annotations

from typing import Any, Dict, List

from django.apps import apps
from django.db import models
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiParameter, OpenApiExample


def _field_info(f: Any) -> Dict[str, Any]:
    info: Dict[str, Any] = {
        'name': getattr(f, 'attname', getattr(f, 'name', '')),
        'type': f.__class__.__name__,
        'null': getattr(f, 'null', False),
        'blank': getattr(f, 'blank', False),
        'primary_key': getattr(f, 'primary_key', False),
        'unique': getattr(f, 'unique', False),
        'db_index': getattr(f, 'db_index', False),
    }
    choices = getattr(f, 'choices', None)
    if choices:
        try:
            info['choices'] = [c[0] for c in choices]
        except Exception:
            info['choices'] = list(choices)
    for k in ('max_length', 'decimal_places', 'max_digits'):
        if hasattr(f, k) and getattr(f, k) is not None:
            info[k] = getattr(f, k)
    # relation target (FK/O2O)
    if hasattr(f, 'related_model') and getattr(f, 'related_model') is not None:
        rm = getattr(f, 'related_model')
        try:
            info['related_model'] = f"{rm._meta.app_label}.{rm.__name__}"
        except Exception:
            info['related_model'] = str(rm)
    return info


class ModelFieldsView(APIView):
    """Return a comprehensive list of all project models and their concrete fields.

    Query params:
      - compact=1: only include names and types per field to reduce payload size
    - app_name=<app_label>: filter to a specific app
    """

    @extend_schema(
        operation_id="core_model_fields_retrieve",
        parameters=[
            OpenApiParameter(name='compact', description='Return only name and type for fields when 1/true', required=False, type=str),
            OpenApiParameter(name='app_name', description='Filter to a single app', required=False, type=str),
        ],
        responses={
            200: inline_serializer(
                name="ModelFields",
                many=True,
                fields={
                    'app': serializers.CharField(),
                    'model': serializers.CharField(),
                    'db_table': serializers.CharField(),
                    'field_count': serializers.IntegerField(),
                    'fields': inline_serializer(
                        name="FieldInfo",
                        many=True,
                        fields={
                            'name': serializers.CharField(),
                            'type': serializers.CharField(),
                            'null': serializers.BooleanField(required=False),
                            'blank': serializers.BooleanField(required=False),
                            'primary_key': serializers.BooleanField(required=False),
                            'unique': serializers.BooleanField(required=False),
                            'db_index': serializers.BooleanField(required=False),
                            'max_length': serializers.IntegerField(required=False),
                            'decimal_places': serializers.IntegerField(required=False),
                            'max_digits': serializers.IntegerField(required=False),
                            'related_model': serializers.CharField(required=False),
                        },
                    ),
                },
            )
        },
        examples=[
            OpenApiExample(
                'ModelFieldsExample',
                value=[{
                    'app': 'products',
                    'model': 'products.Item',
                    'db_table': 'items',
                    'field_count': 12,
                    'fields': [{'name': 'id', 'type': 'AutoField'}, {'name': 'name', 'type': 'CharField'}]
                }]
            )
        ],
        description="Introspect Django models and return their concrete fields.",
    )
    def get(self, request):
        compact = request.query_params.get('compact') in ('1', 'true', 'yes')
        only_app = request.query_params.get('app_name')
        payload: List[Dict[str, Any]] = []
        for model in sorted(apps.get_models(), key=lambda m: f"{m._meta.app_label}.{m.__name__}"):
            app_label = model._meta.app_label
            # skip core Django/system apps
            if app_label in {"admin", "auth", "contenttypes", "sessions"} or app_label.startswith('django_'):
                continue
            if only_app and app_label != only_app:
                continue
            meta = model._meta
            fields: List[Dict[str, Any]] = []
            for f in meta.get_fields():
                # skip reverse relations and auto-created rels
                if isinstance(f, (models.ManyToOneRel, models.ManyToManyRel, models.OneToOneRel)):
                    continue
                if getattr(f, 'auto_created', False) and not getattr(f, 'concrete', False):
                    continue
                name = getattr(f, 'attname', getattr(f, 'name', ''))
                if not name:
                    continue
                info = _field_info(f)
                if compact:
                    info = {'name': info['name'], 'type': info['type']}
                fields.append(info)

            payload.append({
                'app': app_label,
                'model': f"{app_label}.{model.__name__}",
                'db_table': meta.db_table,
                'fields': fields,
                'field_count': len(fields),
            })
        return Response(payload)
