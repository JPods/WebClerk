from __future__ import annotations

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.shortcuts import get_object_or_404
from decimal import Decimal
from typing import cast

from common.api_responses import api_response
from apps.products.models.inventory_layer import InventoryStack
from apps.products.models.inventory_reservation import InventoryReservation
from apps.products.services.inventory_reservations import (
    availability_for_stack, create_reservation,
)
from apps.products.serializers.reservation_serializers import (
    InventoryReservationSerializer, ReservationCreateSerializer, ReservationActionSerializer,
)
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from apps.products.services.inventory_metrics import summarize_inventory_metrics


@extend_schema(
    parameters=[
        OpenApiParameter(name='raw', description='Return raw JSON without envelope', required=False, type=str),
    ],
    responses={200: InventoryReservationSerializer},
    examples=[
        OpenApiExample(
            'AvailabilityExample',
            value={
                'status': 'success',
                'code': 200,
                'message': '',
                'error': None,
                'data': {
                    'stack_id': 10,
                    'item_id': 55,
                    'warehouse_id': 3,
                    'remaining_qty': 120.0,
                    'available_qty': 115.0,
                }
            }
        )
    ]
)
class InventoryAvailabilityView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, stack_id: int):
        raw_flag = request.query_params.get('raw') == '1'
        stack = get_object_or_404(InventoryStack, pk=stack_id)
        available = availability_for_stack(stack)
        # Related FK ids (item_id / warehouse_id) may not be annotated on instance if custom manager; access via related objects for safety.
        payload = {
            'stack_id': stack.id,
            'item_id': getattr(stack, 'item_id', None) or stack.item.id,
            'warehouse_id': getattr(stack, 'warehouse_id', None) or stack.warehouse.id,
            'remaining_qty': float(Decimal(str(stack.remaining_qty()))),
            'available_qty': float(Decimal(str(available))),
        }
        if raw_flag:
            return Response(payload)
        return api_response(data=payload, raw=raw_flag)


@extend_schema(
    request=ReservationCreateSerializer,
    responses={201: InventoryReservationSerializer, 400: dict},
    examples=[
        OpenApiExample(
            'CreateReservationSuccess',
            value={
                'status': 'success', 'code': 201, 'message': '', 'error': None,
                'data': {
                    'id': 77,
                    'item': 55,
                    'warehouse': 3,
                    'stack': 10,
                    'qty': '5.0000',
                    'state': 'pending',
                    'expires_at': '2025-09-04T12:00:00Z',
                    'committed_at': None,
                    'released_at': None,
                    'context': {},
                    'reason': '',
                    'created_dt': '2025-09-04T11:50:00Z',
                    'modified_dt': '2025-09-04T11:50:00Z'
                }
            }
        )
    ]
)
class InventoryReservationCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        raw_flag = request.query_params.get('raw') == '1'
        serializer = ReservationCreateSerializer(data=request.data)
        if not serializer.is_valid():
            if raw_flag:
                return Response(serializer.errors, status=400)
            return api_response(success=False, status_code=400, message='Validation error', error={'fields': serializer.errors}, raw=raw_flag)
        data = cast(dict, serializer.validated_data)
        stack = get_object_or_404(InventoryStack, pk=data['stack_id'])
        try:
            reservation = create_reservation(
                stack,
                data['qty'],
                ttl_seconds=data.get('ttl_seconds', 900),
                reason=data.get('reason') or '',
                context=(data.get('ctx') if isinstance(data.get('ctx'), dict) else {}),
            )
        except ValueError as e:
            if raw_flag:
                return Response({'error': str(e)}, status=400)
            return api_response(success=False, status_code=400, message=str(e), raw=raw_flag)
        out = InventoryReservationSerializer(reservation).data
        if raw_flag:
            return Response(out, status=201)
        return api_response(data=out, status_code=201, raw=raw_flag)


@extend_schema(
    request=ReservationActionSerializer,
    responses={200: InventoryReservationSerializer, 400: dict},
    examples=[
        OpenApiExample(
            'CommitReservation',
            value={
                'status': 'success', 'code': 200, 'message': '', 'error': None,
                'data': {
                    'id': 77,
                    'item': 55,
                    'warehouse': 3,
                    'stack': 10,
                    'qty': '5.0000',
                    'state': 'committed',
                    'expires_at': '2025-09-04T12:00:00Z',
                    'committed_at': '2025-09-04T11:55:00Z',
                    'released_at': None,
                    'context': {},
                    'reason': '',
                    'created_dt': '2025-09-04T11:50:00Z',
                    'modified_dt': '2025-09-04T11:55:00Z'
                }
            }
        )
    ]
)
class InventoryReservationActionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        raw_flag = request.query_params.get('raw') == '1'
        serializer = ReservationActionSerializer(data=request.data)
        if not serializer.is_valid():
            if raw_flag:
                return Response(serializer.errors, status=400)
            return api_response(
                success=False,
                status_code=400,
                message='Validation error',
                error={'fields': serializer.errors},
                raw=raw_flag,
            )
        data = cast(dict, serializer.validated_data)
        reservation = get_object_or_404(InventoryReservation, pk=data['reservation_id'])
        action = data['action']
        if action == 'commit':
            success = reservation.commit()
        else:  # release
            success = reservation.release(data.get('reason') or 'user_release')
        reservation.refresh_from_db()
        out = InventoryReservationSerializer(reservation).data
        if not success:
            if raw_flag:
                return Response({'error': 'action_failed', 'reservation': out}, status=400)
            return api_response(
                success=False,
                status_code=400,
                message='action_failed',
                data=out,
                raw=raw_flag,
            )
        if raw_flag:
            return Response(out)
        return api_response(data=out, raw=raw_flag)


@extend_schema(
    parameters=[
        OpenApiParameter(name='raw', description='Return raw JSON without envelope', required=False, type=str),
        OpenApiParameter(name='samples', description='Include sample rows (1 to enable)', required=False, type=str),
    ],
    examples=[
        OpenApiExample(
            'InventoryMetricsExample',
            value={
                'status': 'success', 'code': 200, 'message': '', 'error': None,
                'data': {
                    'reservations': {'counts': {'pending': 3}, 'qty': {'pending': 15.0}, 'active_reserved_qty': 15.0},
                    'pending_adjustments': {'counts': {'pending': 2}, 'qty': {'pending': 6.0}, 'reserved_conflict_pending': 1, 'insufficient_pending': 1},
                    'stacks': {'total': 12, 'locked': 1, 'remaining_total': 320.0, 'received_total': 400.0},
                    'protection': {'reserved_vs_remaining_pct': 4.69},
                    'processor_runs': {
                        'latest_global': {
                            'id': 10,
                            'attempted': 5,
                            'applied': 4,
                            'skipped_locked': 0,
                            'still_locked': 0,
                            'insufficient': 0,
                            'canceled': 0,
                            'reserved_conflict_skipped': 1,
                            'duration_s': 0.12,
                            'started_dt': '2025-09-04T07:30:00Z',
                            'finished_dt': '2025-09-04T07:30:00Z',
                            'dry_run': False
                        },
                        'latest_stack': None,
                        'latest_global_duration_buckets': {'0.01':0,'0.05':1,'0.1':0,'0.25':1,'0.5':0,'1':0,'2':0,'5':0,'+Inf':0},
                        'latest_stack_duration_buckets': None,
                        'cumulative': {
                            'global_runs': 42,
                            'global_attempted': 250,
                            'global_applied': 240,
                            'stack_runs': 17,
                            'stack_attempted': 60,
                            'stack_applied': 58
                        }
                    }
                }
            }
        )
    ]
)
class InventoryMetricsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        raw_flag = request.query_params.get('raw') == '1'
        samples_flag = request.query_params.get('samples') == '1'
        metrics = summarize_inventory_metrics(include_samples=samples_flag)
        if raw_flag:
            return Response(metrics)
        return api_response(data=metrics, raw=raw_flag)


class InventoryPrometheusMetricsView(APIView):
    # Auth toggle: default require auth unless settings flag disables
    permission_classes = [permissions.AllowAny]
    @extend_schema(
        parameters=[
            OpenApiParameter(name='auth', description='Set auth=0 to bypass auth when INVENTORY_PROMETHEUS_REQUIRE_AUTH is true', required=False, type=str),
        ],
        responses={200: OpenApiExample(
            'PrometheusSample',
            value='''inventory_reservations_count{state="pending"} 3\ninventory_reservations_active_reserved_qty 15.0\n...'''
        )},
        description='Prometheus-style plaintext metrics for inventory, reservations, and processor runs.'
    )
    def get(self, request):
        from django.conf import settings
        require_auth = getattr(settings, 'INVENTORY_PROMETHEUS_REQUIRE_AUTH', True)
        if require_auth and request.query_params.get('auth') != '0' and not request.user.is_authenticated:
            return Response('auth required', status=401, content_type='text/plain')
        m = summarize_inventory_metrics(include_samples=False)
        lines = []
        for state, count in m['reservations']['counts'].items():
            lines.append(f"inventory_reservations_count{{state=\"{state}\"}} {count}")
        for state, qty in m['reservations']['qty'].items():
            lines.append(f"inventory_reservations_qty{{state=\"{state}\"}} {qty}")
        lines.append(f"inventory_reservations_active_reserved_qty {m['reservations']['active_reserved_qty']}")
        lines.append(f"inventory_reservations_avg_pending_ttl_seconds {m['reservations']['avg_pending_ttl_s']}")
        lines.append(f"inventory_reservations_soonest_expiry_seconds {m['reservations']['soonest_expiry_in_s']}")
        # TTL histogram buckets
        ttl_buckets = (m['reservations'].get('pending_ttl_buckets') or {}).items()
        for bound, c in ttl_buckets:
            lines.append(f"inventory_reservations_pending_ttl_bucket{{le=\"{bound}\"}} {c}")
        # Pending adjustments
        for state, count in m['pending_adjustments']['counts'].items():
            lines.append(f"inventory_pending_adjustments_count{{state=\"{state}\"}} {count}")
        for state, qty in m['pending_adjustments']['qty'].items():
            lines.append(f"inventory_pending_adjustments_qty{{state=\"{state}\"}} {qty}")
        lines.append(f"inventory_pending_reserved_conflict_pending {m['pending_adjustments']['reserved_conflict_pending']}")
        lines.append(f"inventory_pending_insufficient_pending {m['pending_adjustments']['insufficient_pending']}")
        # Stacks
        lines.append(f"inventory_stacks_total {m['stacks']['total']}")
        lines.append(f"inventory_stacks_locked {m['stacks']['locked']}")
        lines.append(f"inventory_stacks_remaining_total {m['stacks']['remaining_total']}")
        lines.append(f"inventory_stacks_received_total {m['stacks']['received_total']}")
        # Protection
        lines.append(f"inventory_reserved_vs_remaining_pct {m['protection']['reserved_vs_remaining_pct']}")
        # Processor runs
        pr = m.get('processor_runs') or {}
        lg = pr.get('latest_global') or {}
        if lg:
            prefix = 'inventory_processor_global'
            for k in ['attempted', 'applied', 'skipped_locked', 'still_locked', 'insufficient', 'canceled', 'reserved_conflict_skipped', 'duration_s']:
                if k in lg and lg[k] is not None:
                    lines.append(f"{prefix}_{k} {lg[k]}")
            gbuckets = pr.get('latest_global_duration_buckets') or {}
            for bound, c in gbuckets.items():
                lines.append(f"{prefix}_duration_bucket{{le=\"{bound}\"}} {c}")
        ls = pr.get('latest_stack') or {}
        if ls:
            prefix = 'inventory_processor_stack'
            for k in ['attempted', 'applied', 'insufficient', 'canceled', 'reserved_conflict_skipped', 'duration_s']:
                if k in ls and ls[k] is not None:
                    lines.append(f"{prefix}_{k} {ls[k]}")
            sbuckets = pr.get('latest_stack_duration_buckets') or {}
            for bound, c in sbuckets.items():
                    lines.append(f"{prefix}_duration_bucket{{le=\"{bound}\"}} {c}")
        cum = pr.get('cumulative') or {}
        for name in ['global_runs','global_attempted','global_applied','stack_runs','stack_attempted','stack_applied']:
            if name in cum:
                lines.append(f"inventory_processor_{name} {cum[name]}")
        body = "\n".join(lines) + "\n"
        return Response(body, content_type='text/plain')
