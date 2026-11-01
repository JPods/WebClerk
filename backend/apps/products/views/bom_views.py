from __future__ import annotations

from datetime import datetime
from typing import Any, cast
from rest_framework.views import APIView
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from apps.products.models.bill_of_material import BillOfMaterial
from apps.products.models.item import Item
from apps.products.serializers.bom_serializers import BillOfMaterialSerializer
from apps.products.services import bom_ops as bom_services
from common.api_responses import api_response
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer
from rest_framework import serializers


class BOMListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        operation_id="products_bom_list",
        parameters=[
            OpenApiParameter(name='as_of', description='Date (YYYY-MM-DD) to resolve historical BOM', required=False, type=str),
            OpenApiParameter(name='revision', description='Revision code to select a specific BOM revision', required=False, type=str),
        ],
        responses={200: inline_serializer(name='BillOfMaterialList', fields={
            'results': serializers.ListField(child=BillOfMaterialSerializer()),
            'total': serializers.IntegerField(),
        })}
    )
    def get(self, request, parent_id: int):
        as_of_str = request.query_params.get('as_of')
        revision = request.query_params.get('revision')
        as_of_date = None
        if as_of_str:
            try:
                as_of_date = datetime.strptime(as_of_str, '%Y-%m-%d').date()
            except ValueError:
                return api_response(success=False, status_code=400, message='Invalid as_of format, expected YYYY-MM-DD')
        lines = bom_services.list_bom_lines(parent_id, as_of=as_of_date, revision=revision)
        serializer = BillOfMaterialSerializer(lines, many=True)
        payload = {
            'results': serializer.data,
            'total': len(serializer.data)
        }
        return api_response(data=payload)

    @extend_schema(
        operation_id="products_bom_create",
        request=BillOfMaterialSerializer,
        responses={201: BillOfMaterialSerializer, 400: dict},
    )
    def post(self, request, parent_id: int):
        data = request.data.copy()
        data['parent_id'] = parent_id
        serializer = BillOfMaterialSerializer(data=data)
        if serializer.is_valid():
            # serializer.validated_data is already a dict-like object; cast directly for type checkers
            validated: dict[str, Any] = cast(dict[str, Any], serializer.validated_data)
            line = bom_services.create_bom_line(**validated)
            out = BillOfMaterialSerializer(line).data
            return api_response(data=out, status_code=status.HTTP_201_CREATED)
        return api_response(success=False, status_code=400, message='Validation error', error={'fields': serializer.errors})


class BOMDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, pk: int) -> BillOfMaterial:
        return get_object_or_404(BillOfMaterial, pk=pk)

    @extend_schema(operation_id="products_bom_retrieve", responses={200: BillOfMaterialSerializer})
    def get(self, request, pk: int):
        line = self.get_object(pk)
        data = BillOfMaterialSerializer(line).data
        return api_response(data=data)

    @extend_schema(operation_id="products_bom_partial_update", request=BillOfMaterialSerializer, responses={200: BillOfMaterialSerializer, 400: dict})
    def patch(self, request, pk: int):
        line = self.get_object(pk)
        serializer = BillOfMaterialSerializer(line, data=request.data, partial=True)
        if serializer.is_valid():
            validated: dict[str, Any] = cast(dict[str, Any], serializer.validated_data)
            updated = bom_services.update_bom_line(line, **validated)
            data = BillOfMaterialSerializer(updated).data
            return api_response(data=data)
        return api_response(success=False, status_code=400, message='Validation error', error={'fields': serializer.errors})

    @extend_schema(operation_id="products_bom_destroy", responses={200: inline_serializer(name='DeleteMessage', fields={'message': serializers.CharField()})})
    def delete(self, request, pk: int):
        line = self.get_object(pk)
        bom_services.delete_bom_line(line)
        return api_response(message='Deleted', data=None, status_code=200)


class BOMRecalcCostView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        operation_id="products_bom_recalc_cost",
        responses={200: inline_serializer(name='RecalcMessage', fields={'message': serializers.CharField(), 'parent_id': serializers.IntegerField()})}
    )
    def post(self, request, parent_id: int):
        # Ensure parent exists for 404 semantics
        get_object_or_404(Item, pk=parent_id)
        bom_services.recalc_parent_cost(parent_id)
        return api_response(message='Recalculation triggered', data={'parent_id': parent_id})


class BOMExpandTreeView(APIView):
    """Multi-level BOM tree expansion — flat list with level tracking and costs."""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        operation_id="products_bom_expand_tree",
        parameters=[
            OpenApiParameter(name='qty', description='Build quantity (default 1)', required=False, type=float),
            OpenApiParameter(name='as_of', description='Date (YYYY-MM-DD) for effective window', required=False, type=str),
            OpenApiParameter(name='revision', description='Revision code', required=False, type=str),
            OpenApiParameter(name='cost_basis', description='Cost basis: avg, last, min, landed (default avg)', required=False, type=str),
        ],
    )
    def get(self, request, parent_id: int):
        return self._expand(request, parent_id, request.query_params, None)

    @extend_schema(operation_id="products_bom_expand_tree_what_if")
    def post(self, request, parent_id: int):
        """The same tree calculated with unsaved changes — nothing is saved. Body: the query's
        params plus what_if {"cost": {item_id: unit}, "quantity": {bom_id: qty},
        "scrap_factor": {bom_id: factor}} (Bill, 2026-11-01: the screen sends what the user
        changes and shows the server's numbers)."""
        body = request.data if isinstance(request.data, dict) else {}
        what_if = body.get('what_if')
        if what_if is not None and not isinstance(what_if, dict):
            return api_response(success=False, status_code=400, message='what_if is an object')
        return self._expand(request, parent_id, body, what_if)

    def _expand(self, request, parent_id: int, params, what_if):
        from decimal import Decimal, InvalidOperation
        get_object_or_404(Item, pk=parent_id)
        try:
            qty = Decimal(str(params.get('qty', '1')))
        except InvalidOperation:
            return api_response(success=False, status_code=400, message='qty is a number')
        as_of_str = params.get('as_of')
        revision = params.get('revision')
        cost_basis = params.get('cost_basis', 'avg')
        if cost_basis not in ('avg', 'last', 'min', 'landed'):
            cost_basis = 'avg'
        as_of_date = None
        if as_of_str:
            try:
                as_of_date = datetime.strptime(as_of_str, '%Y-%m-%d').date()
            except ValueError:
                return api_response(success=False, status_code=400, message='Invalid as_of format')

        try:
            rows = bom_services.expand_tree(parent_id, qty, as_of=as_of_date, revision=revision,
                                            cost_basis=cost_basis, what_if=what_if)
        except (InvalidOperation, ValueError, TypeError) as e:
            return api_response(success=False, status_code=400, message=f'what_if: {e}')
        data = [{
            'bom_id': r.bom_id,
            'item_id': r.item_id,
            'item_ida': r.item_ida,
            'description': r.description,
            'level': r.level,
            'qty_plan': float(r.qty_plan),
            'qty_actual': float(r.qty_actual),
            'cost_avg': float(r.cost_avg),
            'cost_last': float(r.cost_last),
            'cost_unit': float(r.cost_unit),
            'cost_rollup': float(r.cost_rollup),
            'cost_extended': float(r.cost_extended),
            'scrap_factor': float(r.scrap_factor),
            'is_subassembly': r.is_subassembly,
        } for r in rows]
        return api_response(data={'rows': data, 'total_cost': float(bom_services.build_cost(rows)),
                                  'total_rows': len(data), 'what_if': bool(what_if)})


class BOMWhereUsedView(APIView):
    """Find all top-level assemblies that contain this item."""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(operation_id="products_bom_where_used")
    def get(self, request, item_id: int):
        get_object_or_404(Item, pk=item_id)
        top_levels = bom_services.find_top_level_assemblies(item_id)
        # Fetch display info for the top-level items
        items = Item.objects.filter(id__in=top_levels).values('id', 'ida', 'description')
        return api_response(data={'top_level_assemblies': list(items), 'total': len(top_levels)})


class BOMPropagateCostView(APIView):
    """Propagate cost recalculation up through all ancestor assemblies."""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(operation_id="products_bom_propagate_cost")
    def post(self, request, item_id: int):
        get_object_or_404(Item, pk=item_id)
        recalculated = bom_services.propagate_cost_up(item_id)
        return api_response(data={'recalculated_parents': recalculated, 'count': len(recalculated)}, message='Cost propagated')
