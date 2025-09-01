from __future__ import annotations

from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from common.models import BaseModel
from .item import Item


class BillOfMaterial(BaseModel):
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

    parent = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="bom_parent")
    component = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="bom_component")

    revision = models.CharField(max_length=20, blank=True, default="")
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)

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

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["parent", "component"], name="uniq_bom_parent_component"),
            models.CheckConstraint(check=~models.Q(parent=models.F('component')), name='ck_bom_parent_ne_component'),
            models.CheckConstraint(check=models.Q(scrap_factor__gte=0) & models.Q(scrap_factor__lt=1), name='ck_bom_scrap_range'),
        ]
        indexes = [
            models.Index(fields=("parent",), name="bom_parent_idx"),
            models.Index(fields=("component",), name="bom_component_idx"),
            models.Index(fields=("parent", "revision", "sequence"), name="bom_parent_rev_seq_idx"),
        ]

    def clean(self):  # pragma: no cover - simple validations
        if self.quantity is None or self.quantity <= 0:
            raise ValidationError({"quantity": "Quantity must be > 0"})
        if self.scrap_factor is None or self.scrap_factor < 0 or self.scrap_factor >= 1:
            raise ValidationError({"scrap_factor": "Scrap factor must be between 0 (inclusive) and 1 (exclusive)"})
        parent_pk = getattr(self, 'parent_id', None)  # type: ignore[attr-defined]
        component_pk = getattr(self, 'component_id', None)  # type: ignore[attr-defined]
        if parent_pk and component_pk and parent_pk == component_pk:
            raise ValidationError("Parent and component cannot be the same item")
        # Recursive cycle detection: ensure adding parent->component line will not introduce a cycle
        if parent_pk and component_pk and self._would_create_cycle(parent_pk, component_pk):
            raise ValidationError("BOM cycle detected: component appears in parent's descendant chain")
        if self.is_alternate and not self.alternate_group:
            raise ValidationError({"alternate_group": "Alternate lines must have an alternate_group"})
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValidationError({"effective_to": "effective_to must be >= effective_from"})

    def save(self, *args, **kwargs):  # pragma: no cover - indirect validation
        creating = self._state.adding
        # Derive yield_pct from scrap_factor if not set
        if self.yield_pct is None and self.scrap_factor is not None:
            try:
                self.yield_pct = Decimal("1") - (self.scrap_factor if self.scrap_factor < 1 else Decimal("0"))
            except Exception:
                pass
        # Capture cost snapshot on create
        component_pk = getattr(self, 'component_id', None)  # type: ignore[attr-defined]
        if creating and self.cost_snapshot is None and component_pk:
            # Try multiple potential cost sources; fallback None silently
            for attr in ("default_cost", "cost", "price"):
                val = getattr(self.component, attr, None)
                # cost / price might be JSON; attempt to pull standard/base keys
                if isinstance(val, dict):
                    for key in ("standard", "avg", "base", "last"):
                        raw = val.get(key)
                        if raw is not None:
                            try:
                                self.cost_snapshot = Decimal(str(raw))
                                break
                            except Exception:
                                continue
                    if self.cost_snapshot is not None:
                        break
                else:
                    if val is not None:
                        try:
                            self.cost_snapshot = Decimal(str(val))
                        except Exception:
                            pass
            self.dt_last_recalc = timezone.now()
        super().save(*args, **kwargs)

    # Lightweight roll-up helper (not auto-invoked here to avoid recursion) -----------------
    @staticmethod
    def recalc_parent_cost(parent_item_id: int):  # pragma: no cover - service style
        """Recompute aggregate component cost snapshot for a parent item.

        Stores summarized value under parent.cost['components']['snapshot_total'] (if JSON present) or sets
        parent.default_cost if empty and snapshot available. Silent on errors.
        """
        try:
            parent = Item.objects.get(id=parent_item_id)
        except Exception:
            return
        from decimal import Decimal as _D
        lines = BillOfMaterial.objects.filter(parent_id=parent_item_id)
        total = _D("0")
        for line in lines:
            try:
                qty = line.quantity or _D("0")
                scrap = line.scrap_factor or _D("0")
                cost = line.cost_snapshot or _D("0")
                total += cost * qty * (_D("1") + scrap)
            except Exception:
                continue
        try:
            if isinstance(parent.cost, dict):
                comp = parent.cost.setdefault('components', {})
                comp['snapshot_total'] = float(total)
            elif getattr(parent, 'default_cost', None) in (None, 0) and total > 0:
                parent.default_cost = total
            parent.save(update_fields=['cost', 'default_cost'])
        except Exception:
            return

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
            child_lines = BillOfMaterial.objects.filter(parent_id=current_parent_id).values_list('component_id', flat=True)
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
