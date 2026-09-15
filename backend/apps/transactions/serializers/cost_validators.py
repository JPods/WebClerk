from __future__ import annotations
from typing import Any, Dict
from rest_framework import serializers

COST_NUMERIC_FIELDS = [
    'unit_po', 'fifo_snapshot', 'lifo_snapshot', 'moving_avg', 'landed',
    'freight', 'duty', 'handling', 'vat', 'scrap_cost', 'trend_pct', 'exchange_rate'
]

REQUIRED_MINIMAL = ['unit_po', 'moving_avg', 'landed']

class CostPayloadValidator:
    """Lightweight validation helper for inventory/purchase layer cost JSON.

    All numeric fields coerced to float if possible. Missing optional fields default to 0.0.
    Ensures no negative monetary values (except trend_pct which can be negative).
    """
    @classmethod
    def normalize(cls, raw: Dict[str, Any] | None) -> Dict[str, Any]:
        if raw is None or not isinstance(raw, dict):
            raw = {}
        out: Dict[str, Any] = {}
        # Copy known fields with coercion
        for k in COST_NUMERIC_FIELDS:
            v = raw.get(k, 0)
            if v in (None, ''):
                v = 0
            try:
                v = float(v)
            except Exception:
                raise serializers.ValidationError({k: ['Must be numeric']})
            if k != 'trend_pct' and v < 0:
                raise serializers.ValidationError({k: ['Must be >= 0']})
            out[k] = v
        currency = raw.get('currency', 'USD')
        if not isinstance(currency, str) or len(currency) not in (3,):
            raise serializers.ValidationError({'currency': ['Currency must be 3-letter code']})
        out['currency'] = currency.upper()
        # Basic relationship sanity: landed should be >= unit_po
        if out['landed'] and out['unit_po'] and out['landed'] < out['unit_po']:
            # soft correction; could also raise
            out['landed'] = out['unit_po']
        return out

class CostJSONField(serializers.JSONField):
    def to_internal_value(self, data: Any) -> Dict[str, Any]:
        data = super().to_internal_value(data)
        return CostPayloadValidator.normalize(data)

    def to_representation(self, value: Any) -> Any:
        if isinstance(value, dict):
            return value
        return {}
