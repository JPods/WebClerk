"""Production workorders: one item per line, signed — Expand and Complete.

Bill, 2026-09-26: "Deal with workorders 1 item at a time in a uniform way, regardless of + or -."
A line is one item and a signed quantity: a **build** line (+) is the item being made; a **consume**
line (−) a part it uses; a **scrap** line (−) the part expected lost, corrected to the actual scrap
before Complete (Bill, 2026-09-27). Three behaviours:

1. No BOM — lines entered by hand, the + line's cost entered on it.
2. One BOM level — Expand depth 1: a − line per child.
3. Full BOM — Expand depth 0: a − line per item with no children; a + and a − line for each item that
   has children (built and used: net zero stock, its cost carried up).

Nothing moves until **Complete**, which writes every line's Pending through the line door, deepest
first — a node's parts, then its + line (costed from the layers they consumed), then its own − line
— in one transaction: all of it, or none of it.
~/Allie/readmes/assessments/2026-09-26-workorder-window.md
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from apps.core.services.door import Refused

PRODUCTION_TYPES = ('build', 'consume', 'scrap')


def _lines(wo):
    from apps.transactions.models import WorkOrderLine
    return list(WorkOrderLine.objects.select_for_update().filter(workorder_id=wo.pk).order_by('line_number', 'id'))


def _bom(line) -> Dict[str, Any]:
    refs = line.refs if isinstance(getattr(line, 'refs', None), dict) else {}
    return refs.get('bom') if isinstance(refs.get('bom'), dict) else {}


def _item_env(item) -> Dict[str, Any]:
    return {'item_id': item.pk, 'id_num': item.pk, 'ida': item.ida or '', 'description': item.name or ''}


def is_full_bom_locked(workorder_id) -> bool:
    """A workorder expanded by full BOM is locked from normal editing (Bill, 2026-09-27: "This
    applies to workorders exploded by all BOM. If exploding by 1 BOM user might edit.")."""
    from apps.transactions.models import WorkOrderLine
    return WorkOrderLine.objects.filter(workorder_id=workorder_id, refs__bom_expand__depth=0).exists()


def _refuse_production_state(wo, lines) -> None:
    if getattr(wo, 'kind', '') == 'count':
        raise Refused(400, 'count_workorder', 'A count workorder has no BOM to expand or build to complete.', wo.pk)
    if getattr(wo, 'status', '') == 'complete' or any(l.events for l in lines):
        raise Refused(409, 'workorder_complete',
                      'This workorder is complete; make a new workorder for another build.', wo.pk)


def _bom_children(item_id: int):
    from apps.products.services.bom_ops import list_bom_lines
    return [b for b in list_bom_lines(item_id, as_of=date.today())
            if not b.is_alternate and getattr(b, 'is_active', True)]


# ── Expand ──────────────────────────────────────────────────────────────────────────────────

def expand(ctx) -> Dict[str, Any]:
    """POST /wcapi/workorder/<id>/expand/ {line_id, depth: 1|0}.

    Replaces the lines an earlier expand made under that build line, then writes the BOM's lines:
    depth 1 one level, depth 0 the whole tree. A component's − line takes the BOM's stated quantity
    (``op_data.per_batch``: per build, not per unit); a component with a scrap_factor also gets its
    own − scrap line (stated × scrap_factor, fractional allowed). Refused once anything has moved.
    """
    from apps.transactions.models import WorkOrderLine
    wo = ctx.obj
    data = ctx.data or {}
    lines = _lines(wo)
    _refuse_production_state(wo, lines)
    try:
        depth = int(data.get('depth', 1))
    except (TypeError, ValueError):
        depth = -1
    if depth not in (0, 1):
        raise Refused(400, 'depth_invalid', 'depth is 1 (one BOM level) or 0 (the full BOM).', data.get('depth'))
    root = next((l for l in lines if str(l.pk) == str(data.get('line_id'))), None)
    if root is None or root.line_type != 'build':
        raise Refused(400, 'build_line_required', "Name the workorder's build (+) line to expand.",
                      data.get('line_id'))
    if _bom(root).get('root_line_id'):
        raise Refused(400, 'expand_the_top', 'Expand the build line at the top of the tree.', root.pk)

    for line in lines:                         # replace what an earlier expand made
        if _bom(line).get('root_line_id') == root.pk:
            line._actor = ctx.actor
            line._by_command = True
            line.delete()

    from apps.products.models import Item
    top = Item.objects.get(pk=root.item_fk_id or (root.item or {}).get('item_id'))
    made: List[int] = []

    def write(line_type: str, item, qty: Decimal, bom: Dict[str, Any], cost_unit=None) -> WorkOrderLine:
        line = WorkOrderLine(workorder=wo, line_type=line_type, item=_item_env(item), item_fk_id=item.pk,
                             quantity={'active': float(qty)}, refs={'bom': {'root_line_id': root.pk, **bom}})
        if cost_unit is not None:
            line.cost = {'unit': float(cost_unit)}
        line._actor = ctx.actor
        line._by_command = True
        line.save()
        made.append(line.pk)
        return line

    def walk(parent_item, parent_qty: Decimal, parent_line_id: int, level: int, seen: frozenset):
        for b in _bom_children(parent_item.pk):
            child = b.child_item
            if child.pk in seen:
                raise Refused(400, 'bom_cycle', f'{child.ida or child.pk} contains itself in its BOM.', child.pk)
            per_batch = bool((b.op_data or {}).get('per_batch'))
            qty = Decimal(str(b.quantity)) if per_batch else Decimal(str(b.quantity)) * parent_qty
            has_children = depth == 0 and bool(_bom_children(child.pk))
            ref = {'bom_id': b.pk, 'parent_line_id': parent_line_id, 'depth': level}
            if has_children:
                plus = write('build', child, qty, {**ref, 'role': 'subassembly'})
                write('consume', child, -qty, {**ref, 'role': 'subassembly_used', 'of_line_id': plus.pk})
                walk(child, qty, plus.pk, level + 1, seen | {child.pk})
            else:
                # Labor and other untracked items carry cost only: stated hours × the item's
                # standard rate (09-22 ruling 1a.2).
                rate = (child.cost or {}).get('standard') if child.is_not_tracked else None
                part = write('consume', child, -qty, {**ref, 'role': 'component'}, cost_unit=rate)
                scrap = Decimal(str(b.scrap_factor or 0))
                if scrap > 0:
                    write('scrap', child, -(qty * scrap).quantize(Decimal('0.0001')),
                          {**ref, 'role': 'scrap', 'of_line_id': part.pk})

    walk(top, Decimal(str((root.quantity or {}).get('active') or 0)), root.pk, 1, frozenset({top.pk}))
    # How it was expanded, on the build line itself. Full BOM locks the workorder from normal
    # editing (Bill, 2026-09-27); one level stays editable. .update(): no door, nothing moves.
    refs = dict(root.refs) if isinstance(root.refs, dict) else {}
    refs['bom_expand'] = {'depth': depth}
    WorkOrderLine.objects.filter(pk=root.pk).update(refs=refs)
    return {'workorder_id': wo.pk, 'line_id': root.pk, 'depth': depth, 'lines_created': made}


# ── Complete ────────────────────────────────────────────────────────────────────────────────

def _apply(line, item_id: int, deltas: Dict[str, float], *, reason: str, layer=None, event_extra=None):
    """One line's Pending through the door's writer; it must apply now, or Complete is refused whole."""
    from apps.transactions.services.line_door import _write
    pending = _write(line, item_id, deltas, reason=reason, layer=layer, event_extra=event_extra)
    pending.refresh_from_db()
    if not pending.is_processed():
        raise Refused(409, 'item_locked',
                      f'Item {item_id} is busy (locked by another save); nothing was completed. Try again.',
                      {'line_id': line.pk, 'item_id': item_id})
    line.refresh_from_db()
    return pending


def _consumed_cost(line) -> Decimal:
    """What a − line took from the layers (its last event), or, for an untracked line, its cost."""
    for event in reversed(line.events or []):
        if isinstance(event, dict):
            if isinstance(event.get('consumed'), dict):
                return Decimal(str(event['consumed'].get('cost') or 0))
            if 'cost' in event:
                return Decimal(str(event.get('cost') or 0))
    return Decimal('0')


def complete(ctx) -> Dict[str, Any]:
    """POST /wcapi/workorder/<id>/complete/ — the build moves its stock, all or nothing.

    Per build line, deepest first: its subassemblies (each built, then used from the layer it just
    made), its parts and scrap, then the + line itself, costed from the layers its − lines consumed
    (Bill: "Actual costs come from inventory_layers consumed"). Every Pending goes through the line
    door's writer; the applier is the only thing that moves stock. A Pending that cannot apply now
    refuses the whole Complete.
    """
    from apps.transactions.models.base_line_model import line_item_id
    from apps.transactions.services.line_door import _is_tracked, _stock_warehouse

    wo = ctx.obj
    lines = _lines(wo)
    _refuse_production_state(wo, lines)
    others = [l for l in lines if l.line_type not in PRODUCTION_TYPES]
    if others:
        raise Refused(400, 'production_line_type',
                      "A build's lines are build (+), consume (−) or scrap (−).",
                      {'line_ids': [l.pk for l in others]})
    builds = [l for l in lines if l.line_type == 'build']
    tops = [l for l in builds if not _bom(l).get('parent_line_id')]
    if not tops:
        raise Refused(400, 'build_line_required', 'A build needs a build (+) line: the item being made.', wo.pk)

    def children(build) -> List:
        kids = [l for l in lines if _bom(l).get('parent_line_id') == build.pk]
        if build in tops and len(tops) == 1:
            # Lines entered by hand (no BOM link) belong to the one item being made.
            kids += [l for l in lines if l is not build and not _bom(l) and l.line_type != 'build']
        return kids

    unlinked = [l for l in lines if not _bom(l) and l.line_type != 'build']
    if unlinked and len(tops) > 1:
        raise Refused(400, 'line_unlinked', 'With several items being made, link each part to its build line.',
                      {'line_ids': [l.pk for l in unlinked]})

    done: List[int] = []

    def use(line, *, from_layer: Optional[int] = None) -> Decimal:
        item_id = line_item_id(line)
        qty = abs(Decimal(str((line.quantity or {}).get('active') or 0)))
        if not qty:
            return Decimal('0')
        line._actor = ctx.actor
        if not _is_tracked(item_id):
            from apps.products.models import Item
            rate = (line.cost or {}).get('unit') or ((Item.objects.filter(pk=item_id).values_list(
                'cost', flat=True).first() or {}).get('standard'))
            cost = Decimal(str(rate or 0)) * qty
            _apply(line, item_id, {}, reason=line.line_type, event_extra={'qty': float(-qty), 'cost': float(cost)})
        else:
            _apply(line, item_id, {'on_hand': float(-qty)}, reason=line.line_type,
                   layer=[{'consume': float(qty), 'layer_id': from_layer}])
        done.append(line.pk)
        return _consumed_cost(line)

    def build(line) -> Optional[int]:
        total = Decimal('0')
        kids = children(line)
        subs = {l.pk: l for l in kids if l.line_type == 'build'}
        for kid in kids:                                   # subassemblies first, each then used
            if kid.line_type == 'build':
                continue
            pair = _bom(kid).get('of_line_id')
            if kid.line_type == 'consume' and pair in subs:
                layer_id = build(subs.pop(pair))
                total += use(kid, from_layer=layer_id)
        for kid in kids:                                   # then parts and scrap
            if kid.line_type in ('consume', 'scrap') and kid.pk not in done:
                total += use(kid)
        qty = Decimal(str((line.quantity or {}).get('active') or 0))
        if qty <= 0:
            raise Refused(400, 'build_quantity', 'A build line makes a positive quantity.', line.pk)
        entered = Decimal(str((line.cost or {}).get('unit') or 0))
        unit = (total / qty) if kids else entered          # case 1: the cost entered on the line
        line._actor = ctx.actor
        _apply(line, line_item_id(line), {'on_hand': float(qty)}, reason='build',
               layer=[{'build': float(qty), 'warehouse_id': _stock_warehouse(line), 'unit_cost': float(unit)}],
               event_extra={'unit_cost': float(unit), 'parts_cost': float(total)})
        done.append(line.pk)
        return line.inventory_layer_id

    made = [{'line_id': top.pk, 'layer_id': build(top)} for top in tops]
    wo.status = 'complete'
    wo.save(update_fields=['status', 'dt_modified', 'version'])
    return {'workorder_id': wo.pk, 'made': made, 'lines_applied': len(done)}


def register() -> None:
    from apps.core.services.verbs import register_command
    register_command('workorder', 'expand', expand)
    register_command('workorder', 'complete', complete)
