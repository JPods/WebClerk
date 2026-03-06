"""
LLM Inventory Observer — Learns from inventory events and provides intelligence.

Implements all 4 phases of the observational learning system:
1. Silent Observer - Logs events (handled by InventoryEvent model)
2. Summarizer - Generates human-readable summaries of events
3. Pattern Detector - Identifies trends, anomalies, and relationships
4. Interactive Assistant - Answers questions about inventory history
"""
from __future__ import annotations

import logging
from datetime import timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db.models import Avg, Count, F, Q, Sum
from django.utils import timezone

if TYPE_CHECKING:
    from apps.ai_assistant.models import InventoryEvent

logger = logging.getLogger(__name__)


class LLMInventoryObserver:
    """
    LLM-powered inventory intelligence layer.
    Uses local Ollama for inference, learns from InventoryEvent stream.
    """
    
    def __init__(self, model: str | None = None):
        """
        Initialize observer with optional custom model.
        
        Args:
            model: Override the default Ollama model
        """
        self.client = None
        self._model = model
        
    def _get_client(self):
        """Lazy load Ollama client."""
        if self.client is None:
            from apps.ai_assistant.services.ollama_client import OllamaClient
            self.client = OllamaClient()
            if self._model:
                self.client.model = self._model
        return self.client
    
    # ─────────────────────────────────────────────────────────────────
    # Phase 2: Event Summarization
    # ─────────────────────────────────────────────────────────────────
    
    def summarize_event(self, event: InventoryEvent) -> str:
        """
        Generate a concise human-readable summary of an inventory event.
        
        Args:
            event: The InventoryEvent instance to summarize
            
        Returns:
            One-sentence summary of what happened
        """
        # Build context string
        actor = event.user_name if event.user_name else "System"
        item = f"{event.item_code} ({event.item_description})" if event.item_code else f"Item #{event.item_id}"
        
        # Quantity change description
        qty_desc = ""
        if event.quantity_before is not None and event.quantity_after is not None:
            delta = event.quantity_after - event.quantity_before
            direction = "increased" if delta > 0 else "decreased"
            qty_desc = f"quantity {direction} from {event.quantity_before} to {event.quantity_after}"
        elif event.quantity_after is not None:
            qty_desc = f"quantity set to {event.quantity_after}"
        
        # Transaction context
        tx_desc = ""
        if event.transaction_ida:
            tx_desc = f" on {event.transaction_type.upper()} {event.transaction_ida}"
        
        # Customer/vendor
        party = ""
        if event.customer_name:
            party = f" for customer {event.customer_name}"
        elif event.vendor_name:
            party = f" from vendor {event.vendor_name}"
        
        # Build natural language prompt
        prompt = f"""Summarize this inventory event in ONE short sentence (under 100 chars):

Event: {event.event_type.replace('_', ' ')}
Actor: {actor}
Item: {item}
{f'Change: {qty_desc}' if qty_desc else ''}
{f'Transaction: {event.transaction_type} {event.transaction_ida}' if event.transaction_ida else ''}
{f'Party: {event.customer_name or event.vendor_name}' if event.customer_name or event.vendor_name else ''}
{f'Reason: {event.reason}' if event.reason else ''}

Return ONLY the summary sentence, no explanation."""

        try:
            client = self._get_client()
            summary = client.generate(prompt).strip()
            # Clean up any quotes or extra formatting
            summary = summary.strip('"\'')
            return summary[:200]  # Safety limit
        except Exception as e:
            logger.debug(f"LLM summarization failed: {e}")
            # Fallback to template-based summary
            return self._template_summary(event)
    
    def _template_summary(self, event: InventoryEvent) -> str:
        """Fallback template-based summary when LLM is unavailable."""
        actor = event.user_name or "System"
        item = event.item_code or f"Item #{event.item_id}"
        action = event.event_type.replace('_', ' ')
        
        parts = [f"{actor} {action}"]
        if event.item_code:
            parts.append(f"{item}")
        if event.quantity_delta is not None:
            parts.append(f"({event.quantity_delta:+})")
        if event.transaction_ida:
            parts.append(f"on {event.transaction_ida}")
        
        return " ".join(parts)
    
    # ─────────────────────────────────────────────────────────────────
    # Phase 2: Item Narrative
    # ─────────────────────────────────────────────────────────────────
    
    def get_item_narrative(self, item_id: int, days: int = 30) -> str:
        """
        Generate a narrative summary of an item's recent inventory history.
        
        Args:
            item_id: The item's ID
            days: Number of days to look back
            
        Returns:
            Multi-paragraph narrative of the item's inventory story
        """
        from apps.ai_assistant.models import InventoryEvent
        
        since = timezone.now() - timedelta(days=days)
        events = list(
            InventoryEvent.objects.filter(
                item_id=item_id,
                created_at__gte=since
            ).order_by('created_at')[:100]
        )
        
        if not events:
            return f"No inventory events found for item {item_id} in the last {days} days."
        
        # Build event timeline
        timeline = []
        for e in events:
            summary = e.llm_summary or self._template_summary(e)
            timeline.append(f"- {e.created_at.strftime('%Y-%m-%d %H:%M')}: {summary}")
        
        # Get aggregate stats
        stats = InventoryEvent.objects.filter(
            item_id=item_id,
            created_at__gte=since
        ).aggregate(
            total_events=Count('id'),
            total_delta=Sum('quantity_delta'),
            unique_customers=Count('customer_id', distinct=True),
        )
        
        item_code = events[0].item_code if events else f"Item #{item_id}"
        
        prompt = f"""Write a brief narrative (2-3 paragraphs) about this item's recent inventory activity:

Item: {item_code}
Period: Last {days} days
Total Events: {stats['total_events']}
Net Quantity Change: {stats['total_delta'] or 0}
Unique Customers: {stats['unique_customers']}

Recent Events:
{chr(10).join(timeline[:20])}

Focus on:
1. Overall trend (building up inventory, depleting, steady?)
2. Notable patterns (regular customers, unusual activity?)
3. Current status and any concerns

Keep it conversational and insightful."""

        try:
            client = self._get_client()
            return client.generate(prompt)
        except Exception as e:
            logger.warning(f"LLM narrative generation failed: {e}")
            return f"Item {item_code}: {stats['total_events']} events, net change {stats['total_delta'] or 0}"
    
    # ─────────────────────────────────────────────────────────────────
    # Phase 3: Pattern Detection
    # ─────────────────────────────────────────────────────────────────
    
    def detect_patterns(self, days: int = 7) -> dict:
        """
        Analyze recent events to detect patterns and anomalies.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with detected patterns, anomalies, and recommendations
        """
        from apps.ai_assistant.models import InventoryEvent
        
        since = timezone.now() - timedelta(days=days)
        events = InventoryEvent.objects.filter(created_at__gte=since)
        
        # High-activity items
        active_items = (
            events
            .values('item_id', 'item_code')
            .annotate(
                event_count=Count('id'),
                total_movement=Sum('quantity_delta'),
            )
            .order_by('-event_count')[:10]
        )
        
        # Frequent customers
        top_customers = (
            events
            .exclude(customer_id__isnull=True)
            .values('customer_id', 'customer_name')
            .annotate(order_count=Count('id'))
            .order_by('-order_count')[:5]
        )
        
        # Alert summary
        alerts = (
            events
            .filter(category='alert')
            .values('event_type')
            .annotate(count=Count('id'))
        )
        
        # Events by category
        by_category = (
            events
            .values('category')
            .annotate(count=Count('id'))
        )
        
        patterns = {
            'period_days': days,
            'total_events': events.count(),
            'active_items': list(active_items),
            'top_customers': list(top_customers),
            'alerts': {a['event_type']: a['count'] for a in alerts},
            'by_category': {c['category']: c['count'] for c in by_category},
        }
        
        # Generate LLM insights
        patterns['insights'] = self._generate_insights(patterns)
        
        return patterns
    
    def _generate_insights(self, patterns: dict) -> str:
        """Generate LLM-powered insights from pattern data."""
        if patterns['total_events'] == 0:
            return "No events to analyze in this period."
        
        prompt = f"""Analyze this inventory activity and provide 3-5 actionable insights:

Period: {patterns['period_days']} days
Total Events: {patterns['total_events']}

Events by Category:
{chr(10).join(f'- {k}: {v}' for k, v in patterns['by_category'].items())}

Most Active Items:
{chr(10).join(f"- {i['item_code'] or 'Item #' + str(i['item_id'])}: {i['event_count']} events, {i['total_movement'] or 0:+} net" for i in patterns['active_items'][:5])}

Alerts Triggered:
{chr(10).join(f'- {k}: {v}' for k, v in patterns['alerts'].items()) or 'None'}

Provide brief, actionable insights. Focus on:
- Inventory health observations
- Items needing attention
- Ordering recommendations
- Potential issues to watch"""

        try:
            client = self._get_client()
            return client.generate(prompt)
        except Exception as e:
            logger.warning(f"LLM insights generation failed: {e}")
            return "Unable to generate insights - LLM unavailable"
    
    # ─────────────────────────────────────────────────────────────────
    # Phase 4: Interactive Q&A
    # ─────────────────────────────────────────────────────────────────
    
    def answer_question(self, question: str, context_days: int = 30) -> str:
        """
        Answer a natural language question about inventory.
        
        Args:
            question: User's question about inventory
            context_days: How many days of history to consider
            
        Returns:
            LLM-generated answer based on inventory event data
        """
        from apps.ai_assistant.models import InventoryEvent
        
        since = timezone.now() - timedelta(days=context_days)
        
        # Gather relevant context based on question keywords
        context_parts = []
        
        # Recent summary stats
        stats = InventoryEvent.objects.filter(created_at__gte=since).aggregate(
            total=Count('id'),
            transactions=Count('id', filter=Q(category='transaction')),
            adjustments=Count('id', filter=Q(category='adjustment')),
            alerts=Count('id', filter=Q(category='alert')),
        )
        context_parts.append(f"System Stats (last {context_days} days):")
        context_parts.append(f"- Total events: {stats['total']}")
        context_parts.append(f"- Transaction events: {stats['transactions']}")
        context_parts.append(f"- Adjustments: {stats['adjustments']}")
        context_parts.append(f"- Alerts: {stats['alerts']}")
        
        # Check for item-specific questions
        # Simple keyword extraction - could be enhanced
        question_lower = question.lower()
        
        if 'alert' in question_lower or 'reorder' in question_lower:
            alerts = list(
                InventoryEvent.objects.filter(
                    category='alert',
                    created_at__gte=since
                ).order_by('-created_at')[:10]
            )
            if alerts:
                context_parts.append("\nRecent Alerts:")
                for a in alerts:
                    context_parts.append(f"- {a.created_at.strftime('%m/%d')}: {a.event_type} - {a.item_code or a.item_id}")
        
        # Recent notable events
        recent = list(
            InventoryEvent.objects.filter(created_at__gte=since)
            .exclude(category='alert')
            .order_by('-created_at')[:20]
        )
        if recent:
            context_parts.append("\nRecent Events:")
            for e in recent[:10]:
                summary = e.llm_summary or self._template_summary(e)
                context_parts.append(f"- {e.created_at.strftime('%m/%d %H:%M')}: {summary}")
        
        context = "\n".join(context_parts)
        
        prompt = f"""You are an inventory management assistant. Answer this question based on the provided context.

Question: {question}

Context:
{context}

Provide a helpful, accurate answer. If you can't answer from the available data, say so and suggest what information would help."""

        try:
            client = self._get_client()
            return client.generate(prompt)
        except Exception as e:
            logger.error(f"LLM Q&A failed: {e}")
            return f"I apologize, but I'm unable to answer right now. Please try again later."
    
    # ─────────────────────────────────────────────────────────────────
    # Utility Methods
    # ─────────────────────────────────────────────────────────────────
    
    def get_daily_digest(self) -> str:
        """
        Generate a daily digest of inventory activity.
        Suitable for automated reporting or notifications.
        """
        from apps.ai_assistant.models import InventoryEvent
        
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        
        events = InventoryEvent.objects.filter(
            created_at__date=yesterday
        )
        
        stats = events.aggregate(
            total=Count('id'),
            items_touched=Count('item_id', distinct=True),
            sales=Count('id', filter=Q(event_type__startswith='order_') | Q(event_type__startswith='invoice_')),
            purchases=Count('id', filter=Q(event_type__startswith='purchase_')),
            adjustments=Count('id', filter=Q(category='adjustment')),
            alerts=Count('id', filter=Q(category='alert')),
        )
        
        if stats['total'] == 0:
            return f"No inventory activity recorded for {yesterday}."
        
        # Get alert details
        alerts = list(
            events.filter(category='alert')
            .values('event_type', 'item_code')[:10]
        )
        
        prompt = f"""Write a brief daily inventory digest report for {yesterday}:

Activity Summary:
- Total events: {stats['total']}
- Items affected: {stats['items_touched']}
- Sales activity: {stats['sales']} events
- Purchase activity: {stats['purchases']} events
- Adjustments: {stats['adjustments']}
- Alerts triggered: {stats['alerts']}

{f"Alerts: {', '.join(f'{a['event_type']} on {a['item_code']}' for a in alerts)}" if alerts else 'No alerts'}

Write 2-3 paragraphs summarizing the day's activity and any items needing attention."""

        try:
            client = self._get_client()
            return client.generate(prompt)
        except Exception as e:
            logger.warning(f"Daily digest generation failed: {e}")
            return f"Daily Digest for {yesterday}: {stats['total']} events, {stats['items_touched']} items, {stats['alerts']} alerts."
