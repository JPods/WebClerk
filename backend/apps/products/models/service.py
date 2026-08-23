from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import TYPE_CHECKING, TypedDict, List, Dict, Any, Optional, Tuple
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError

if TYPE_CHECKING:  # pragma: no cover - typing only
    class BillingTier(TypedDict, total=False):
        unit: str
        rate: float
        cost: float
        min_minutes: int
        dt_effective: int

    class ProcessStep(TypedDict, total=False):
        name: str
        minutes: int

from .item_base_model import ItemLinkedBase


def default_billing():
    """Billing JSON schema

    Structure:
        currency (str): ISO currency code used for all monetary values (default 'USD').
        tiers (list[dict]): Chronologically sorted pricing tiers (earliest -> latest). Each tier dict:
            unit (str): Billing unit (e.g. 'hour', 'minute', 'day').
            rate (float): Sell rate per unit.
            cost (float): Internal cost per unit (optional; 0 default).
            min_minutes (int): Minimum billable minutes for a call under this tier.
            dt_effective (int): Epoch ms when tier becomes effective (0 = legacy / default).
        travel (dict): Per‑unit travel pricing adjustments:
            per_mile (float): Bill rate per mile beyond included_miles.
            per_hour (float): Bill rate per hour of travel (if applicable).
            included_miles (int): Miles included before per_mile applies.
            dt_updated (int): Epoch ms of last travel pricing update.
        version (int): Schema version for future evolution.
    """
    return {
        "currency": "USD",
        "tiers": [],
        "travel": {"per_mile": 0.0, "per_hour": 0.0, "included_miles": 0, "dt_updated": 0},
        "rounding": {"strategy": "HALF_UP", "places": 2},  # rounding policy for compute_charge
        "min_charge": None,  # optional absolute minimum invoice amount
        "max_charge": None,  # optional cap
        "version": 1,
        "schema_version": 1,
    }


def default_process():
    """Process / workflow schema

    steps (list[dict]): Ordered list describing the nominal workflow for the service.
        Each step dict:
            name (str): Short machine/human readable identifier.
            minutes (int): Estimated minutes for the step.
    version (int): Schema version.
    dt_updated (int): Epoch ms of last modification.
    """
    return {"steps": [], "version": 1, "dt_updated": 0, "schema_version": 1}


def default_travel_details():
    """Travel requirement schema

    miles_included (int): Miles bundled before extra charges.
    lodging_required (bool): If typical engagement requires overnight stay.
    meal_per_diem (float): Allowance per day for meals.
    notes (str): Free‑form annotations (routes, region constraints, etc.).
    dt_updated (int): Epoch ms of last update.
    """
    return {"miles_included": 0, "lodging_required": False, "meal_per_diem": 0.0, "notes": "", "dt_updated": 0, "schema_version": 1}


class Service(ItemLinkedBase):
    """Service / labor extension for an Item.

    Field Overview:
        description: Short summary of the service.
        purpose: Why / for whom the service exists (used for filtering & display).
        category: Taxonomy bucket (installation, consulting, training, etc.).
        display: Rich long‑form (HTML / markdown) marketing or procedural description.
        billing (JSON): Structured pricing (see default_billing docstring).
        process (JSON): Ordered workflow steps (default_process schema).
        travel (JSON): Logistical travel qualifiers (default_travel_details schema).
        default_duration_minutes: Suggested baseline duration for quoting / scheduling.
        rates (JSON, deprecated): Legacy raw rate structure retained temporarily for migration.
        minutes_minimum_bill (int, deprecated): Legacy minimum billable minutes (migrated into billing.tiers[].min_minutes).
    """

    # Core descriptive metadata
    description = models.CharField(max_length=255, blank=True)  # human readable summary
    category = models.CharField(max_length=120, blank=True, help_text="Service category or type")
    display = models.TextField(blank=True, help_text="Rich text / HTML description")

    # Structured JSON envelopes
    # spawns one or more specific action records to 
    actions = models.JSONField(default=dict, blank=True, help_text="Actionable steps and status tracking (schema_version key expected)")
    billing = models.JSONField(default=default_billing, blank=True, help_text="Billing tiers & travel pricing JSON structure (schema_version, extensions)")
    process = models.JSONField(default=default_process, blank=True, help_text="Workflow steps JSON structure")
    travel = models.JSONField(default=default_travel_details, blank=True, help_text="Travel requirement JSON structure")
    default_duration_minutes = models.PositiveIntegerField(default=0, help_text="Suggested base duration in minutes")
    row_version = models.PositiveIntegerField(default=0, help_text="Optimistic concurrency version counter")
    billing_audit = models.JSONField(default=list, blank=True, help_text="Append-only log of billing tier changes")

    # Deprecated legacy fields removed (see migration & scan command for any lingering DB columns)

    def __str__(self):
        return self.description or self.category or f"Service {self.id}"

    class Meta:
        indexes = []

    # ---------------- Normalization ----------------
    def _norm_billing(self):  # pragma: no cover
        if not isinstance(self.billing, dict):
            self.billing = default_billing()
        b = self.billing
        b.setdefault("currency", "USD")
        b.setdefault("version", 1)
        b.setdefault("schema_version", 1)
        b.setdefault("travel", {"per_mile": 0.0, "per_hour": 0.0, "included_miles": 0, "dt_updated": 0})
        b.setdefault("rounding", {"strategy": "HALF_UP", "places": 2})
        b.setdefault("extensions", {})  # reserved namespace for future billing attributes
        tiers = []
        for t in b.get("tiers", []):
            if not isinstance(t, dict):
                continue
            try:
                unit = t.get("unit") or "hour"
                rate = float(t.get("rate", 0) or 0)
                cost = float(t.get("cost", 0) or 0)
                min_minutes = int(t.get("min_minutes", 0) or 0)
                dt_eff = int(t.get("dt_effective", 0) or 0)
            except Exception:
                continue
            # Quantize to 4 places for internal, 2 for display later
            rate = float(Decimal(str(rate)).quantize(Decimal("1.0000"), rounding=ROUND_HALF_UP))
            cost = float(Decimal(str(cost)).quantize(Decimal("1.0000"), rounding=ROUND_HALF_UP))
            tiers.append({
                "unit": unit,
                "rate": rate,
                "cost": cost,
                "min_minutes": min_minutes,
                "dt_effective": dt_eff,
            })
        tiers.sort(key=lambda x: x.get("dt_effective", 0))
        b["tiers"] = tiers
        return b

    def _norm_process(self):  # pragma: no cover
        if not isinstance(self.process, dict):
            self.process = default_process()
        p = self.process
        p.setdefault("version", 1)
        p.setdefault("dt_updated", 0)
        p.setdefault("schema_version", 1)
        p.setdefault("extensions", {})
        norm_steps = []
        seen = set()
        for s in p.get("steps", []):
            if not isinstance(s, dict):
                continue
            name = (s.get("name") or "").strip()
            if not name:
                continue
            try:
                minutes = int(s.get("minutes", 0) or 0)
            except Exception:
                minutes = 0
            key = name.lower()
            if key in seen:  # enforce uniqueness
                continue
            seen.add(key)
            norm_steps.append({"name": name, "minutes": minutes})
        p["steps"] = norm_steps
        return p

    def _norm_travel(self):  # pragma: no cover
        if not isinstance(self.travel, dict):
            self.travel = default_travel_details()
        tr = self.travel
        tr.setdefault("miles_included", tr.pop("miles_included", 0))
        tr.setdefault("lodging_required", False)
        tr.setdefault("meal_per_diem", 0.0)
        tr.setdefault("notes", "")
        tr.setdefault("dt_updated", 0)
        tr.setdefault("schema_version", 1)
        tr.setdefault("extensions", {})
        return tr

    def _norm_actions(self):  # pragma: no cover
        if not isinstance(self.actions, dict):
            self.actions = {}
        a = self.actions
        a.setdefault("schema_version", 1)
        a.setdefault("records", [])  # list of action dicts executed when service added to a transaction
        a.setdefault("extensions", {})
        return a

    def _validate_billing(self):  # pragma: no cover lightweight
        """Perform structural & semantic validation; accumulate errors.

        Checks:
            - currency format (3 upper letters)
            - tier chronological ordering (already sorted, but verify monotonic)
            - no overlapping dt_effective (strictly increasing permitted)
            - non-negative rates/costs/min_minutes
            - travel numeric fields non-negative
        """
        errors = {}
        b = self.billing if isinstance(self.billing, dict) else {}
        cur = b.get("currency")
        if not (isinstance(cur, str) and len(cur) == 3 and cur.isalpha()):
            errors.setdefault("billing.currency", "Invalid currency code (expected 3-letter ISO like USD)")
        tiers = b.get("tiers", []) if isinstance(b.get("tiers", []), list) else []
        dt_last = -1
        allowed_units = {"hour", "minute", "day", "flat"}
        for i, t in enumerate(tiers):
            dtv = t.get("dt_effective", 0) or 0
            if dtv < dt_last:
                errors.setdefault("billing.tiers", "Tiers not in chronological order")
                break
            if dtv == dt_last and i > 0:
                errors.setdefault("billing.tiers", "Duplicate dt_effective values not allowed")
                break
            dt_last = dtv
            if t.get("unit") not in allowed_units:
                errors.setdefault("billing.tiers", f"Unsupported unit {t.get('unit')}")
            for fld in ("rate", "cost"):
                if (t.get(fld, 0) or 0) < 0:
                    errors.setdefault("billing.tiers", f"Negative {fld} not allowed")
            if (t.get("min_minutes", 0) or 0) < 0:
                errors.setdefault("billing.tiers", "Negative min_minutes not allowed")
        travel = b.get("travel", {}) if isinstance(b.get("travel"), dict) else {}
        for fld in ("per_mile", "per_hour"):
            if float(travel.get(fld, 0) or 0) < 0:
                errors.setdefault("billing.travel", f"Negative {fld} not allowed")
        if int(travel.get("included_miles", 0) or 0) < 0:
            errors.setdefault("billing.travel", "Negative included_miles not allowed")
        if errors:
            from django.core.exceptions import ValidationError
            raise ValidationError(errors)
        return True

    def clean(self):  # pragma: no cover
        self._norm_billing()
        self._norm_process()
        self._norm_travel()
        self._norm_actions()
        # Billing validation
        self._validate_billing()
        # Concurrency: if existing row ensure row_version matches DB current
        if self.pk:
            current = Service.objects.filter(pk=self.pk).values_list("row_version", flat=True).first()
            if current is not None and current != self.row_version:
                raise ValidationError({"row_version": "Stale row_version - reload before saving"})

    # ---------------- Public API ------------------
    def add_rate(self, rate, cost=None, unit="hour", min_minutes=0, dt_effective=None):  # pragma: no cover
        self._norm_billing()
        if dt_effective is None:
            dt_effective = int(timezone.now().timestamp() * 1000)
        self.billing.setdefault("tiers", []).append({
            "unit": unit,
            "rate": float(rate),
            "cost": float(cost) if cost is not None else 0.0,
            "min_minutes": int(min_minutes),
            "dt_effective": int(dt_effective),
        })
        self._norm_billing()
        if hasattr(self, "_rate_cache"):
            self._rate_cache.pop(unit, None)
        self.log_billing_change(f"Added tier unit={unit} rate={rate} dt={dt_effective}")
        return self

    def current_rate(self, unit="hour"):
        self._norm_billing()
        if not hasattr(self, "_rate_cache"):
            self._rate_cache: Dict[str, Optional[Dict[str, Any]]] = {}
        if unit in self._rate_cache:
            return self._rate_cache[unit]
        tiers = [t for t in self.billing.get("tiers", []) if t.get("unit") == unit]
        current = tiers[-1] if tiers else None
        self._rate_cache[unit] = current
        return current

    def compute_charge(self, minutes, miles=0, unit="hour"):
        if minutes < 0 or miles < 0:
            raise ValueError("minutes and miles must be non-negative")
        tier = self.current_rate(unit)
        if not tier:
            return 0.0
        min_minutes = tier.get("min_minutes", 0) or 0
        bill_minutes = max(int(minutes), int(min_minutes))
        hours = bill_minutes / 60.0 if unit == "hour" else bill_minutes
        base = hours * float(tier.get("rate", 0))
        travel_rates = self.billing.get("travel", {}) if isinstance(self.billing, dict) else {}
        per_mile = float(travel_rates.get("per_mile", 0) or 0)
        included_miles = int(travel_rates.get("included_miles", 0) or 0)
        extra_miles = max(0, miles - included_miles)
        travel_charge = extra_miles * per_mile
        total = base + travel_charge
        rounding = self.billing.get("rounding", {}) if isinstance(self.billing, dict) else {}
        strategy = rounding.get("strategy", "HALF_UP")
        places = int(rounding.get("places", 2) or 2)
        q = Decimal(str(total))
        quant = Decimal("1." + ("0" * places))
        if strategy == "HALF_UP":
            total_rounded = float(q.quantize(quant, rounding=ROUND_HALF_UP))
        else:  # default fallback
            total_rounded = round(total, places)
        min_charge = self.billing.get("min_charge")
        max_charge = self.billing.get("max_charge")
        if min_charge is not None:
            total_rounded = max(float(min_charge), total_rounded)
        if max_charge is not None:
            total_rounded = min(float(max_charge), total_rounded)
        return total_rounded

    # ------------ Observability / Audit ----------
    def log_billing_change(self, summary: str):  # pragma: no cover lightweight
        if not isinstance(self.billing_audit, list):
            self.billing_audit = []
        self.billing_audit.append({
            "dt": int(timezone.now().timestamp() * 1000),
            "summary": summary,
            "row_version": self.row_version,
        })
        # Keep last 100 entries
        if len(self.billing_audit) > 100:
            self.billing_audit = self.billing_audit[-100:]
        return self

    # ------------ Deprecation wrappers -----------
    @property
    def deprecated_rates(self):  # pragma: no cover
        import warnings as _w
        _w.warn("rates field removed; use billing.tiers", DeprecationWarning, stacklevel=2)
        return None

    @property
    def deprecated_minutes_minimum_bill(self):  # pragma: no cover
        import warnings as _w
        _w.warn("minutes_minimum_bill removed; use billing.tiers[].min_minutes", DeprecationWarning, stacklevel=2)
        return None

    # ------------ Schema upgrade helpers --------
    def ensure_billing_schema(self, target_version: int = 1):  # pragma: no cover lightweight
        self._norm_billing()
        cur = self.billing.get("schema_version", 1)
        if cur == target_version:
            return self
        # Placeholder for future migrations; update version marker.
        self.billing["schema_version"] = target_version
        return self

    def upsert_process_step(self, name, minutes):  # pragma: no cover
        self._norm_process()
        key = name.strip().lower()
        for step in self.process.get("steps", []):
            if step.get("name", "").lower() == key:
                step["minutes"] = int(minutes)
                break
        else:
            self.process["steps"].append({"name": name.strip(), "minutes": int(minutes)})
        self.process["dt_updated"] = int(timezone.now().timestamp() * 1000)
        return self

    def save(self, *args, **kwargs):  # pragma: no cover
        self.clean()
        # increment row_version on each successful save attempt
        if self.pk:
            self.row_version += 1
        return super().save(*args, **kwargs)




# Take care of this in Actions
# CREATE TABLE IF NOT EXISTS "services" (
#     "action" VARCHAR(255),
#     "action_by" VARCHAR(255),
#     "attention" VARCHAR(255),
#     "attribute" VARCHAR(255),
#     "cause" VARCHAR(255),
#     "comment" TEXT,
#     "comment_public" TEXT,
#     "company" VARCHAR(255),
#     "cost_to_customer" INTEGER,
#     "cost_to_rep" INTEGER,
#     "cost_to_us" INTEGER,
#     "created_by" VARCHAR(255),
#     "description" VARCHAR(255),
#     "display" TEXT,
#     "duration_planned" INTEGER,
#     "expense_explain" TEXT,
#     "expenses" DOUBLE PRECISION,
#     "field_56" VARCHAR(255),
#     "is_tracked_sales" BOOLEAN DEFAULT FALSE,
#     "miles" INTEGER,
#     "price_service" DOUBLE PRECISION,
#     "price_travel" DOUBLE PRECISION,
#     "process" VARCHAR(255),
#     "publish" INTEGER,
#     "purpose" VARCHAR(255),
#     "references" JSONB,
#     "timer" INTEGER,
#     "travel_time" INTEGER
# );
