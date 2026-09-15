# LLM Inventory Observer — Architecture & Implementation

> **Version**: 1.1  
> **Created**: 2026-03-06  
> **Updated**: 2026-03-06  
> **Status**: ✅ Implemented  
> **Scope**: Observational learning for inventory management

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Implementation Files](#implementation-files)
3. [Patent Alignment](#patent-alignment)
4. [Overview](#overview)
5. [Event Logging Schema](#event-logging-schema)
6. [Observer Service Architecture](#observer-service-architecture)
7. [Staging Phases](#staging-phases)
8. [Integration Points](#integration-points)
9. [Example Scenarios](#example-scenarios)
10. [Configuration](#configuration)

---

## Quick Start

### Basic Usage

```python
from apps.ai_assistant.services.llm_observer import LLMInventoryObserver

observer = LLMInventoryObserver()

# Get narrative summary for an item
narrative = observer.get_item_narrative(item_id=123, days=30)
print(narrative)

# Detect patterns in recent activity
patterns = observer.detect_patterns(days=7)
print(patterns['insights'])

# Interactive Q&A
answer = observer.answer_question("Which items are below reorder point?")
print(answer)

# Daily digest for automated reporting
digest = observer.get_daily_digest()
print(digest)
```

### Events are Logged Automatically

All 5 transaction line types (Order, Invoice, Proposal, Purchase, WorkOrder) automatically emit events via signals when:
- Lines are added → `{type}_line_add`
- Lines are updated → `{type}_line_update`
- Lines are deleted → `{type}_line_delete`
- Items are changed → `{type}_line_item_change`

---

## Implementation Files

| File | Purpose |
|------|----------|
| `apps/ai_assistant/models.py` | `InventoryEvent` model with 30+ fields |
| `apps/ai_assistant/services/event_emitter.py` | `InventoryEventEmitter` class |
| `apps/ai_assistant/services/llm_observer.py` | `LLMInventoryObserver` class with all 4 phases |
| `apps/transactions/signals.py` | Signal hooks via `_emit_line_event()` |
| `webclerk3_api/settings.py` | `INVENTORY_EVENTS_ENABLED` flag |

---

## Patent Alignment

This system architecture supports future integration with **U.S. Patent Application 19/356,062** — *Automated Guideways Facilitating 3-Tiered Cargo Shipments* (William Dean James, October 2025).

### Claim Mapping

| Patent Claim | Current Implementation | Future Extension |
|--------------|----------------------|------------------|
| **Claim 4** — LLM-defined load/unload windows | `detect_patterns()` identifies optimal timing | Generate shipping windows for AGT scheduling |
| **Claim 6-7** — Sensor suite event logging | `InventoryEvent.payload` JSON field | Capture temp, accelerometer, tamper, geolocation |
| **Claim 3** — Blockchain chain-of-custody | Immutable event log with `event_id` UUIDs | Hash events to blockchain ledger |
| **Claim 9** — Predictive shipment forecasts | Pattern detection + LLM insights | Feed forecasts to AGT routing modules |
| **Claim 8** — Routing-control modules | Alert events (`below_reorder`, etc.) | Trigger AGT routing decisions |

### Future AGT Event Types

```python
# Not yet implemented — reserved for AGT integration
EVENT_TYPES_AGT = [
    # Physical logistics events
    ('shipment_arrived', 'Subcontainer arrived at facility'),
    ('shipment_departed', 'Subcontainer departed facility'),
    ('container_scanned', 'Subcontainer scanned at checkpoint'),
    ('tier_transfer', 'Subcontainer transferred between tiers'),
    
    # Sensor events
    ('temp_excursion', 'Temperature outside acceptable range'),
    ('impact_detected', 'Accelerometer triggered impact event'),
    ('tamper_detected', 'Tamper sensor activated'),
    ('geofence_violation', 'Subcontainer outside expected zone'),
    
    # AGT scheduling events
    ('window_assigned', 'Load/unload window assigned'),
    ('window_missed', 'Load/unload window deadline passed'),
    ('route_optimized', 'AGT route recalculated'),
]
```

### Three-Tier Logistics Mapping

| Tier | Patent Definition | Inventory Observer Role |
|------|------------------|------------------------|
| **Tier 3** — Long-haul | Rail, aircraft, tube networks | Track inter-city shipment events |
| **Tier 2** — Middle-mile | AGT guideways, autonomous vehicles | Schedule urban distribution windows |
| **Tier 1** — Last-mile | LUVs (pickups, vans, cargobikes) | Coordinate local delivery |

See: [readmes/topics/ai/patent.md](topics/ai/patent.md) for full patent text.

---

## Overview

### Goals

| Goal | Description |
|------|-------------|
| **Learn by watching** | LLM observes user actions without intervening |
| **Capture intent** | Log *why* actions happen, not just *what* changed |
| **Build domain knowledge** | Accumulate patterns for inventory decisions |
| **Enable future assistance** | Foundation for suggestions, anomaly detection |

### Non-Goals (Phase 1)

- No autonomous actions
- No blocking validation
- No real-time interruption of workflows

---

## Event Logging Schema

### Base Event Structure

```python
# apps/inventory/models/inventory_event.py

from django.db import models
from django.contrib.postgres.fields import ArrayField

class InventoryEvent(models.Model):
    """
    Structured event log for LLM observational learning.
    Captures both data changes and semantic context.
    """
    
    # Identity
    id = models.BigAutoField(primary_key=True)
    event_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Event Classification
    EVENT_CATEGORIES = [
        ('transaction', 'Transaction Activity'),
        ('adjustment', 'Manual Adjustment'),
        ('transfer', 'Inter-Location Transfer'),
        ('receipt', 'Goods Receipt'),
        ('count', 'Physical Count'),
        ('reorder', 'Reorder Action'),
        ('alert', 'System Alert'),
    ]
    category = models.CharField(max_length=20, choices=EVENT_CATEGORIES, db_index=True)
    
    EVENT_TYPES = [
        # Transaction events
        ('order_line_add', 'Line added to order'),
        ('order_line_update', 'Line quantity changed'),
        ('order_line_delete', 'Line removed from order'),
        ('order_convert_invoice', 'Order converted to invoice'),
        ('invoice_pack', 'Invoice lines packed/shipped'),
        
        # Purchase events
        ('po_create', 'Purchase order created'),
        ('po_line_add', 'PO line added'),
        ('po_receive', 'PO goods received'),
        
        # Adjustment events
        ('qty_adjust_up', 'Quantity increased'),
        ('qty_adjust_down', 'Quantity decreased'),
        ('cost_adjust', 'Unit cost changed'),
        
        # Alert events
        ('below_reorder', 'Fell below reorder point'),
        ('below_safety', 'Fell below safety stock'),
        ('overstock', 'Exceeded max stock level'),
    ]
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES, db_index=True)
    
    # Actor
    user_id = models.IntegerField(null=True, db_index=True)
    user_name = models.CharField(max_length=100, blank=True)
    is_system = models.BooleanField(default=False)  # True if triggered by automation
    
    # Subject (what was affected)
    item_id = models.IntegerField(null=True, db_index=True)
    item_code = models.CharField(max_length=50, blank=True)
    item_description = models.CharField(max_length=255, blank=True)
    
    # Context (related entities)
    transaction_type = models.CharField(max_length=20, blank=True)  # order, invoice, po, etc.
    transaction_id = models.IntegerField(null=True, db_index=True)
    transaction_ida = models.CharField(max_length=50, blank=True)
    line_id = models.IntegerField(null=True)
    customer_id = models.IntegerField(null=True)
    customer_name = models.CharField(max_length=100, blank=True)
    vendor_id = models.IntegerField(null=True)
    vendor_name = models.CharField(max_length=100, blank=True)
    
    # Quantitative Data
    quantity_before = models.DecimalField(max_digits=12, decimal_places=4, null=True)
    quantity_after = models.DecimalField(max_digits=12, decimal_places=4, null=True)
    quantity_delta = models.DecimalField(max_digits=12, decimal_places=4, null=True)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=4, null=True)
    unit_price = models.DecimalField(max_digits=12, decimal_places=4, null=True)
    
    # Inventory Buckets (snapshot after event)
    on_hand = models.DecimalField(max_digits=12, decimal_places=4, null=True)
    on_order = models.DecimalField(max_digits=12, decimal_places=4, null=True)  # on_so
    on_purchase = models.DecimalField(max_digits=12, decimal_places=4, null=True)  # on_po
    available = models.DecimalField(max_digits=12, decimal_places=4, null=True)
    reorder_point = models.DecimalField(max_digits=12, decimal_places=4, null=True)
    
    # Semantic Context (for LLM consumption)
    reason = models.TextField(blank=True)  # User-provided or inferred reason
    tags = ArrayField(models.CharField(max_length=50), default=list, blank=True)
    
    # Raw payload for detailed analysis
    payload = models.JSONField(default=dict, blank=True)
    
    # LLM Processing
    llm_summary = models.TextField(blank=True)  # LLM-generated natural language summary
    llm_processed_at = models.DateTimeField(null=True)
    
    class Meta:
        db_table = 'inventory_event'
        indexes = [
            models.Index(fields=['created_at', 'category']),
            models.Index(fields=['item_id', 'created_at']),
            models.Index(fields=['transaction_id', 'transaction_type']),
        ]
        ordering = ['-created_at']
```

### Event Payload Examples

```python
# Order line added
{
    "category": "transaction",
    "event_type": "order_line_add",
    "item_id": 243,
    "item_code": "WIDGET-A",
    "item_description": "Standard Widget Type A",
    "transaction_type": "order",
    "transaction_id": 1234,
    "transaction_ida": "SO-1234",
    "customer_id": 83,
    "customer_name": "Acme Corp",
    "quantity_delta": 10,
    "unit_price": 25.00,
    "on_hand": 150,
    "on_order": 45,  # includes this new 10
    "available": 105,
    "reorder_point": 50,
    "payload": {
        "line": {
            "quantity": {"staged": 10, "active": 10},
            "price": {"unit": 25.00, "extended": 250.00}
        },
        "order": {
            "status": "planned",
            "priority": "normal"
        }
    }
}

# Below reorder point alert
{
    "category": "alert",
    "event_type": "below_reorder",
    "item_id": 456,
    "item_code": "GADGET-B",
    "is_system": True,
    "quantity_before": 52,
    "quantity_after": 48,
    "quantity_delta": -4,
    "on_hand": 48,
    "reorder_point": 50,
    "tags": ["reorder_needed", "auto_detected"],
    "reason": "Invoice 5678 reduced on_hand below reorder point"
}
```

---

## Observer Service Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           User Actions                                   │
│  (Create Order, Adjust Qty, Receive PO, etc.)                           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         Django Signals                                   │
│  post_save → OrderLine, InvoiceLine, PurchaseLine, Item                 │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Event Emitter Service                                 │
│  apps/ai_assistant/services/event_emitter.py                            │
│                                                                          │
│  • Captures before/after state                                           │
│  • Enriches with context (customer, vendor, item details)               │
│  • Computes deltas and bucket snapshots                                 │
│  • Writes to InventoryEvent table                                        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      Event Queue (Celery)                                │
│  Optional async processing for LLM enrichment                           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     LLM Observer Service                                 │
│  apps/ai_assistant/services/llm_observer.py                             │
│                                                                          │
│  Phase 2: summarize_event(), get_item_narrative()                       │
│  Phase 3: detect_patterns() — trends, anomalies                         │
│  Phase 4: answer_question() — interactive Q&A                           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        LLM Context Store                                 │
│  Vector DB or searchable summaries for RAG                              │
└─────────────────────────────────────────────────────────────────────────┘
```

### Event Emitter Service

```python
# apps/inventory/services/event_emitter.py

from decimal import Decimal
from typing import Optional
from django.utils import timezone

from apps.inventory.models import InventoryEvent, Item


class InventoryEventEmitter:
    """
    Emits structured events for LLM observational learning.
    Called from signals or service layer after inventory-affecting operations.
    """
    
    @classmethod
    def emit(
        cls,
        category: str,
        event_type: str,
        item_id: int,
        *,
        user=None,
        transaction_type: str = '',
        transaction_id: int = None,
        quantity_before: Decimal = None,
        quantity_after: Decimal = None,
        reason: str = '',
        tags: list = None,
        payload: dict = None,
    ) -> InventoryEvent:
        """
        Create an inventory event with enriched context.
        """
        # Fetch item for enrichment
        item = Item.objects.filter(id=item_id).first()
        item_data = item.data if item else {}
        
        # Compute delta
        delta = None
        if quantity_before is not None and quantity_after is not None:
            delta = quantity_after - quantity_before
        
        # Get current inventory buckets
        qty = item_data.get('quantity', {}) if item else {}
        
        event = InventoryEvent.objects.create(
            category=category,
            event_type=event_type,
            
            # Actor
            user_id=user.id if user else None,
            user_name=getattr(user, 'display_name', str(user)) if user else '',
            is_system=user is None,
            
            # Subject
            item_id=item_id,
            item_code=item_data.get('ida', ''),
            item_description=item_data.get('description', {}).get('en', ''),
            
            # Context
            transaction_type=transaction_type,
            transaction_id=transaction_id,
            
            # Quantities
            quantity_before=quantity_before,
            quantity_after=quantity_after,
            quantity_delta=delta,
            
            # Buckets
            on_hand=qty.get('on_hand'),
            on_order=qty.get('on_so'),
            on_purchase=qty.get('on_po'),
            available=qty.get('available'),
            reorder_point=qty.get('reorder_point'),
            
            # Semantic
            reason=reason,
            tags=tags or [],
            payload=payload or {},
        )
        
        # Queue for LLM processing (Phase 2+)
        # from apps.inventory.tasks import process_event_with_llm
        # process_event_with_llm.delay(event.id)
        
        return event
    
    @classmethod
    def emit_line_event(
        cls,
        event_type: str,
        line,
        transaction,
        *,
        user=None,
        quantity_before: Decimal = None,
        reason: str = '',
    ):
        """
        Convenience method for transaction line events.
        """
        item_id = line.item_id
        qty = line.quantity or {}
        quantity_after = Decimal(str(qty.get('staged', 0)))
        
        # Build payload with line and transaction context
        payload = {
            'line': {
                'id': line.id,
                'line_number': line.line_number,
                'quantity': qty,
                'price': line.price,
                'cost': line.cost,
            },
            'transaction': {
                'id': transaction.id,
                'ida': getattr(transaction, 'ida', ''),
                'status': transaction.status,
            }
        }
        
        # Add customer/vendor if available
        if hasattr(transaction, 'customer_id') and transaction.customer_id:
            payload['customer'] = {
                'id': transaction.customer_id,
                'name': getattr(transaction, 'customer_name', ''),
            }
        
        return cls.emit(
            category='transaction',
            event_type=event_type,
            item_id=item_id,
            user=user,
            transaction_type=transaction._meta.model_name,
            transaction_id=transaction.id,
            quantity_before=quantity_before,
            quantity_after=quantity_after,
            reason=reason,
            payload=payload,
        )
```

### LLM Observer Service

```python
# apps/inventory/services/llm_observer.py

from typing import List, Optional
from datetime import timedelta
from django.utils import timezone

from apps.inventory.models import InventoryEvent


class LLMInventoryObserver:
    """
    Processes inventory events for LLM comprehension.
    Generates natural language summaries and detects patterns.
    """
    
    def __init__(self, llm_client=None):
        self.llm = llm_client  # Injected LLM API client
    
    def summarize_event(self, event: InventoryEvent) -> str:
        """
        Generate a natural language summary of a single event.
        """
        templates = {
            'order_line_add': (
                "{user} added {delta} units of {item} to {transaction}. "
                "Customer: {customer}. Unit price: ${price}. "
                "Current on-hand: {on_hand}, available: {available}."
            ),
            'order_line_update': (
                "{user} changed quantity on {transaction} line for {item} "
                "from {before} to {after} ({delta:+}). "
                "Reason: {reason}"
            ),
            'below_reorder': (
                "ALERT: {item} dropped below reorder point. "
                "On-hand: {on_hand}, reorder point: {reorder}. "
                "Consider creating a purchase order."
            ),
            'po_receive': (
                "Received {delta} units of {item} from vendor {vendor}. "
                "PO: {transaction}. New on-hand: {on_hand}."
            ),
        }
        
        template = templates.get(event.event_type, "{event_type}: {item} - {delta}")
        
        return template.format(
            user=event.user_name or 'System',
            item=f"{event.item_code} ({event.item_description})",
            delta=event.quantity_delta,
            before=event.quantity_before,
            after=event.quantity_after,
            transaction=f"{event.transaction_type} {event.transaction_ida or event.transaction_id}",
            customer=event.payload.get('customer', {}).get('name', 'N/A'),
            vendor=event.vendor_name or 'N/A',
            price=event.unit_price or 0,
            on_hand=event.on_hand,
            available=event.available,
            reorder=event.reorder_point,
            reason=event.reason or 'not specified',
            event_type=event.event_type,
        )
    
    def get_item_narrative(self, item_id: int, days: int = 30) -> str:
        """
        Generate a narrative of recent activity for an item.
        Useful for LLM context when answering questions.
        """
        since = timezone.now() - timedelta(days=days)
        events = InventoryEvent.objects.filter(
            item_id=item_id,
            created_at__gte=since
        ).order_by('created_at')
        
        if not events.exists():
            return f"No activity for item {item_id} in the last {days} days."
        
        summaries = [self.summarize_event(e) for e in events[:50]]
        
        narrative = f"Activity for item {item_id} (last {days} days):\n"
        narrative += "\n".join(f"- {s}" for s in summaries)
        
        return narrative
    
    def detect_patterns(self, item_id: int) -> List[str]:
        """
        Analyze events to detect patterns (Phase 2).
        Returns list of observations.
        """
        # Example pattern detection logic
        observations = []
        
        # Check for frequent reorder alerts
        recent_alerts = InventoryEvent.objects.filter(
            item_id=item_id,
            event_type='below_reorder',
            created_at__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        if recent_alerts >= 3:
            observations.append(
                f"Item triggered reorder alert {recent_alerts} times in 30 days. "
                "Consider increasing reorder point or safety stock."
            )
        
        # Check for large quantity swings
        # ... additional pattern logic
        
        return observations
    
    async def answer_question(self, question: str, context_items: List[int] = None) -> str:
        """
        Answer a natural language question about inventory (Phase 3).
        """
        if not self.llm:
            return "LLM not configured"
        
        # Build context from recent events
        context_parts = []
        if context_items:
            for item_id in context_items[:5]:
                context_parts.append(self.get_item_narrative(item_id, days=14))
        
        prompt = f"""You are an inventory management assistant.
        
Context:
{chr(10).join(context_parts)}

Question: {question}

Provide a helpful, concise answer based on the inventory activity shown."""
        
        response = await self.llm.complete(prompt)
        return response
```

---

## Staging Phases

### Phase 1: Silent Observer (Week 1-2)

**Goal:** Capture events without affecting workflows

| Task | Description |
|------|-------------|
| Create `InventoryEvent` model | Migration + admin interface |
| Add signals to capture events | Line saves, item updates |
| Basic event enrichment | Item details, transaction context |
| Admin dashboard | View recent events |

**Success Criteria:**
- Events logged for all inventory-affecting operations
- No performance impact on existing workflows
- Admin can review event history

### Phase 2: Summarize & Report (Week 3-4)

**Goal:** LLM generates human-readable summaries

| Task | Description |
|------|-------------|
| Implement `LLMInventoryObserver` | Template-based summaries first |
| Daily digest generation | Summary of inventory activity |
| Item history narrative | Contextual story for each item |
| Alert enrichment | Natural language for threshold alerts |

**Success Criteria:**
- LLM summaries stored on events
- Users can view narrative history per item
- Daily/weekly digest available

### Phase 3: Pattern Detection (Week 5-6)

**Goal:** LLM identifies trends and anomalies

| Task | Description |
|------|-------------|
| Implement pattern detection | Reorder frequency, demand spikes |
| Anomaly flagging | Unusual quantity changes |
| Suggestion generation | "Consider reordering X" |
| Confidence scoring | How certain is the pattern |

**Success Criteria:**
- Patterns surfaced in UI
- Anomalies highlighted for review
- Suggestions logged (not acted upon)

### Phase 4: Interactive Assistant (Week 7+)

**Goal:** LLM answers questions and assists workflows

| Task | Description |
|------|-------------|
| Q&A interface | "Why did X inventory drop?" |
| RAG integration | Vector search over event history |
| Workflow suggestions | "Should I create a PO?" |
| Draft generation | Pre-fill PO based on patterns |

**Success Criteria:**
- Users can ask questions in natural language
- LLM provides accurate, contextual answers
- Optional action suggestions (user confirms)

---

## Integration Points

### Signal Registration

```python
# apps/inventory/signals.py

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.transactions.models import OrderLine, InvoiceLine, PurchaseLine
from apps.inventory.services.event_emitter import InventoryEventEmitter


# Capture pre-save state for delta calculation
@receiver(pre_save, sender=OrderLine)
def capture_order_line_before(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            instance._qty_before = old.quantity.get('staged', 0) if old.quantity else 0
        except sender.DoesNotExist:
            instance._qty_before = None
    else:
        instance._qty_before = None


@receiver(post_save, sender=OrderLine)
def emit_order_line_event(sender, instance, created, **kwargs):
    event_type = 'order_line_add' if created else 'order_line_update'
    qty_before = getattr(instance, '_qty_before', None)
    
    InventoryEventEmitter.emit_line_event(
        event_type=event_type,
        line=instance,
        transaction=instance.parent,
        quantity_before=qty_before,
    )


# Similar for InvoiceLine, PurchaseLine, etc.
```

### Pending Processor Hook

```python
# apps/transactions/services/pending_inventory_processor.py

def process_line_item_pending(pending: Pending) -> None:
    # ... existing processing logic ...
    
    # After applying delta to item:
    if setting_enabled('INVENTORY_EVENTS_ENABLED'):
        from apps.inventory.services.event_emitter import InventoryEventEmitter
        
        InventoryEventEmitter.emit(
            category='transaction',
            event_type=f"{pending.transaction_type}_pending_processed",
            item_id=pending.item_id,
            quantity_before=old_on_hand,
            quantity_after=new_on_hand,
            transaction_type=pending.transaction_type,
            transaction_id=pending.transaction_id,
            payload={'pending_id': pending.id, 'bucket': pending.bucket},
        )
```

---

## Example Scenarios

### Scenario 1: Order Created, Inventory Question

```
User: Creates order for 10 units of WIDGET-A for Acme Corp

Event logged:
{
  "event_type": "order_line_add",
  "item_code": "WIDGET-A",
  "customer_name": "Acme Corp",
  "quantity_delta": 10,
  "on_hand": 150,
  "on_order": 45,
  "available": 105
}

LLM Summary:
"Bill added 10 units of WIDGET-A (Standard Widget Type A) to order SO-1234. 
Customer: Acme Corp. Unit price: $25.00. Current on-hand: 150, available: 105."

Later, user asks: "What's happening with WIDGET-A?"

LLM Response:
"WIDGET-A has had moderate activity this week:
- 10 units committed to SO-1234 (Acme Corp) on Monday
- 5 units shipped on Invoice IN-5678 (Beta Inc) on Tuesday
- Current inventory: 145 on-hand, 45 on order, 100 available
- Reorder point is 50, so stock levels are healthy."
```

### Scenario 2: Reorder Alert

```
Invoice shipped, reducing on-hand below reorder point

Event logged:
{
  "event_type": "below_reorder",
  "item_code": "GADGET-B",
  "is_system": true,
  "on_hand": 48,
  "reorder_point": 50,
  "tags": ["reorder_needed", "auto_detected"]
}

LLM Summary:
"ALERT: GADGET-B dropped below reorder point. On-hand: 48, reorder point: 50. 
Consider creating a purchase order."

Pattern Detection (Phase 3):
"GADGET-B has triggered reorder alerts 4 times this month. 
Historical demand suggests increasing reorder point to 75 would reduce stockout risk."
```

---

## Configuration

### Settings

```python
# webclerk3_api/settings.py

# Enable/disable inventory event logging for LLM observational learning
INVENTORY_EVENTS_ENABLED = config('INVENTORY_EVENTS_ENABLED', default=True, cast=bool)

# Ollama settings (used by LLM Observer)
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "deepseek-r1:8b"
OLLAMA_TIMEOUT = 120
```

### Environment Variables

```bash
# .env
INVENTORY_EVENTS_ENABLED=true   # Set to false to disable event logging
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=deepseek-r1:8b
```

### Disabling Events

To disable inventory event logging without code changes:

```bash
export INVENTORY_EVENTS_ENABLED=false
```

Or in `.env`:
```
INVENTORY_EVENTS_ENABLED=false
```

---

## Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| `InventoryEvent` model | ✅ Done | 30+ fields, migration applied |
| `InventoryEventEmitter` service | ✅ Done | `emit()` and `emit_line_event()` methods |
| `LLMInventoryObserver` service | ✅ Done | All 4 phases implemented |
| Signal hooks | ✅ Done | All 5 line types wired |
| Feature flag | ✅ Done | `INVENTORY_EVENTS_ENABLED` in settings |
| Admin view | ⏳ Pending | Future enhancement |
| Celery async processing | ⏳ Pending | Optional for high volume |
