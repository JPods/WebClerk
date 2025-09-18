from __future__ import annotations

from rest_framework import status, response
from typing import Any, Dict, cast
from rest_framework.views import APIView
from common.decorators import allow_write
from drf_spectacular.utils import extend_schema, OpenApiResponse

from apps.transactions.models import Proposal, SalesOrder, PurchaseOrder, Workorder, WorkorderLine
from apps.core.models.action import Action
from apps.transactions.serializers.actions import (
    ConvertRequestSerializer,
    ReceivePurchaseOrderSerializer,
    TransitionRequestSerializer,
)
from apps.transactions.services.flow import (
    proposal_to_sales_order,
    sales_order_to_invoice,
    sales_order_to_purchase_order,
    receive_purchase_order,
    ReceiveLine,
)
from apps.transactions.views.line_views import BasePermission
from django.utils import timezone
from django.db import transaction


def _is_action_done(act: Action) -> bool:
    """Heuristic: treat action.status in done/completed/closed/resolved as complete.

    Keep permissive to align with current free-form Action.status field.
    """
    st = (act.status or '').strip().lower()
    return st in {"done", "completed", "closed", "resolved", "complete"}


def _check_dependencies(depends_on: dict | None) -> tuple[bool, str | None]:
    """Gate execution based on provided depends_on dict.

    Expected shape (lightweight, evolvable):
      {
        'action': [ids...],
        'work_order': [ids...],
        'work_order_line': [ids...]
      }
    Only present keys are evaluated. Unknown keys are ignored.
    """
    deps = depends_on or {}
    if not isinstance(deps, dict):
        return True, None
    # Actions must be completed
    missing: list[str] = []
    action_ids = deps.get('action') or []
    if isinstance(action_ids, list) and action_ids:
        acts = Action.objects.filter(pk__in=[a for a in action_ids if isinstance(a, int)])
        done_ids = {a.pk for a in acts if _is_action_done(a)}
        pending = [str(aid) for aid in action_ids if isinstance(aid, int) and aid not in done_ids]
        if pending:
            missing.append(f"actions[{', '.join(pending)}]")
    # Workorder dependencies -> require completed
    wo_ids = deps.get('work_order') or []
    if isinstance(wo_ids, list) and wo_ids:
        wos = Workorder.objects.filter(pk__in=[i for i in wo_ids if isinstance(i, int)])
        done = {w.pk for w in wos if (w.status or '').lower() in {'completed', 'complete', 'done'}}
        pend_wo = [str(i) for i in wo_ids if isinstance(i, int) and i not in done]
        if pend_wo:
            missing.append(f"work_orders[{', '.join(pend_wo)}]")
    # Workorder line dependencies -> require done
    wol_ids = deps.get('work_order_line') or []
    if isinstance(wol_ids, list) and wol_ids:
        lines = WorkorderLine.objects.filter(pk__in=[i for i in wol_ids if isinstance(i, int)])
        done_lines = {l.pk for l in lines if (l.status or '').lower() in {'done'}}
        pend_lines = [str(i) for i in wol_ids if isinstance(i, int) and i not in done_lines]
        if pend_lines:
            missing.append(f"work_order_lines[{', '.join(pend_lines)}]")
    if missing:
        return False, "Dependencies not satisfied: " + "; ".join(missing)
    return True, None


@allow_write
class ProposalToSalesOrderView(APIView):
    permission_classes = [BasePermission]
    queryset = Proposal.objects.all()

    @extend_schema(request=ConvertRequestSerializer, responses={201: OpenApiResponse(description="Sales order created")})
    def post(self, request, *args, **kwargs):
        proposal_id = kwargs.get('pk')
        proposal = Proposal.objects.filter(pk=proposal_id).first()
        if not proposal:
            return response.Response({'detail': 'Proposal not found'}, status=404)
        so = proposal_to_sales_order(proposal)
        return response.Response({'sales_order_id': so.id, 'order_no': so.order_no}, status=status.HTTP_201_CREATED)  # type: ignore[attr-defined]


@allow_write
class SalesOrderToInvoiceView(APIView):
    permission_classes = [BasePermission]
    queryset = SalesOrder.objects.all()

    @extend_schema(request=ConvertRequestSerializer, responses={201: OpenApiResponse(description="Invoice created")})
    def post(self, request, *args, **kwargs):
        so_id = kwargs.get('pk')
        so = SalesOrder.objects.filter(pk=so_id).first()
        if not so:
            return response.Response({'detail': 'Sales order not found'}, status=404)
        inv = sales_order_to_invoice(so)
        return response.Response({'invoice_id': inv.id, 'invoice_ida': getattr(inv, 'ida', '')}, status=status.HTTP_201_CREATED)


@allow_write
class SalesOrderToPurchaseOrderView(APIView):
    permission_classes = [BasePermission]
    queryset = SalesOrder.objects.all()

    @extend_schema(request=ConvertRequestSerializer, responses={201: OpenApiResponse(description="Purchase order created")})
    def post(self, request, *args, **kwargs):
        so_id = kwargs.get('pk')
        so = SalesOrder.objects.filter(pk=so_id).first()
        if not so:
            return response.Response({'detail': 'Sales order not found'}, status=404)
        po = sales_order_to_purchase_order(so)
        return response.Response({'purchase_order_id': po.id, 'po_no': po.po_no}, status=status.HTTP_201_CREATED)  # type: ignore[attr-defined]


class LinkageCommentsAggregateView(APIView):
    permission_classes = [BasePermission]

    @extend_schema(responses={200: OpenApiResponse(description="Aggregated comments for linkage")})
    def get(self, request, *args, **kwargs):
        linkage_id = kwargs.get('linkage_id')
        from apps.docs.models.linkage import Linkage
        linkage = Linkage.objects.filter(pk=linkage_id).first()
        if not linkage:
            return response.Response({'detail': 'Linkage not found'}, status=404)
        # Aggregate comments across linked records (headers & lines) fetching their comments JSON if present
        aggregated: list[dict] = []
        links = (getattr(linkage, 'refs', {}) or {}).get('links', {})
        from apps.transactions.models import (
            ProposalLine, SalesOrderLine, InvoiceLine, PurchaseOrderLine
        )
        line_models = [ProposalLine, SalesOrderLine, InvoiceLine, PurchaseOrderLine]
        if isinstance(links, dict):
            for id_list in links.values():
                if not isinstance(id_list, list):
                    continue
                for rec_id in id_list:
                    for lm in line_models:
                        obj = lm.objects.filter(pk=rec_id).first()
                        if obj and isinstance(getattr(obj, 'comments', {}), dict):
                            cm = getattr(obj, 'comments')
                            if any(v for v in cm.values() if isinstance(cm, dict)):
                                aggregated.append({
                                    'model': lm._meta.model_name,  # type: ignore[attr-defined]
                                    'id': rec_id,
                                    'comments': cm,
                                })
                            break
        linkage_comments = getattr(linkage, 'comments', {}) or {}
        # Normalize to ensure a 'general' bucket exists and that simple public/process fields nest under it.
        if 'general' not in linkage_comments or not isinstance(linkage_comments.get('general'), dict):
            # If legacy flat structure (public/process/partner/notes) elevate into general
            flat_keys = {'public', 'process', 'partner', 'notes'}
            if any(k in linkage_comments for k in flat_keys):
                general_block = {k: linkage_comments.get(k, '') for k in flat_keys}
                # Remove moved keys
                for k in flat_keys:
                    linkage_comments.pop(k, None)
                linkage_comments['general'] = general_block
            else:
                linkage_comments.setdefault('general', {})

        return response.Response({
            'linkage_id': linkage.id,  # type: ignore[attr-defined]
            'comments': linkage_comments,
            'items': aggregated
        }, status=200)


@allow_write
class ReceivePurchaseOrderView(APIView):
    permission_classes = [BasePermission]
    queryset = PurchaseOrder.objects.all()

    @extend_schema(request=ReceivePurchaseOrderSerializer, responses={201: OpenApiResponse(description="Receipt posted & inventory updated")})
    def post(self, request, *args, **kwargs):
        po_id = kwargs.get('pk')
        po = PurchaseOrder.objects.filter(pk=po_id).first()
        if not po:
            return response.Response({'detail': 'Purchase order not found'}, status=404)
        ser = ReceivePurchaseOrderSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vd: Dict[str, Any] = cast(Dict[str, Any], ser.validated_data)  # dict-like with required keys
        receipt_no = str(vd['receipt_no'])
        line_payloads = list(vd['lines'])
        lines = [ReceiveLine(**ln) for ln in line_payloads]
        summary = receive_purchase_order(po, receipt_no, lines)
        return response.Response(summary, status=status.HTTP_201_CREATED)


@allow_write
class WorkorderTransitionView(APIView):
    permission_classes = [BasePermission]
    queryset = Workorder.objects.all()

    @extend_schema(request=TransitionRequestSerializer, responses={200: OpenApiResponse(description="Workorder transitioned")})
    def post(self, request, *args, **kwargs):
        wo_id = kwargs.get('pk')
        wo = Workorder.objects.filter(pk=wo_id).first()
        if not wo:
            return response.Response({'detail': 'Workorder not found'}, status=404)
        # Validate dependencies from payload (if any)
        depends_on = request.data.get('depends_on') if isinstance(request.data, dict) else None
        ok, msg = _check_dependencies(depends_on)
        if not ok:
            return response.Response({'detail': msg}, status=409)
        ser = TransitionRequestSerializer(data=request.data, context={'model': Workorder})
        ser.is_valid(raise_exception=True)
        vd = cast(dict, ser.validated_data)
        to = cast(str, vd.get('to'))
        reason = vd.get('reason', '')
        depends_on = vd.get('depends_on') or {}
        prev = wo.status
        action_rec: Action | None = None
        now_ms = int(timezone.now().timestamp() * 1000)
        with transaction.atomic():
            wo.status = to
            try:
                wo.save()
            except Exception as e:  # surface validation error
                return response.Response({'detail': str(e)}, status=400)
            # Create or reuse an idempotent Action record for this transition
            try:
                idem_key = f"wo:{wo.id}:{prev}->{to}:{reason}".strip()
                # Try to find an existing action by idempotency key
                existing = Action.objects.filter(
                    action='transition.work_order',
                    metadata__idempotency_key=idem_key,
                ).first()
                if existing:
                    action_rec = existing
                else:
                    action_rec = Action(
                        action='transition.work_order',
                        action_by=str(getattr(request.user, 'id', 'system')),
                        status='done',
                        description=f"wo_status {prev}->{to}: {reason}".strip(),
                        dt_action=timezone.now(),
                        dt_completed=timezone.now(),
                    )
                    # write refs: links + depends_on
                    refs = getattr(action_rec, 'refs', {}) or {}
                    links = refs.setdefault('links', {})
                    links['work_order'] = [wo.id]
                    if isinstance(depends_on, dict) and depends_on:
                        refs['depends_on'] = depends_on
                    action_rec.refs = refs  # type: ignore[attr-defined]
                    # set metadata idempotency key
                    meta = getattr(action_rec, 'metadata', {}) or {}
                    meta['idempotency_key'] = idem_key
                    action_rec.metadata = meta
                    action_rec.save()
                # We avoid mutating Workorder.refs because Workorder doesn't carry refs json
            except Exception:
                action_rec = None  # non-fatal: continue without action record
            # Minimal audit: stamp metadata.history.action on lines for visibility, include action id
            count = 0
            for ln in wo.lines.all():  # type: ignore[attr-defined]
                meta = getattr(ln, 'metadata', {}) or {}
                hist = meta.setdefault('history', {})
                acts = hist.setdefault('action', []) if isinstance(hist.get('action'), list) else []
                entry = {'by': getattr(request.user, 'id', 0), 'dt': now_ms, 'what': f'wo_status {prev}->{to}', 'reason': reason}
                if action_rec and getattr(action_rec, 'id', None):
                    entry['action_id'] = action_rec.id  # type: ignore[attr-defined]
                acts.append(entry)
                hist['action'] = acts
                ln.metadata = meta
                ln.save(update_fields=['metadata'])
                count += 1
        return response.Response({'id': wo.id, 'status': wo.status, 'lines_audited': count, 'action_id': getattr(action_rec, 'id', None)}, status=200)


@allow_write
class WorkorderLineTransitionView(APIView):
    permission_classes = [BasePermission]
    queryset = WorkorderLine.objects.all()

    @extend_schema(request=TransitionRequestSerializer, responses={200: OpenApiResponse(description="Workorder line transitioned")})
    def post(self, request, *args, **kwargs):
        line_id = kwargs.get('pk')
        ln = WorkorderLine.objects.filter(pk=line_id).first()
        if not ln:
            return response.Response({'detail': 'Workorder line not found'}, status=404)
        depends_on = request.data.get('depends_on') if isinstance(request.data, dict) else None
        ok, msg = _check_dependencies(depends_on)
        if not ok:
            return response.Response({'detail': msg}, status=409)
        ser = TransitionRequestSerializer(data=request.data, context={'model': WorkorderLine})
        ser.is_valid(raise_exception=True)
        vd = cast(dict, ser.validated_data)
        to = cast(str, vd.get('to'))
        reason = vd.get('reason', '')
        depends_on = vd.get('depends_on') or {}
        prev = ln.status or 'planned'
        action_rec: Action | None = None
        with transaction.atomic():
            ln.status = to
            try:
                ln.save()
            except Exception as e:
                return response.Response({'detail': str(e)}, status=400)
            # Create or reuse idempotent Action for this line transition and link it
            try:
                idem_key = f"wol:{ln.id}:{prev}->{to}:{reason}".strip()
                existing = Action.objects.filter(
                    action='transition.work_order_line',
                    metadata__idempotency_key=idem_key,
                ).first()
                if existing:
                    action_rec = existing
                else:
                    action_rec = Action(
                        action='transition.work_order_line',
                        action_by=str(getattr(request.user, 'id', 'system')),
                        status='done',
                        description=f"line_status {prev}->{to}: {reason}".strip(),
                        dt_action=timezone.now(),
                        dt_completed=timezone.now(),
                    )
                    refs = getattr(action_rec, 'refs', {}) or {}
                    links = refs.setdefault('links', {})
                    links['work_order_line'] = [ln.id]
                    if isinstance(depends_on, dict) and depends_on:
                        refs['depends_on'] = depends_on
                    action_rec.refs = refs  # type: ignore[attr-defined]
                    # set idempotency key
                    meta = getattr(action_rec, 'metadata', {}) or {}
                    meta['idempotency_key'] = idem_key
                    action_rec.metadata = meta
                    action_rec.save()
                # Additionally, reciprocate on the line since it has refs
                try:
                    ln_refs = getattr(ln, 'refs', {}) or {}
                    ln_links = ln_refs.setdefault('links', {})
                    actions_list = ln_links.setdefault('actions', [])
                    if action_rec.id not in actions_list:
                        actions_list.append(action_rec.id)  # type: ignore[attr-defined]
                    ln.refs = ln_refs
                    ln.save(update_fields=['refs'])
                except Exception:
                    pass
            except Exception:
                action_rec = None
            # Append audit entry into metadata.history.action as list (include action id)
            meta = getattr(ln, 'metadata', {}) or {}
            hist = meta.setdefault('history', {})
            actions = hist.setdefault('action', []) if isinstance(hist.get('action'), list) else []
            entry = {
                'by': getattr(request.user, 'id', 0),
                'dt': int(timezone.now().timestamp() * 1000),
                'what': f'line_status {prev}->{to}',
                'reason': reason,
            }
            if action_rec and getattr(action_rec, 'id', None):
                entry['action_id'] = action_rec.id  # type: ignore[attr-defined]
            actions.append(entry)
            hist['action'] = actions
            ln.metadata = meta
            ln.save(update_fields=['metadata'])
        return response.Response({'id': ln.id, 'status': ln.status, 'action_id': getattr(action_rec, 'id', None)}, status=200)
