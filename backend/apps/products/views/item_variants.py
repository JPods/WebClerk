from __future__ import annotations

import json
import pathlib
import subprocess

from rest_framework.views import APIView  # type: ignore
from django.db.models import Q
from django.http import HttpRequest
from apps.core.views.get_view import OpenReadOrAuthenticated
from common.api_responses import api_response
from apps.products.models import Item


_ALLIE_CAPTURE = pathlib.Path.home() / "Allie" / "scripts" / "allie-capture.py"


def _allie(event: str, message: str = "", data: dict | None = None):
    if not _ALLIE_CAPTURE.exists():
        return
    try:
        args = ["python3", str(_ALLIE_CAPTURE),
                "--source", "WC3", "--event", event, "--message", message[:200]]
        if data:
            args += ["--data", json.dumps(data)]
        subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer
from rest_framework import serializers
try:
    from apps.products.models import Variant  # type: ignore
except Exception:  # pragma: no cover
    Variant = None  # type: ignore


class ItemVariantsView(APIView):
    """List items filtered by variant parent and/or canonical key.

    GET /wcapi/items/?parent_id=<int>&key=<canonical>
    Optionally supports parent_uuid=<uuid> in addition to parent_id.
    """

    permission_classes = [OpenReadOrAuthenticated]

    @extend_schema(
        operation_id="products_item_variants_retrieve",
        parameters=[
            OpenApiParameter(name='parent_id', required=False, type=int),
            OpenApiParameter(name='parent_uuid', required=False, type=str),
            OpenApiParameter(name='key', required=False, type=str),
        ],
        responses={
            200: inline_serializer(
                name="ItemVariantList",
                fields={
                    'model_name': serializers.CharField(),
                    'results': serializers.ListField(child=serializers.DictField()),
                    'total': serializers.IntegerField(),
                    'limit': serializers.IntegerField(allow_null=True),
                    'offset': serializers.IntegerField(),
                }
            )
        }
    )
    def get(self, request: HttpRequest):
        # Prefer concrete Variant for filtering when available
        parent_id = request.GET.get('parent_id')
        parent_uuid = request.GET.get('parent_uuid')
        key = request.GET.get('key')
        if Variant is not None and (parent_id or parent_uuid or key):
            vqs = Variant.objects.active()
            try:
                if parent_id:
                    vqs = vqs.filter(parent_item_id=int(parent_id))
            except Exception:
                pass
            if parent_uuid:
                vqs = vqs.filter(set_uuid__isnull=False)  # lightweight guard, still return family members
            if key:
                vqs = vqs.filter(canonical_key=str(key))
            total = vqs.count()
            item_ids = list(vqs.values_list('item_id', flat=True))
            items = Item.objects.filter(id__in=item_ids)
            data = list(items.values('id', 'name', 'uuid', 'refs', 'catalog'))
            return api_response(data={'model_name': 'item', 'results': data, 'total': total, 'limit': None, 'offset': 0})
        qs = Item.objects.active()
        try:
            if parent_id:
                qs = qs.filter(refs__variants__parent_id=int(parent_id))
        except Exception:
            pass
        if parent_uuid:
            qs = qs.filter(refs__variants__parent_uuid=str(parent_uuid))
        if key:
            qs = qs.filter(refs__variants__key=str(key))
        total = qs.count()
        # Tool boundary: zero results = a gap in the catalog Alice should know about.
        if total == 0:
            _allie("search_no_result",
                   f"No variants: parent_id={parent_id} parent_uuid={parent_uuid} key={key}",
                   {"parent_id": parent_id, "parent_uuid": parent_uuid, "key": key})
        # Keep payload simple and JSON-safe; include id/name/refs/catalog.uuid for reference
        data = list(qs.values('id', 'name', 'uuid', 'refs', 'catalog'))
        return api_response(data={'model_name': 'item', 'results': data, 'total': total, 'limit': None, 'offset': 0})
