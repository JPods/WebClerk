from __future__ import annotations

from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from common.models import BaseModel
from .item import Item


class BillOfMaterial(BaseModel):

    parent_ida = models.CharField(max_length=120, blank=True, db_index=True, help_text="String identifier for this BOM line")
    parent_description = models.CharField(max_length=255, blank=True, help_text="Description for this parent item (denormalized from Item.description for convenience)", db_column='recalc_parent_cost_description')
    parent_item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="bom_parent", db_column='parent_id')

    @property
    def ida(self):
        return str(self.pk)

    @property
    def item_ida_value(self):
        return self.item_ida or str(self.pk)

    @property
    def description_value(self):
        return self.child_description or str(self.child_item) if hasattr(self, 'child_item') else ""

    """Single component line for an assembled/bundle item.

    Extended with:
      - revision + effective_from/effective_to window for phased BOMs
      - yield_pct (explicit) vs scrap_factor (either can be used; yield derives if one missing)
      - is_alternate / alternate_group for substitution groups
      - is_optional flag
      - cost_snapshot captured at creation (component current standard/avg cost)
      - op_data JSON for lightweight routing/tooling notes
      - validation: quantity>0, 0<=scrap_factor<1, parent!=component, no duplicate sequence per parent+revision
    """


    child_item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="bom_child", db_column='child_id')
    child_ida = models.CharField(max_length=120, blank=True, db_index=True, help_text="String identifier for this BOM child item (denormalized from Item.ida for convenience)")
    child_description = models.CharField(max_length=255, blank=True, help_text="Description for this child item (denormalized from Item.description for convenience)")

    revision = models.CharField(max_length=20, blank=True, default="")
    dt_effective_from = models.DateField(null=True, blank=True)
    dt_effective_to = models.DateField(null=True, blank=True)

    quantity = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal("1"))
    scrap_factor = models.DecimalField(
        max_digits=6, decimal_places=4, default=Decimal("0"), help_text="Scrap ratio (0-1); applied as qty*(1+scrap)"
    )
    yield_pct = models.DecimalField(
        max_digits=6, decimal_places=4, null=True, blank=True, help_text="Optional explicit yield (0-1). If provided, may override scrap calc"
    )
    sequence = models.PositiveIntegerField(default=0)

    is_alternate = models.BooleanField(default=False)
    alternate_group = models.CharField(max_length=40, blank=True, default="", help_text="Group key for alternates")
    is_optional = models.BooleanField(default=False)

    cost_snapshot = models.DecimalField(
        max_digits=14, decimal_places=4, null=True, blank=True, help_text="Component unit cost snapshot at creation"
    )
    op_data = models.JSONField(default=dict, blank=True, help_text="Lightweight routing/tooling notes JSON")
    change_reason = models.CharField(max_length=120, blank=True, default="")
    dt_last_recalc = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"BOM {self.id}: {self.parent_ida} -> {self.child_ida}"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["parent_item", "child_item"], name="uniq_bom_parent_component"),
            models.CheckConstraint(condition=~models.Q(parent_item=models.F('child_item')), name='ck_bom_parent_ne_component'),
            models.CheckConstraint(condition=models.Q(scrap_factor__gte=0) & models.Q(scrap_factor__lt=1), name='ck_bom_scrap_range'),
        ]
        indexes = [
            models.Index(fields=("parent_item",), name="bom_parent_idx"),
            models.Index(fields=("child_item",), name="bom_component_idx"),
            models.Index(fields=("parent_item", "revision", "sequence"), name="bom_parent_rev_seq_idx"),
        ]

    def clean(self):  # pragma: no cover - simple validations
        if self.quantity is None or self.quantity <= 0:
            raise ValidationError({"quantity": "Quantity must be > 0"})
        if self.scrap_factor is None or self.scrap_factor < 0 or self.scrap_factor >= 1:
            raise ValidationError({"scrap_factor": "Scrap factor must be between 0 (inclusive) and 1 (exclusive)"})
        parent_pk = self.parent_item.pk if self.parent_item else None
        component_pk = self.child_item.pk if self.child_item else None
        if parent_pk and component_pk and parent_pk == component_pk:
            raise ValidationError("Parent and component cannot be the same item")
        # Recursive cycle detection: ensure adding parent->component line will not introduce a cycle
        if parent_pk and component_pk and self._would_create_cycle(parent_pk, component_pk):
            raise ValidationError("BOM cycle detected: component appears in parent's descendant chain")
        if self.is_alternate and not self.alternate_group:
            raise ValidationError({"alternate_group": "Alternate lines must have an alternate_group"})
        if self.dt_effective_from and self.dt_effective_to and self.dt_effective_to < self.dt_effective_from:
            raise ValidationError({"dt_effective_to": "dt_effective_to must be >= dt_effective_from"})

    def save(self, *args, **kwargs):  # pragma: no cover - indirect validation
        creating = self._state.adding
        # Derive yield_pct from scrap_factor if not set
        if self.yield_pct is None and self.scrap_factor is not None:
            try:
                self.yield_pct = Decimal("1") - (self.scrap_factor if self.scrap_factor < 1 else Decimal("0"))
            except Exception:
                pass
        # Capture cost snapshot on create
        component_pk = self.child_item.pk if self.child_item else None
        if creating and self.cost_snapshot is None and component_pk:
            val = getattr(self.child_item, 'cost', None)
            if isinstance(val, dict):
                # Cost precedence order:
                # We intentionally probe keys in this fixed sequence so the first
                # populated value becomes the snapshot. Treat the first non-null as
                # the "authoritative" unit cost for BOM purposes.
                # Default order (highest priority first): avg → standard → last → landed.
                # Rationale: avg typically reflects rolling actuals; if absent fall back
                # to standard cost policy; if neither present try last receipt; finally
                # landed (may be noisy with freight allocations). Reordering this tuple
                # lets an implementation shift precedence without schema changes.
                for key in ("avg", "standard", "last", "landed"):
                    raw = val.get(key)
                    if raw is not None:
                        try:
                            self.cost_snapshot = Decimal(str(raw))
                            break
                        except Exception:
                            continue
            self.dt_last_recalc = timezone.now()
        super().save(*args, **kwargs)
        # Denormalize BOM into parent item.refs.bom[]
        self._denorm_parent_bom()

    def _denorm_parent_bom(self):
        """Rebuild parent_item.refs.bom[] from all BOM lines for this parent.

        If parent is locked (journalized invoice, reconciled payment, etc.),
        creates a Pending record so the denorm retries when the lock clears.
        """
        try:
            parent = self.parent_item
            parent.refresh_from_db(fields=['is_locked', 'refs'])

            bom_list = self._build_bom_list(parent.pk)

            if getattr(parent, 'is_locked', False):
                self._create_denorm_pending(parent, bom_list)
                return

            refs = parent.refs if isinstance(parent.refs, dict) else {}
            refs['bom'] = bom_list
            Item.objects.filter(pk=parent.pk).update(refs=refs)
        except Exception:
            pass  # best-effort denorm

    @staticmethod
    def _build_bom_list(parent_id):
        """Build the denormalized BOM list for a parent item."""
        bom_lines = BillOfMaterial.objects.filter(
            parent_item_id=parent_id
        ).select_related('child_item').order_by('sequence')
        return [{
            'id': line.pk,
            'child_id': line.child_item_id,
            'child_ida': line.child_ida or (line.child_item.ida if line.child_item else ''),
            'child_name': line.child_item.name if line.child_item else '',
            'quantity': float(line.quantity),
            'sequence': line.sequence,
            'cost_snapshot': float(line.cost_snapshot) if line.cost_snapshot else None,
            'is_alternate': line.is_alternate,
            'is_optional': line.is_optional,
        } for line in bom_lines]

    @staticmethod
    def _create_denorm_pending(parent, bom_list):
        """Create a Pending record to retry denorm when parent unlocks."""
        try:
            from apps.core.models import Pending
            Pending.objects.create(
                model_name='item',
                record_id=str(parent.pk),
                purpose='denorm_refs',
                name=f'Denorm BOM: Item {parent.ida}',
                config={
                    'field': 'refs.bom',
                    'bom': bom_list,
                    'reason': 'parent_locked',
                    'parent_ida': parent.ida,
                },
            )
        except Exception:
            pass

    def delete(self, *args, **kwargs):
        parent = self.parent_item
        super().delete(*args, **kwargs)
        # Rebuild after delete — respects lock
        try:
            parent.refresh_from_db(fields=['is_locked', 'refs'])
            bom_list = self._build_bom_list(parent.pk)
            if getattr(parent, 'is_locked', False):
                self._create_denorm_pending(parent, bom_list)
            else:
                refs = parent.refs if isinstance(parent.refs, dict) else {}
                refs['bom'] = bom_list
                Item.objects.filter(pk=parent.pk).update(refs=refs)
        except Exception:
            pass

    # Lightweight roll-up helper (not auto-invoked here to avoid recursion) -----------------
    @staticmethod
    def recalc_parent_cost(parent_item_id: int, depth: int = 1):  # pragma: no cover - service style
        """Recompute aggregate component cost for a parent item.

        Args:
            parent_item_id: the parent item to recalculate
            depth: how deep to explode the BOM
              - 1: immediate children only (kit — use component costs as-is)
              - 2: children + grandchildren (intermediate assemblies exploded one level)
              - 0 or -1: all levels (full tree to leaf nodes)

        Depth matters for inventory:
          - depth=1: "I have subassemblies in stock, cost them as units"
          - depth=2: "Explode one level deeper for intermediate builds"
          - depth=0: "Cost from raw materials — full explosion"

        If a child is itself a parent (has BOM children) and depth allows,
        its cost is recursively computed from its children rather than using
        its own cost_snapshot or cost.avg.

        Stores result in parent.cost['components']['snapshot_total'].
        Also records depth used in parent.cost['components']['depth'].
        """
        try:
            parent = Item.objects.get(id=parent_item_id)
        except Exception:
            return
        from decimal import Decimal as _D

        # Normalize depth: 0 or negative = unlimited
        max_depth = depth if depth > 0 else 999

        total = BillOfMaterial._rollup_cost(parent_item_id, max_depth, current_depth=0)

        try:
            if isinstance(parent.cost, dict):
                comp = parent.cost.setdefault('components', {})
                try:
                    total = total.quantize(_D("0.0001"))
                except Exception:
                    pass
                comp['snapshot_total'] = float(total)
                comp['depth'] = depth
                if parent.cost.get('avg') in (None, 0, 0.0):
                    parent.cost['avg'] = float(total)
            parent.save(update_fields=['cost'])
        except Exception:
            return

    @staticmethod
    def _rollup_cost(parent_item_id: int, max_depth: int, current_depth: int) -> 'Decimal':
        """Recursively compute BOM cost, respecting depth limit.

        At each level:
          - If the child has its own BOM children AND we haven't hit max_depth,
            recurse into the child (explode it).
          - Otherwise, use the child's cost_snapshot or cost.avg (treat it as
            a purchased/stocked component — don't explode further).

        This means depth=1 uses each child's own cost (kit mode).
        Depth=2 explodes children that have BOMs, but uses grandchildren's
        own costs. Depth=0 (unlimited) walks to leaf nodes.
        """
        from decimal import Decimal as _D

        lines = BillOfMaterial.objects.filter(
            parent_item_id=parent_item_id
        ).select_related('child_item')

        total = _D("0")

        for line in lines:
            try:
                qty = line.quantity or _D("0")
                scrap = line.scrap_factor or _D("0")

                # Check if child has its own BOM and we can go deeper
                child_has_bom = BillOfMaterial.objects.filter(
                    parent_item_id=line.child_item_id
                ).exists() if current_depth + 1 < max_depth else False

                if child_has_bom:
                    # Explode: child's cost comes from its children
                    unit_cost = BillOfMaterial._rollup_cost(
                        line.child_item_id, max_depth, current_depth + 1
                    )
                else:
                    # Leaf or depth limit: use component's own cost
                    unit_cost = line.cost_snapshot
                    if unit_cost is None:
                        comp_cost = getattr(line.child_item, 'cost', None)
                        if isinstance(comp_cost, dict):
                            for key in ("avg", "standard", "last", "landed"):
                                raw = comp_cost.get(key)
                                if raw is not None:
                                    try:
                                        unit_cost = _D(str(raw))
                                        break
                                    except Exception:
                                        continue
                    if unit_cost is None:
                        continue

                total += unit_cost * qty * (_D("1") + scrap)
            except Exception:
                continue

        return total

    # ----------------- Cycle / recursion utilities ---------------------------------
    @staticmethod
    def _descendant_component_ids(root_parent_id: int, max_depth: int = 20) -> set[int]:  # pragma: no cover - helper
        """Return set of all component item IDs reachable from parent within max_depth.

        Simple DFS using BillOfMaterial table; depth guard prevents infinite loops in pathological data.
        """
        from collections import deque
        visited: set[int] = set()
        queue = deque([(root_parent_id, 0)])
        while queue:
            current_parent_id, depth = queue.popleft()
            if depth >= max_depth:
                continue
            child_lines = BillOfMaterial.objects.filter(parent_item_id=current_parent_id).values_list('child_item_id', flat=True)
            for comp_id in child_lines:
                if comp_id in visited:
                    continue
                visited.add(comp_id)
                queue.append((comp_id, depth + 1))
        return visited

    def _would_create_cycle(self, parent_id: int, component_id: int) -> bool:  # pragma: no cover - helper
        """Check if introducing (parent_id -> component_id) creates a cycle.

        Cycle exists if parent_id reachable from component_id through existing chains.
        """
        if parent_id == 0 or component_id == 0:
            return False
        # Fast reject: if parent not among descendant components of proposed component
        descendants = self._descendant_component_ids(component_id)
        return parent_id in descendants
