from __future__ import annotations

from django.db import models
from django.utils import timezone
from typing import Any


def default_stats() -> dict:
        """Default stats structure.

        counts: integer counters (page_views, tx_sale_count, tx_return_count, service_calls,...)
        values: scalar values (avg_margin_pct, last_sale_value, last_return_value, tx_sale_total_value,...)
        series: small capped lists of {dt,v} samples (weekly_sales, margin_trend, ...)
        last: per-event last timestamps (ms) e.g. dt_last_sale, dt_last_purchase, dt_last_service_call

        Reserved / suggested keys (optional usage):
            counts:
                tx_total, tx_sale_count, tx_purchase_count, tx_return_count, tx_adjust_count,
                service_calls
            values:
                tx_sale_total_value, tx_purchase_total_value, tx_return_total_value,
                avg_margin_pct, last_margin_pct, last_sale_value, last_purchase_value
            last:
                dt_last_sale, dt_last_purchase, dt_last_return, dt_last_service_call
        """
        return {"counts": {}, "values": {}, "series": {}, "last": {}}


class StatsMixin(models.Model):
    """Lightweight per-record statistics container.

    Non-authoritative, low-cardinality metrics suited for UI surfacing and
    quick filters. Heavy analytical data should live in a warehouse.
    """

    feature_flags = {"stats"}
    stats = models.JSONField(default=default_stats, blank=True)

    class Meta:
        abstract = True

    # ---- Counter helpers -------------------------------------------------
    def inc_stat(self, key: str, delta: int = 1) -> int:
        counts = self.stats.setdefault("counts", {})
        counts[key] = int(counts.get(key, 0)) + delta
        return counts[key]

    def set_value(self, key: str, value: Any):
        self.stats.setdefault("values", {})[key] = value
        return value

    def push_series(self, key: str, value: Any, max_len: int = 50):
        series = self.stats.setdefault("series", {}).setdefault(key, [])
        series.append({"dt": int(timezone.now().timestamp() * 1000), "v": value})
        if max_len and len(series) > max_len:
            del series[0 : len(series) - max_len]
        return series

    # Convenience accessors
    def get_count(self, key: str, default: int = 0) -> int:
        return int(self.stats.get("counts", {}).get(key, default)) if isinstance(self.stats, dict) else default

    def get_value(self, key: str, default=None):
        return self.stats.get("values", {}).get(key, default) if isinstance(self.stats, dict) else default

    # ---- Domain helpers (transactions & service events) -----------------
    def record_transaction(self, tx_type: str, value: float | int | None = None, margin_value: float | None = None):
        """Record a transaction occurrence updating counts, totals, last timestamps, and margin aggregates.

        tx_type examples: 'sale', 'purchase', 'return', 'adjust'.
        value: monetary value (positive; returns may be negative or handled separately).
        margin_value: margin percent (0-1 or 0-100 depending on caller; stored as 0-1 if >1 convert down).
        """
        now_ms = int(timezone.now().timestamp() * 1000)
        counts = self.stats.setdefault("counts", {})
        values = self.stats.setdefault("values", {})
        last = self.stats.setdefault("last", {})
        # Generic totals
        counts["tx_total"] = int(counts.get("tx_total", 0)) + 1
        key_count = f"tx_{tx_type}_count"
        counts[key_count] = int(counts.get(key_count, 0)) + 1
        if value is not None:
            total_key = f"tx_{tx_type}_total_value"
            values[total_key] = float(values.get(total_key, 0.0)) + float(value)
            if tx_type == "sale":
                values["last_sale_value"] = float(value)
            elif tx_type == "purchase":
                values["last_purchase_value"] = float(value)
            elif tx_type == "return":
                values["last_return_value"] = float(value)
        last[f"dt_last_{tx_type}"] = now_ms
        # Margin tracking (average of sale margins)
        if margin_value is not None:
            mv = float(margin_value)
            if mv > 1.0:  # assume percent passed like 23.5 -> convert
                mv = mv / 100.0
            # Maintain running average margin_pct for sales only
            if tx_type == "sale":
                sale_count = counts.get("tx_sale_count", 1)
                prev_avg = float(values.get("avg_margin_pct", mv))
                # incremental average: new_avg = prev_avg + (mv - prev_avg)/sale_count
                new_avg = prev_avg + (mv - prev_avg) / float(sale_count)
                values["avg_margin_pct"] = new_avg
                values["last_margin_pct"] = mv
        return counts.get(key_count)

    def record_service_call(self):
        now_ms = int(timezone.now().timestamp() * 1000)
        counts = self.stats.setdefault("counts", {})
        last = self.stats.setdefault("last", {})
        counts["service_calls"] = int(counts.get("service_calls", 0)) + 1
        last["dt_last_service_call"] = now_ms
        return counts["service_calls"]
