from __future__ import annotations
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Callable, Iterable, Optional, Sequence
from django.apps import apps
from django.utils import timezone

@dataclass(frozen=True)
class RefsRule:
    # Which source objects this rule governs
    source_model: str             # e.g. "billing.invoice_line"
    # Where links live (the owner object we attach to, e.g., Customer)
    attach_to_model: str          # e.g. "accounts.customer"
    kind: str                     # logical bucket name used in link entry
    include_recent_days: int = 30
    require_open_actions: bool = False
    max_items_per_kind: int = 500
    enabled: bool = True

class PolicyEngine:
    def __init__(self, rules: Sequence[RefsRule], settings_provider: Optional[Callable[[Any], dict]] = None):
        self.rules = [r for r in rules if r.enabled]
        self._settings_provider = settings_provider

    def rule_for(self, *, source_model: str, attach_to_model: str, kind: str) -> Optional[RefsRule]:
        for r in self.rules:
            if r.source_model == source_model and r.attach_to_model == attach_to_model and r.kind == kind:
                return r
        return None

    def should_attach(self, source_obj, attach_to_obj, *, kind: str) -> bool:
        now = timezone.now()
        src_label = source_obj._meta.label_lower
        dst_label = attach_to_obj._meta.label_lower
        rule = self.rule_for(source_model=src_label, attach_to_model=dst_label, kind=kind)
        if not rule:
            return False
        # recency
        dt = _best_dt(source_obj)
        if dt and dt < now - timedelta(days=rule.include_recent_days):
            return False
        # actions
        if rule.require_open_actions and not _has_open_actions(source_obj):
            return False
        return True

    def prune_links_for(self, owner_obj) -> bool:
        """
        Remove links on owner_obj.refs.links that no longer satisfy rules
        or exceed per-kind caps. Returns True if mutated.
        """
        links = getattr(owner_obj, "refs", {}).get("links") or []
        if not links:
            return False

        # Group links by kind for cap enforcement
        by_kind: dict[str, list[dict]] = {}
        for e in links:
            by_kind.setdefault(e.get("kind") or "", []).append(e)

        mutated = False
        new_links: list[dict] = []

        now = timezone.now()
        for kind, entries in by_kind.items():
            # Apply per-kind pruning rules
            kept: list[dict] = []
            for e in entries:
                model_label = e.get("model")
                if not model_label:
                    continue
                app_label, model_name = model_label.split(".")
                Model = apps.get_model(app_label, model_name)
                if not Model:
                    continue
                try:
                    obj = Model.objects.filter(pk=e.get("id")).only("id").first()
                except Exception:
                    obj = None
                if not obj:
                    mutated = True
                    continue  # drop dead link

                # Find a matching rule (if any)
                rule = self.rule_for(source_model=model_label, attach_to_model=owner_obj._meta.label_lower, kind=kind)
                if rule:
                    # recency check
                    dt = _best_dt(obj)
                    if dt and dt < now - timedelta(days=rule.include_recent_days):
                        mutated = True
                        continue
                    # actions check
                    if rule.require_open_actions and not _has_open_actions(obj):
                        mutated = True
                        continue
                kept.append(e)

            # Enforce max_items_per_kind if any rule applies
            # Determine rule for this kind using a valid source_model label (if present)
            rule: Optional[RefsRule] = None
            if entries:
                possible_label = entries[0].get("model")
                if isinstance(possible_label, str):
                    rule = self.rule_for(source_model=possible_label, attach_to_model=owner_obj._meta.label_lower, kind=kind)
            max_items = rule.max_items_per_kind if rule else None
            if max_items and len(kept) > max_items:
                # Prefer newest by timestamp if present
                kept.sort(key=lambda x: x.get("ts") or "", reverse=True)
                kept = kept[:max_items]
                mutated = True

            new_links.extend(kept)

        if mutated:
            base = getattr(owner_obj, "refs", None) or {}
            base["links"] = new_links
            setattr(owner_obj, "refs", base)
        return mutated

def _best_dt(obj):
    for attr in ("updated_at", "modified_at", "created_at", "created"):
        dt = getattr(obj, attr, None)
        if dt:
            return dt
    return None

def _has_open_actions(obj) -> bool:
    # Heuristic placeholder; adapt to your actions/assignments model
    if hasattr(obj, "open_actions_count"):
        return (getattr(obj, "open_actions_count") or 0) > 0
    if hasattr(obj, "actions"):
        try:
            return obj.actions.filter(status__in=("open", "pending")).exists()
        except Exception:
            return False
    return False

def default_rules() -> list[RefsRule]:
    # Example defaults; adjust model labels/kinds to your domain
    return [
        # Only keep recent invoice lines on the customer’s refs
        RefsRule(source_model="billing.invoice_line", attach_to_model="accounts.customer", kind="invoice_line", include_recent_days=30, require_open_actions=False, max_items_per_kind=1000),
        # Invoices: even stricter by default
        RefsRule(source_model="billing.invoice", attach_to_model="accounts.customer", kind="invoice", include_recent_days=90, require_open_actions=False, max_items_per_kind=500),
        # Orders with open actions stick around regardless of age
        RefsRule(source_model="orders.order", attach_to_model="accounts.customer", kind="order", include_recent_days=365, require_open_actions=True, max_items_per_kind=500),
    ]