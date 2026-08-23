"""
5F. Margin & Profitability Tracking.
5G. Inventory Velocity & Investment Efficiency.

Deterministic margin math with Ollama for anomaly detection, trend forecasting,
and narrative summaries. Inventory velocity measures margin earned per unit
of time capital is tied up.

Usage:
    from apps.ai_assistant.services.margin_tracker import MarginTracker

    tracker = MarginTracker()
    report = tracker.compute_item_margins(limit=500)
    velocity = tracker.compute_velocity(limit=500)
    print(tracker.format_report(report, velocity))
"""
from __future__ import annotations

import logging
from collections import defaultdict
from decimal import Decimal
from typing import Any

from django.apps import apps
from django.db.models import Avg, Count, F, Q, Sum
from django.utils import timezone

logger = logging.getLogger(__name__)


class MarginTracker:
    """Compute and track margins, profitability, and inventory velocity."""

    def __init__(self, use_llm: bool = False):
        self.use_llm = use_llm
        self._client = None

    def _get_client(self):
        if self._client is None and self.use_llm:
            from apps.ai_assistant.services.ollama_client import OllamaClient
            self._client = OllamaClient()
        return self._client

    # ── Item-level margin computation ──────────────────────────────────

    def compute_item_margins(self, limit: int = 500) -> dict[str, Any]:
        """Compute margin for each item from price/cost JSON fields.

        Margin = (base_price - average_cost) / base_price * 100

        Returns per-item margin data and aggregate statistics.
        """
        from apps.products.models.item import Item

        items_data = []
        anomalies = []
        total_margin_sum = Decimal(0)
        total_counted = 0

        qs = Item.objects.filter(is_active=True).order_by("pk")[:limit]
        for item in qs.iterator(chunk_size=200):
            price_data = item.price if isinstance(item.price, dict) else {}
            cost_data = item.cost if isinstance(item.cost, dict) else {}

            base_price = Decimal(str(price_data.get("base", 0) or 0))
            avg_cost = Decimal(str(cost_data.get("average", 0) or cost_data.get("last", 0) or 0))

            if base_price <= 0:
                continue

            margin_amount = base_price - avg_cost
            margin_pct = (margin_amount / base_price * 100).quantize(Decimal("0.01"))

            item_info = {
                "pk": item.pk,
                "name": item.name,
                "sku": item.sku or "",
                "base_price": float(base_price),
                "avg_cost": float(avg_cost),
                "margin_amount": float(margin_amount),
                "margin_pct": float(margin_pct),
            }
            items_data.append(item_info)
            total_margin_sum += margin_pct
            total_counted += 1

            # Anomaly detection (deterministic thresholds)
            if margin_pct < 0:
                anomalies.append({**item_info, "anomaly": "negative_margin"})
            elif margin_pct < 5:
                anomalies.append({**item_info, "anomaly": "very_low_margin"})
            elif margin_pct > 90:
                anomalies.append({**item_info, "anomaly": "unusually_high_margin"})

        avg_margin = float(total_margin_sum / total_counted) if total_counted else 0

        # Distribution
        distribution = {"negative": 0, "0-10": 0, "10-25": 0, "25-50": 0, "50-75": 0, "75+": 0}
        for item in items_data:
            m = item["margin_pct"]
            if m < 0:
                distribution["negative"] += 1
            elif m < 10:
                distribution["0-10"] += 1
            elif m < 25:
                distribution["10-25"] += 1
            elif m < 50:
                distribution["25-50"] += 1
            elif m < 75:
                distribution["50-75"] += 1
            else:
                distribution["75+"] += 1

        return {
            "items_analyzed": total_counted,
            "avg_margin_pct": round(avg_margin, 2),
            "distribution": distribution,
            "anomalies": anomalies,
            "top_margin": sorted(items_data, key=lambda x: x["margin_pct"], reverse=True)[:10],
            "bottom_margin": sorted(items_data, key=lambda x: x["margin_pct"])[:10],
        }

    # ── Usage-based margin tracking (ItemUsage monthly) ────────────────

    def compute_usage_margins(self, year: int | None = None, month: int | None = None) -> dict[str, Any]:
        """Aggregate margins from ItemUsage monthly snapshots."""
        from apps.products.models.usage import ItemUsage

        now = timezone.now()
        year = year or now.year
        month = month or now.month

        qs = ItemUsage.objects.filter(year=year, month=month)

        results = []
        for usage in qs.iterator(chunk_size=200):
            metrics = usage.metrics if isinstance(usage.metrics, dict) else {}
            sales_actual = float(metrics.get("sales.actual", 0) or 0)
            cost_actual = float(metrics.get("cost.actual", 0) or 0)
            margin_factor = float(metrics.get("margin.factor", 0) or 0)

            if sales_actual > 0:
                computed_margin = ((sales_actual - cost_actual) / sales_actual * 100)
            else:
                computed_margin = 0

            results.append({
                "item_id": usage.item_id,
                "year": year,
                "month": month,
                "sales": sales_actual,
                "cost": cost_actual,
                "margin_pct": round(computed_margin, 2),
                "stored_margin_factor": margin_factor,
                "turns": float(metrics.get("turns.actual", 0) or 0),
            })

        return {
            "period": f"{year}-{month:02d}",
            "records": len(results),
            "data": results,
        }

    # ── 5G: Inventory Velocity ─────────────────────────────────────────

    def compute_velocity(self, limit: int = 500) -> dict[str, Any]:
        """Compute inventory velocity: margin per day of inventory investment.

        velocity = margin_per_unit / avg_days_on_hand
        Where avg_days_on_hand = (avg_inventory_value / annual_cogs) * 365

        Items with higher velocity are better investments.
        """
        from apps.products.models.item import Item

        velocity_data = []
        slow_movers = []
        dead_stock = []

        qs = Item.objects.filter(is_active=True).order_by("pk")[:limit]
        for item in qs.iterator(chunk_size=200):
            price_data = item.price if isinstance(item.price, dict) else {}
            cost_data = item.cost if isinstance(item.cost, dict) else {}
            qty_data = item.quantity if isinstance(item.quantity, dict) else {}

            base_price = float(price_data.get("base", 0) or 0)
            avg_cost = float(cost_data.get("average", 0) or cost_data.get("last", 0) or 0)
            on_hand = float(qty_data.get("on_hand", 0) or 0)
            on_so = float(qty_data.get("on_so", 0) or 0)
            on_po = float(qty_data.get("on_po", 0) or 0)

            if avg_cost <= 0 or base_price <= 0:
                continue

            # Margin per unit
            margin_per_unit = base_price - avg_cost

            # Inventory investment (cost of on-hand)
            inventory_investment = on_hand * avg_cost

            # Estimate turns from ItemUsage if available
            turns = self._get_recent_turns(item.pk)

            # Days of supply = on_hand / daily_demand
            # If we have turns, days = 365 / turns
            if turns and turns > 0:
                days_of_supply = round(365.0 / turns, 1)
            elif on_so > 0:
                # Rough estimate: committed qty as proxy for demand
                days_of_supply = round(on_hand / max(on_so / 30, 0.01), 1) if on_hand > 0 else 0
            else:
                days_of_supply = 999  # Unknown — assume slow

            # Velocity: margin earned per dollar per day
            if inventory_investment > 0 and days_of_supply > 0:
                # Margin velocity: how much margin we earn per day per dollar invested
                velocity = round(margin_per_unit / (avg_cost * max(days_of_supply, 1)) * 100, 4)
            else:
                velocity = 0

            item_velocity = {
                "pk": item.pk,
                "name": item.name,
                "sku": item.sku or "",
                "on_hand": on_hand,
                "avg_cost": avg_cost,
                "base_price": base_price,
                "margin_per_unit": round(margin_per_unit, 2),
                "inventory_investment": round(inventory_investment, 2),
                "turns": turns or 0,
                "days_of_supply": days_of_supply,
                "velocity": velocity,  # %/day — higher is better
            }
            velocity_data.append(item_velocity)

            # Classify
            if on_hand > 0 and days_of_supply > 365:
                dead_stock.append(item_velocity)
            elif on_hand > 0 and days_of_supply > 90:
                slow_movers.append(item_velocity)

        # Sort by velocity (highest first = best investment)
        velocity_data.sort(key=lambda x: x["velocity"], reverse=True)

        total_investment = sum(v["inventory_investment"] for v in velocity_data)
        dead_investment = sum(v["inventory_investment"] for v in dead_stock)
        slow_investment = sum(v["inventory_investment"] for v in slow_movers)

        return {
            "items_analyzed": len(velocity_data),
            "total_inventory_investment": round(total_investment, 2),
            "dead_stock_count": len(dead_stock),
            "dead_stock_investment": round(dead_investment, 2),
            "slow_mover_count": len(slow_movers),
            "slow_mover_investment": round(slow_investment, 2),
            "top_velocity": velocity_data[:10],
            "bottom_velocity": velocity_data[-10:] if len(velocity_data) > 10 else velocity_data,
            "dead_stock": dead_stock[:20],
            "slow_movers": slow_movers[:20],
        }

    def _get_recent_turns(self, item_id: int) -> float | None:
        """Get the most recent turns.actual from ItemUsage."""
        try:
            from apps.products.models.usage import ItemUsage
            now = timezone.now()
            usage = (ItemUsage.objects
                     .filter(item_id=item_id)
                     .order_by("-year", "-month")
                     .values_list("metrics", flat=True)
                     .first())
            if usage and isinstance(usage, dict):
                return float(usage.get("turns.actual", 0) or 0)
        except Exception:
            pass
        return None

    # ── Update ItemUsage with velocity metrics ─────────────────────────

    def update_usage_velocity(self, limit: int = 500) -> dict[str, Any]:
        """Write velocity metrics back into ItemUsage records."""
        from apps.products.models.item import Item
        from apps.products.models.usage import ItemUsage

        now = timezone.now()
        updated = 0

        velocity_report = self.compute_velocity(limit=limit)
        for v in velocity_report.get("top_velocity", []) + velocity_report.get("bottom_velocity", []):
            # Find or create current month ItemUsage
            usage, created = ItemUsage.objects.get_or_create(
                item_id=v["pk"],
                year=now.year,
                month=now.month,
                defaults={"metrics": {}}
            )
            metrics = usage.metrics if isinstance(usage.metrics, dict) else {}
            metrics["velocity.margin_per_day"] = v["velocity"]
            metrics["velocity.carrying_days"] = v["days_of_supply"]
            metrics["velocity.rank"] = 0  # Will be set after sorting
            metrics["velocity.investment"] = v["inventory_investment"]
            metrics["velocity.dt_computed"] = int(now.timestamp() * 1000)

            ItemUsage.objects.filter(pk=usage.pk).update(metrics=metrics)
            updated += 1

        return {"updated": updated}

    # ── LLM-enhanced analysis ─────────────────────────────────────────

    def llm_margin_analysis(self, margin_report: dict[str, Any]) -> str:
        """Use Ollama to generate narrative margin analysis."""
        client = self._get_client()
        if not client:
            return "LLM not available"

        try:
            anomalies = margin_report.get("anomalies", [])
            top = margin_report.get("top_margin", [])[:5]
            bottom = margin_report.get("bottom_margin", [])[:5]
            dist = margin_report.get("distribution", {})

            prompt = (
                f"Analyze these margin statistics for a product catalog:\n\n"
                f"Average margin: {margin_report.get('avg_margin_pct', 0)}%\n"
                f"Distribution: {dist}\n"
                f"Anomalies ({len(anomalies)} items): "
                + ", ".join(f"{a['name']} ({a['anomaly']}, {a['margin_pct']}%)" for a in anomalies[:10])
                + f"\nTop margin items: "
                + ", ".join(f"{t['name']} ({t['margin_pct']}%)" for t in top)
                + f"\nLowest margin items: "
                + ", ".join(f"{b['name']} ({b['margin_pct']}%)" for b in bottom)
                + "\n\nProvide a brief analysis with actionable recommendations."
            )
            return client.generate(prompt, mode="general")
        except Exception as e:
            return f"LLM analysis failed: {e}"

    def llm_velocity_analysis(self, velocity_report: dict[str, Any]) -> str:
        """Use Ollama to generate investment efficiency recommendations."""
        client = self._get_client()
        if not client:
            return "LLM not available"

        try:
            prompt = (
                f"Analyze this inventory velocity report:\n\n"
                f"Total inventory investment: ${velocity_report.get('total_inventory_investment', 0):,.2f}\n"
                f"Dead stock: {velocity_report.get('dead_stock_count', 0)} items, "
                f"${velocity_report.get('dead_stock_investment', 0):,.2f} invested\n"
                f"Slow movers: {velocity_report.get('slow_mover_count', 0)} items, "
                f"${velocity_report.get('slow_mover_investment', 0):,.2f} invested\n\n"
                f"Top velocity items (best investments):\n"
                + "\n".join(
                    f"  - {v['name']}: velocity={v['velocity']}%/day, "
                    f"investment=${v['inventory_investment']:,.2f}, "
                    f"days_supply={v['days_of_supply']}"
                    for v in velocity_report.get("top_velocity", [])[:5]
                )
                + f"\n\nDead stock (over 365 days supply):\n"
                + "\n".join(
                    f"  - {d['name']}: on_hand={d['on_hand']}, "
                    f"investment=${d['inventory_investment']:,.2f}"
                    for d in velocity_report.get("dead_stock", [])[:5]
                )
                + "\n\nProvide a brief analysis with specific recommendations to improve capital efficiency."
            )
            return client.generate(prompt, mode="general")
        except Exception as e:
            return f"LLM analysis failed: {e}"

    # ── Report formatting ─────────────────────────────────────────────

    def format_report(self, margin_report: dict[str, Any], velocity_report: dict[str, Any] | None = None) -> str:
        """Format combined margin + velocity report as markdown."""
        lines = [
            "# Margin & Inventory Intelligence Report",
            f"Generated: {timezone.now():%Y-%m-%d %H:%M}",
            "",
            "## Margin Analysis",
            f"- Items analyzed: {margin_report.get('items_analyzed', 0)}",
            f"- Average margin: **{margin_report.get('avg_margin_pct', 0)}%**",
            f"- Anomalies: {len(margin_report.get('anomalies', []))}",
            "",
            "### Distribution",
        ]

        dist = margin_report.get("distribution", {})
        for label, count in dist.items():
            lines.append(f"- {label}%: {count} items")

        lines.append("")

        # Anomalies
        anomalies = margin_report.get("anomalies", [])
        if anomalies:
            lines.append("### Anomalies")
            for a in anomalies[:15]:
                lines.append(f"- ⚠️ **{a['name']}** ({a['sku']}): {a['margin_pct']}% — {a['anomaly']}")
            lines.append("")

        # Top/bottom
        lines.append("### Top 10 Margin")
        for t in margin_report.get("top_margin", []):
            lines.append(f"- {t['name']} ({t['sku']}): {t['margin_pct']}%")

        lines.extend(["", "### Bottom 10 Margin"])
        for b in margin_report.get("bottom_margin", []):
            lines.append(f"- {b['name']} ({b['sku']}): {b['margin_pct']}%")

        # Velocity section
        if velocity_report:
            lines.extend([
                "",
                "---",
                "",
                "## Inventory Velocity (Investment Efficiency)",
                f"- Items analyzed: {velocity_report.get('items_analyzed', 0)}",
                f"- Total inventory investment: **${velocity_report.get('total_inventory_investment', 0):,.2f}**",
                f"- Dead stock ({velocity_report.get('dead_stock_count', 0)} items): "
                f"${velocity_report.get('dead_stock_investment', 0):,.2f}",
                f"- Slow movers ({velocity_report.get('slow_mover_count', 0)} items): "
                f"${velocity_report.get('slow_mover_investment', 0):,.2f}",
                "",
                "### Best Investments (Highest Velocity)",
            ])
            for v in velocity_report.get("top_velocity", [])[:10]:
                lines.append(
                    f"- **{v['name']}** ({v['sku']}): velocity={v['velocity']}%/day, "
                    f"{v['days_of_supply']} days supply, ${v['inventory_investment']:,.2f} invested"
                )

            lines.extend(["", "### Dead Stock (> 365 days supply)"])
            for d in velocity_report.get("dead_stock", [])[:10]:
                lines.append(
                    f"- ⛔ **{d['name']}** ({d['sku']}): {d['on_hand']} on hand, "
                    f"${d['inventory_investment']:,.2f} invested, {d['days_of_supply']} days supply"
                )

            lines.extend(["", "### Slow Movers (90-365 days supply)"])
            for s in velocity_report.get("slow_movers", [])[:10]:
                lines.append(
                    f"- 🐌 **{s['name']}** ({s['sku']}): {s['on_hand']} on hand, "
                    f"${s['inventory_investment']:,.2f} invested, {s['days_of_supply']} days supply"
                )

        lines.append("")
        return "\n".join(lines)
