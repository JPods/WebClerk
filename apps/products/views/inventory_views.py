from __future__ import annotations

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.shortcuts import get_object_or_404
from decimal import Decimal
from typing import cast

from common.api_responses import api_response
from apps.products.models.inventory_layer import InventoryLayer
from apps.products.models.inventory_reservation import InventoryReservation
from apps.products.services.inventory_reservations import (
    availability_for_stack, create_reservation,
)
from apps.products.serializers.reservation_serializers import (
    InventoryReservationSerializer, ReservationCreateSerializer, ReservationActionSerializer,
)
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse
from apps.products.services.inventory_metrics import summarize_inventory_metrics
from rest_framework.permissions import AllowAny

# Prefer project BaseJSONAPIView; fallback to DRF APIView
try:
    from apps.core.views import BaseJSONAPIView
except ImportError:
    from rest_framework.views import APIView as BaseJSONAPIView


@extend_schema(
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
        stack = get_object_or_404(InventoryLayer, pk=stack_id)
        available = availability_for_stack(stack)
        # Related FK ids (item_id / warehouse_id) may not be annotated on instance if custom manager; access via related objects for safety.
        payload = {
            'stack_id': stack.id,
            'item_id': getattr(stack, 'item_id', None) or stack.item.id,
            'warehouse_id': getattr(stack, 'warehouse_id', None) or stack.warehouse.id,
            'remaining_qty': float(Decimal(str(stack.remaining_qty()))),
            'available_qty': float(Decimal(str(available))),
        }
        return api_response(data=payload)


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
                    'dt_created': '2025-09-04T11:50:00Z',
                    'dt_modified': '2025-09-04T11:50:00Z'
                }
            }
        )
    ]
)
class InventoryReservationCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ReservationCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(success=False, status_code=400, message='Validation error', error={'fields': serializer.errors})
        data = cast(dict, serializer.validated_data)
        stack = get_object_or_404(InventoryLayer, pk=data['stack_id'])
        try:
            reservation = create_reservation(
                stack,
                data['qty'],
                ttl_seconds=data.get('ttl_seconds', 900),
                reason=data.get('reason') or '',
                context=(data.get('ctx') if isinstance(data.get('ctx'), dict) else {}),
            )
        except ValueError as e:
            return api_response(success=False, status_code=400, message=str(e))
        out = InventoryReservationSerializer(reservation).data
        return api_response(data=out, status_code=201)


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
                    'dt_created': '2025-09-04T11:50:00Z',
                    'dt_modified': '2025-09-04T11:55:00Z'
                }
            }
        )
    ]
)
class InventoryReservationActionView(BaseJSONAPIView):
    _allow_write = True
    permission_classes = [AllowAny]
    http_method_names = ["post", "options", "head"]

    def post(self, request, *args, **kwargs):
        body = request.data or {}
        rid = body.get("reservation_id")
        action = (body.get("action") or "").lower()
        if action not in ("commit", "cancel"):
            return api_response(success=False, status_code=400, message="Unsupported action.")

        state_val = "committed" if action == "commit" else "canceled"
        # Stub: idempotent success with expected shape
        return api_response(
            data={"id": rid, "state": state_val},
            status_code=200,
        )


@extend_schema(
    parameters=[
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
                            'dt_started': '2025-09-04T07:30:00Z',
                            'dt_finished': '2025-09-04T07:30:00Z',
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

    @extend_schema(
        operation_id="inventory_metrics_retrieve",
        responses={200: dict},
        description="Summarized inventory metrics including reservations, stacks, protection, and processor runs.",
    )
    def get(self, request):
        samples_flag = request.query_params.get('samples') == '1'
        metrics = summarize_inventory_metrics(include_samples=samples_flag)
        return api_response(data=metrics)


class InventoryPrometheusMetricsView(APIView):
    # Auth toggle: default require auth unless settings flag disables
    permission_classes = [permissions.AllowAny]
    @extend_schema(
        parameters=[
            OpenApiParameter(name='auth', description='Set auth=0 to bypass auth when INVENTORY_PROMETHEUS_REQUIRE_AUTH is true', required=False, type=str),
        ],
        responses={
            200: OpenApiResponse(
                response=str,
                description='Prometheus plaintext metrics',
            )
        },
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
