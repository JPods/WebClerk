from __future__ import annotations

from datetime import datetime
from typing import Any, cast
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from apps.products.models.bom import BillOfMaterial
from apps.products.models.item import Item
from apps.products.serializers.bom_serializers import BillOfMaterialSerializer
from apps.products.services import bom_services
from common.api_responses import api_response


class BOMListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, parent_id: int):
        raw_flag = request.query_params.get('raw') == '1'
        as_of_str = request.query_params.get('as_of')
        revision = request.query_params.get('revision')
        as_of_date = None
        if as_of_str:
            try:
                as_of_date = datetime.strptime(as_of_str, '%Y-%m-%d').date()
            except ValueError:
                return api_response(success=False, status_code=400, message='Invalid as_of format, expected YYYY-MM-DD', raw=raw_flag)
        lines = bom_services.list_bom_lines(parent_id, as_of=as_of_date, revision=revision)
        serializer = BillOfMaterialSerializer(lines, many=True)
        if raw_flag:
            return Response(serializer.data)
        payload = {
            'results': serializer.data,
            'total': len(serializer.data)
        }
        return api_response(data=payload, raw=raw_flag)

    def post(self, request, parent_id: int):
        raw_flag = request.query_params.get('raw') == '1'
        data = request.data.copy()
        data['parent_id'] = parent_id
        serializer = BillOfMaterialSerializer(data=data)
        if serializer.is_valid():
            # serializer.validated_data is already a dict-like object; cast directly for type checkers
            validated: dict[str, Any] = cast(dict[str, Any], serializer.validated_data)
            line = bom_services.create_bom_line(**validated)
            out = BillOfMaterialSerializer(line).data
            if raw_flag:
                return Response(out, status=status.HTTP_201_CREATED)
            return api_response(data=out, status_code=status.HTTP_201_CREATED, raw=raw_flag)
        if raw_flag:
            return Response(serializer.errors, status=400)
        return api_response(success=False, status_code=400, message='Validation error', error={'fields': serializer.errors}, raw=raw_flag)


class BOMDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, pk: int) -> BillOfMaterial:
        return get_object_or_404(BillOfMaterial, pk=pk)

    def get(self, request, pk: int):
        raw_flag = request.query_params.get('raw') == '1'
        line = self.get_object(pk)
        data = BillOfMaterialSerializer(line).data
        if raw_flag:
            return Response(data)
        return api_response(data=data, raw=raw_flag)

    def patch(self, request, pk: int):
        raw_flag = request.query_params.get('raw') == '1'
        line = self.get_object(pk)
        serializer = BillOfMaterialSerializer(line, data=request.data, partial=True)
        if serializer.is_valid():
            validated: dict[str, Any] = cast(dict[str, Any], serializer.validated_data)
            updated = bom_services.update_bom_line(line, **validated)
            data = BillOfMaterialSerializer(updated).data
            if raw_flag:
                return Response(data)
            return api_response(data=data, raw=raw_flag)
        if raw_flag:
            return Response(serializer.errors, status=400)
        return api_response(success=False, status_code=400, message='Validation error', error={'fields': serializer.errors}, raw=raw_flag)

    def delete(self, request, pk: int):
        raw_flag = request.query_params.get('raw') == '1'
        line = self.get_object(pk)
        bom_services.delete_bom_line(line)
        if raw_flag:
            return Response(status=204)
        return api_response(message='Deleted', data=None, status_code=200, raw=raw_flag)


class BOMRecalcCostView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, parent_id: int):
        raw_flag = request.query_params.get('raw') == '1'
        # Ensure parent exists for 404 semantics
        get_object_or_404(Item, pk=parent_id)
        bom_services.recalc_parent_cost(parent_id)
        if raw_flag:
            return Response({'status': 'ok'})
        return api_response(message='Recalculation triggered', data={'parent_id': parent_id}, raw=raw_flag)
