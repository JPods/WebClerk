"""
Relationship Intelligence — Alice watches all relationships and hunts for
ways to enhance their value.

Four relationship types, same discipline:
  - Customers: health, lifecycle, reorder patterns, proactive outreach triggers
  - Vendors: performance, catalog freshness, delivery reliability, price stability
  - Employees: training progress, productivity patterns, skill gaps
  - Reps: pipeline health, follow-up discipline, customer satisfaction

Alice's job: "What can I do to enhance the value of this relationship?"
Not reactive support — proactive relationship investment.

Usage:
    from apps.ai_assistant.services.relationship_intelligence import RelationshipIntelligence

    ri = RelationshipIntelligence()
    ri.scan_customers(limit=500)      # nightly customer health scan
    ri.scan_vendors(limit=200)        # weekly vendor performance scan
    ri.scan_all()                     # full relationship scan
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from django.apps import apps
from django.db.models import Avg, Count, F, Max, Min, Q, Sum
from django.utils import timezone

logger = logging.getLogger(__name__)


# ── Customer Lifecycle Stages ────────────────────────────────────────

LIFECYCLE_STAGES = {
    'new':      {'label': 'New',      'desc': 'First 90 days — make first experience excellent'},
    'growing':  {'label': 'Growing',  'desc': 'Increasing order frequency or value — expand relationship'},
    'stable':   {'label': 'Stable',   'desc': 'Consistent pattern — maintain, don\'t over-contact'},
    'at_risk':  {'label': 'At Risk',  'desc': 'Pattern breaking, health declining — intervene'},
    'dormant':  {'label': 'Dormant',  'desc': 'No activity 2x normal cycle — re-engagement needed'},
    'lost':     {'label': 'Lost',     'desc': 'No response to re-engagement — archive'},
}

# ── Outreach Triggers ────────────────────────────────────────────────

CUSTOMER_TRIGGERS = [
    {
        'id': 'reorder_overdue',
        'name': 'Reorder Overdue',
        'desc': 'Customer past their typical reorder cycle by 50%+',
        'category': 'alert',
        'priority': 1,
    },
    {
        'id': 'seasonal_reminder',
        'name': 'Seasonal Service Reminder',
        'desc': 'Annual/seasonal service window approaching based on last service date',
        'category': 'coaching',
        'priority': 0,
    },
    {
        'id': 'health_declining',
        'name': 'Health Score Declining',
        'desc': 'Customer health dropped 20+ points in last scoring cycle',
        'category': 'alert',
        'priority': 1,
    },
    {
        'id': 'new_customer_checkin',
        'name': 'New Customer Check-in',
        'desc': 'Customer in first 90 days — ensure first experience is excellent',
        'category': 'coaching',
        'priority': 0,
    },
    {
        'id': 'proposal_no_followup',
        'name': 'Proposal Without Follow-up',
        'desc': 'Inspection/proposal sent 30+ days ago with no resulting order',
        'category': 'alert',
        'priority': 1,
    },
    {
        'id': 'high_value_inactive',
        'name': 'High-Value Customer Inactive',
        'desc': 'Top-20% customer by lifetime value with no recent activity',
        'category': 'alert',
        'priority': 2,
    },
]

VENDOR_TRIGGERS = [
    {
        'id': 'delivery_slipping',
        'name': 'Delivery Performance Slipping',
        'desc': 'On-time delivery rate dropped below 90% in last 30 days',
        'category': 'alert',
        'priority': 1,
    },
    {
        'id': 'price_increase',
        'name': 'Price Increase Detected',
        'desc': 'Vendor cost increased 5%+ on items we actively sell',
        'category': 'alert',
        'priority': 1,
    },
    {
        'id': 'catalog_stale',
        'name': 'Catalog Data Stale',
        'desc': 'Vendor catalog not updated in 90+ days',
        'category': 'anomaly',
        'priority': 0,
    },
    {
        'id': 'fill_rate_low',
        'name': 'Fill Rate Below Threshold',
        'desc': 'Ordered qty vs shipped qty below 85% over last 60 days',
        'category': 'alert',
        'priority': 1,
    },
    {
        'id': 'single_source_risk',
        'name': 'Single Source Risk',
        'desc': 'Items sourced from only one vendor with no alternative',
        'category': 'anomaly',
        'priority': 1,
    },
]


class RelationshipIntelligence:
    """Alice's relationship scanner — hunts for ways to enhance value."""

    def __init__(self):
        self._now = timezone.now()

    # ── Customer Scanning ────────────────────────────────────────────

    def scan_customers(self, limit: int = 500) -> dict[str, Any]:
        """Scan customer relationships for health, lifecycle, and triggers.

        Updates metadata.health on each contact.
        Creates AliceObservation records for actionable findings.
        """
        Contact = apps.get_model('core', 'Contact')
        AliceObservation = apps.get_model('ai_assistant', 'AliceObservation')

        # Get contacts that are customers (have orders or customer role)
        customers = (
            Contact.objects
            .filter(is_active=True)
            .exclude(name='')
            .exclude(name__isnull=True)
            .order_by('-dt_modified')[:limit]
        )

        results = {
            'scanned': 0,
            'observations_created': 0,
            'lifecycle': {stage: 0 for stage in LIFECYCLE_STAGES},
            'triggers_fired': {},
        }

        for contact in customers:
            profile = self._build_customer_profile(contact)
            lifecycle = self._determine_lifecycle(profile)
            triggers = self._check_customer_triggers(contact, profile, lifecycle)

            # Update metadata.health with relationship signals
            self._update_relationship_health(contact, profile, lifecycle)

            # Create observations for triggers
            for trigger in triggers:
                dedup = f"ri:{trigger['id']}:{contact.pk}"
                existing = AliceObservation.objects.filter(
                    dedup_key=dedup, resolved=False
                ).exists()
                if not existing:
                    AliceObservation.objects.create(
                        category=trigger['category'],
                        priority=trigger['priority'],
                        message=f"{trigger['name']}: {contact.name}",
                        detail=trigger['desc'],
                        model_name='contact',
                        record_id=contact.pk,
                        contact=contact,
                        dedup_key=dedup,
                    )
                    results['observations_created'] += 1
                    results['triggers_fired'][trigger['id']] = (
                        results['triggers_fired'].get(trigger['id'], 0) + 1
                    )

            results['scanned'] += 1
            results['lifecycle'][lifecycle] = results['lifecycle'].get(lifecycle, 0) + 1

        logger.info(
            "Customer scan: %d scanned, %d observations, lifecycle=%s",
            results['scanned'], results['observations_created'], results['lifecycle'],
        )
        return results

    def _build_customer_profile(self, contact) -> dict:
        """Build a relationship profile from transaction history."""
        Order = apps.get_model('transactions', 'Order')
        Invoice = apps.get_model('transactions', 'Invoice')

        now = self._now
        profile = {
            'contact_id': contact.pk,
            'created_days_ago': 0,
            'last_order_days_ago': None,
            'order_count': 0,
            'order_count_90d': 0,
            'order_count_180d': 0,
            'total_revenue': 0,
            'avg_order_value': 0,
            'avg_order_interval_days': None,
            'has_open_issues': False,
            'small_stings_count': 0,
        }

        # Days since creation
        if hasattr(contact, 'dt_created') and contact.dt_created:
            from datetime import datetime
            if isinstance(contact.dt_created, (int, float)) and contact.dt_created > 0:
                created_dt = datetime.fromtimestamp(contact.dt_created / 1000, tz=timezone.utc)
                profile['created_days_ago'] = (now - created_dt).days

        # Order history
        try:
            orders = Order.objects.filter(
                contact=contact, is_active=True
            ).order_by('-dt_created')

            profile['order_count'] = orders.count()

            if profile['order_count'] > 0:
                latest = orders.first()
                if latest and latest.dt_created:
                    from datetime import datetime
                    if isinstance(latest.dt_created, (int, float)) and latest.dt_created > 0:
                        last_dt = datetime.fromtimestamp(latest.dt_created / 1000, tz=timezone.utc)
                        profile['last_order_days_ago'] = (now - last_dt).days

                cutoff_90 = now - timedelta(days=90)
                cutoff_180 = now - timedelta(days=180)

                # Count recent orders using dt_modified as proxy
                profile['order_count_90d'] = orders.filter(
                    dt_modified__gte=int(cutoff_90.timestamp() * 1000)
                ).count()
                profile['order_count_180d'] = orders.filter(
                    dt_modified__gte=int(cutoff_180.timestamp() * 1000)
                ).count()

                # Revenue from invoices
                agg = Invoice.objects.filter(
                    contact=contact, is_active=True
                ).aggregate(
                    total=Sum('totals__total'),
                    avg=Avg('totals__total'),
                )
                profile['total_revenue'] = float(agg['total'] or 0)
                profile['avg_order_value'] = float(agg['avg'] or 0)

                # Average interval between orders
                if profile['order_count'] >= 2:
                    dates = list(orders.values_list('dt_created', flat=True)[:20])
                    dates = [d for d in dates if d and d > 0]
                    if len(dates) >= 2:
                        intervals = []
                        for i in range(len(dates) - 1):
                            diff = abs(dates[i] - dates[i + 1]) / (1000 * 86400)  # ms to days
                            if diff > 0:
                                intervals.append(diff)
                        if intervals:
                            profile['avg_order_interval_days'] = sum(intervals) / len(intervals)
        except Exception as e:
            logger.debug("Order history lookup failed for contact %s: %s", contact.pk, e)

        # Small-Stings from metadata
        if hasattr(contact, 'metadata') and isinstance(contact.metadata, dict):
            stings = contact.metadata.get('small_stings', [])
            profile['small_stings_count'] = len(stings) if isinstance(stings, list) else 0

        return profile

    def _determine_lifecycle(self, profile: dict) -> str:
        """Determine customer lifecycle stage from profile."""
        days_ago = profile['created_days_ago']
        last_order = profile['last_order_days_ago']
        order_count = profile['order_count']
        avg_interval = profile['avg_order_interval_days']

        # New: created within 90 days
        if days_ago <= 90:
            return 'new'

        # No orders at all
        if order_count == 0:
            return 'dormant' if days_ago > 180 else 'at_risk'

        # Has orders — check recency
        if last_order is None:
            return 'stable'

        # Growing: recent orders increasing (more in last 90d than prior 90d)
        recent = profile['order_count_90d']
        prior = profile['order_count_180d'] - recent
        if recent > prior and recent > 0:
            return 'growing'

        # At risk: past their typical cycle by 50%+
        if avg_interval and last_order > avg_interval * 1.5:
            return 'at_risk'

        # Dormant: no order in 2x their cycle, or 365 days
        dormant_threshold = (avg_interval * 2) if avg_interval else 365
        if last_order > dormant_threshold:
            return 'dormant'

        # Lost: dormant and no response (dormant > 2x threshold)
        if last_order > dormant_threshold * 2:
            return 'lost'

        return 'stable'

    def _check_customer_triggers(self, contact, profile: dict, lifecycle: str) -> list[dict]:
        """Check which outreach triggers fire for this customer."""
        triggers = []

        # Reorder overdue
        avg_interval = profile.get('avg_order_interval_days')
        last_order = profile.get('last_order_days_ago')
        if avg_interval and last_order and last_order > avg_interval * 1.5:
            triggers.append(CUSTOMER_TRIGGERS[0])  # reorder_overdue

        # Health declining — check if previous score was 20+ higher
        if hasattr(contact, 'metadata') and isinstance(contact.metadata, dict):
            health = contact.metadata.get('health', {})
            prev_rating = health.get('prev_rating', 0)
            curr_rating = health.get('rating', 0)
            if prev_rating and curr_rating and (prev_rating - curr_rating) >= 20:
                triggers.append(CUSTOMER_TRIGGERS[2])  # health_declining

        # New customer check-in (30-60 days, first order placed)
        if lifecycle == 'new' and profile['order_count'] >= 1:
            if 30 <= profile['created_days_ago'] <= 60:
                triggers.append(CUSTOMER_TRIGGERS[3])  # new_customer_checkin

        # High-value inactive
        if profile['total_revenue'] > 0 and last_order and last_order > 90:
            triggers.append(CUSTOMER_TRIGGERS[5])  # high_value_inactive

        return triggers

    def _update_relationship_health(self, contact, profile: dict, lifecycle: str):
        """Update contact.metadata.health with relationship signals."""
        if not hasattr(contact, 'metadata') or not isinstance(contact.metadata, dict):
            return

        health = contact.metadata.get('health', {})
        prev_rating = health.get('rating', 0)

        # Compute relationship score (separate from data health)
        score = 0
        max_score = 100

        # Recency (30 pts)
        last_order = profile.get('last_order_days_ago')
        if last_order is not None:
            if last_order <= 30:
                score += 30
            elif last_order <= 90:
                score += 20
            elif last_order <= 180:
                score += 10
            elif last_order <= 365:
                score += 5

        # Order trend (20 pts)
        if profile['order_count_90d'] > (profile['order_count_180d'] - profile['order_count_90d']):
            score += 20  # growing
        elif profile['order_count_90d'] > 0:
            score += 10  # active

        # Engagement depth (20 pts)
        if profile['order_count'] >= 10:
            score += 20
        elif profile['order_count'] >= 5:
            score += 15
        elif profile['order_count'] >= 2:
            score += 10
        elif profile['order_count'] >= 1:
            score += 5

        # Data completeness (15 pts) — delegate to existing health scorer
        completeness = health.get('completeness', 0)
        score += min(int(completeness * 0.15), 15)

        # Issue-free (15 pts)
        if profile['small_stings_count'] == 0:
            score += 15
        elif profile['small_stings_count'] <= 2:
            score += 5

        # Update metadata
        contact.metadata['health'] = {
            **health,
            'rating': score,
            'prev_rating': prev_rating,
            'lifecycle': lifecycle,
            'last_order_days': last_order,
            'order_count': profile['order_count'],
            'avg_interval_days': profile.get('avg_order_interval_days'),
            'total_revenue': profile['total_revenue'],
            'scored_at': self._now.isoformat(),
        }

        try:
            type(contact).objects.filter(pk=contact.pk).update(metadata=contact.metadata)
        except Exception as e:
            logger.debug("Failed to update health for contact %s: %s", contact.pk, e)

    # ── Vendor Scanning ──────────────────────────────────────────────

    def scan_vendors(self, limit: int = 200) -> dict[str, Any]:
        """Scan vendor relationships for performance and catalog freshness.

        Creates AliceObservation records for actionable findings.
        """
        Contact = apps.get_model('core', 'Contact')
        AliceObservation = apps.get_model('ai_assistant', 'AliceObservation')

        # Vendors are contacts with vendor-related keywords or linked vendor records
        vendors = (
            Contact.objects
            .filter(is_active=True)
            .filter(
                Q(refs__keywords__contains=['vendor']) |
                Q(refs__keywords__contains=['supplier']) |
                Q(refs__keywords__contains=['manufacturer'])
            )
            .order_by('-dt_modified')[:limit]
        )

        results = {
            'scanned': 0,
            'observations_created': 0,
            'triggers_fired': {},
        }

        for vendor in vendors:
            triggers = self._check_vendor_triggers(vendor)

            for trigger in triggers:
                dedup = f"ri:vendor:{trigger['id']}:{vendor.pk}"
                existing = AliceObservation.objects.filter(
                    dedup_key=dedup, resolved=False
                ).exists()
                if not existing:
                    AliceObservation.objects.create(
                        category=trigger['category'],
                        priority=trigger['priority'],
                        message=f"{trigger['name']}: {vendor.name}",
                        detail=trigger['desc'],
                        model_name='contact',
                        record_id=vendor.pk,
                        contact=vendor,
                        dedup_key=dedup,
                    )
                    results['observations_created'] += 1
                    results['triggers_fired'][trigger['id']] = (
                        results['triggers_fired'].get(trigger['id'], 0) + 1
                    )

            results['scanned'] += 1

        logger.info(
            "Vendor scan: %d scanned, %d observations",
            results['scanned'], results['observations_created'],
        )
        return results

    def _check_vendor_triggers(self, vendor) -> list[dict]:
        """Check which vendor triggers fire."""
        triggers = []

        # Catalog staleness — check metadata for last catalog update
        if hasattr(vendor, 'metadata') and isinstance(vendor.metadata, dict):
            history = vendor.metadata.get('history', {})
            verified = history.get('verified', {})
            verified_dt = verified.get('dt', 0)
            if verified_dt:
                from datetime import datetime
                try:
                    last_verified = datetime.fromtimestamp(verified_dt / 1000, tz=timezone.utc)
                    days_since = (self._now - last_verified).days
                    if days_since > 90:
                        triggers.append(VENDOR_TRIGGERS[2])  # catalog_stale
                except (ValueError, OSError):
                    pass

        return triggers

    # ── Full Scan ────────────────────────────────────────────────────

    def scan_all(self, customer_limit: int = 500, vendor_limit: int = 200) -> dict[str, Any]:
        """Run all relationship scans."""
        logger.info("Starting full relationship intelligence scan")
        started = timezone.now()

        results = {
            'customers': self.scan_customers(limit=customer_limit),
            'vendors': self.scan_vendors(limit=vendor_limit),
        }

        duration = (timezone.now() - started).total_seconds()
        results['duration_seconds'] = duration
        logger.info("Relationship scan complete in %.1fs", duration)
        return results

    # ── Report ───────────────────────────────────────────────────────

    def generate_report(self, results: dict[str, Any]) -> str:
        """Generate a human-readable relationship intelligence report."""
        lines = [
            "# Relationship Intelligence Report",
            f"Generated: {timezone.now():%Y-%m-%d %H:%M}",
            "",
        ]

        # Customer section
        cust = results.get('customers', {})
        lines.extend([
            "## Customers",
            f"- Scanned: {cust.get('scanned', 0)}",
            f"- Observations created: {cust.get('observations_created', 0)}",
            "",
            "### Lifecycle Distribution",
        ])
        for stage, count in cust.get('lifecycle', {}).items():
            info = LIFECYCLE_STAGES.get(stage, {})
            lines.append(f"- **{info.get('label', stage)}**: {count} — {info.get('desc', '')}")

        lines.append("")
        if cust.get('triggers_fired'):
            lines.append("### Triggers Fired")
            for tid, count in cust['triggers_fired'].items():
                lines.append(f"- {tid}: {count}")
            lines.append("")

        # Vendor section
        vend = results.get('vendors', {})
        lines.extend([
            "## Vendors",
            f"- Scanned: {vend.get('scanned', 0)}",
            f"- Observations created: {vend.get('observations_created', 0)}",
        ])
        if vend.get('triggers_fired'):
            lines.append("")
            lines.append("### Triggers Fired")
            for tid, count in vend['triggers_fired'].items():
                lines.append(f"- {tid}: {count}")

        return "\n".join(lines)
