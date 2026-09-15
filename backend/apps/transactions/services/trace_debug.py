"""
Transaction Flow Trace Debugging Utility.

Enable strategic tracing to watch transaction flows through
LineItemService → Pending → Item.quantity updates.

Usage:
    # Enable tracing for specific items
    from apps.transactions.services.trace_debug import enable_trace, disable_trace
    enable_trace([249, 250, 251])
    
    # ... perform transactions ...
    
    disable_trace()
    
    # Or use as context manager
    with transaction_trace([249, 250, 251]):
        # ... perform transactions ...

Configuration:
    TRACE_ENABLED: Set to True to enable tracing
    TRACE_ITEM_IDS: Set of item IDs to trace (empty = all items)
    
Log files saved to: webClerk3/logs/trace_YYYYMMDD_HHMMSS.log
"""

import json
import os
from datetime import datetime
from decimal import Decimal
from functools import wraps
from pathlib import Path
from typing import Optional, Set, List, Any

# ---------------------------------------------------------------------------
# Trace Configuration
# ---------------------------------------------------------------------------
TRACE_ENABLED = False
TRACE_ITEM_IDS: Set[int] = set()  # Empty = trace all items
TRACE_LOG_FILE = None  # File handle for logging

# Colors for terminal output (ANSI codes)
RESET = '\033[0m'
BOLD = '\033[1m'
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
MAGENTA = '\033[95m'
CYAN = '\033[96m'


def _get_log_dir() -> Path:
    """Get or create the logs directory."""
    # Find webClerk3 root (where manage.py is)
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / 'manage.py').exists():
            log_dir = parent / 'logs'
            log_dir.mkdir(exist_ok=True)
            return log_dir
    # Fallback to current directory
    return Path('.')


def _strip_ansi(text: str) -> str:
    """Remove ANSI color codes for plain text logging."""
    import re
    return re.sub(r'\033\[[0-9;]*m', '', text)


def _log_write(message: str):
    """Write to both console and log file."""
    print(message)
    if TRACE_LOG_FILE:
        TRACE_LOG_FILE.write(_strip_ansi(message) + '\n')
        TRACE_LOG_FILE.flush()


def enable_trace(item_ids: Optional[List[int]] = None, log_name: Optional[str] = None):
    """
    Enable tracing, optionally filtering to specific item IDs.
    
    Args:
        item_ids: List of item IDs to trace (None = all items)
        log_name: Custom log filename (default: trace_YYYYMMDD_HHMMSS.log)
    """
    global TRACE_ENABLED, TRACE_ITEM_IDS, TRACE_LOG_FILE
    TRACE_ENABLED = True
    TRACE_ITEM_IDS = set(item_ids) if item_ids else set()
    
    # Create log file
    log_dir = _get_log_dir()
    if log_name:
        log_path = log_dir / log_name
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_path = log_dir / f'trace_{timestamp}.log'
    
    TRACE_LOG_FILE = open(log_path, 'w')
    
    # Write header
    header = f"""
{'='*70}
  TRANSACTION TRACE LOG
  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
  Items:   {sorted(TRACE_ITEM_IDS) if TRACE_ITEM_IDS else 'ALL'}
  Log:     {log_path}
{'='*70}
"""
    _log_write(f"\n{BOLD}{GREEN}═══ TRACE ENABLED ═══{RESET}")
    if TRACE_ITEM_IDS:
        _log_write(f"Watching items: {sorted(TRACE_ITEM_IDS)}")
    else:
        _log_write("Watching ALL items")
    _log_write(f"Log file: {log_path}")
    _log_write("")
    
    # Write plain header to file
    TRACE_LOG_FILE.write(header)
    TRACE_LOG_FILE.flush()
    
    return log_path


def disable_trace():
    """Disable tracing and close log file."""
    global TRACE_ENABLED, TRACE_LOG_FILE
    TRACE_ENABLED = False
    
    if TRACE_LOG_FILE:
        footer = f"""
{'='*70}
  TRACE ENDED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*70}
"""
        TRACE_LOG_FILE.write(footer)
        TRACE_LOG_FILE.close()
        TRACE_LOG_FILE = None
    
    print(f"\n{BOLD}{RED}═══ TRACE DISABLED ═══{RESET}\n")


class transaction_trace:
    """Context manager for tracing."""
    def __init__(self, item_ids: Optional[List[int]] = None, log_name: Optional[str] = None):
        self.item_ids = item_ids
        self.log_name = log_name
        self.log_path = None
        
    def __enter__(self):
        self.log_path = enable_trace(self.item_ids, self.log_name)
        return self
        
    def __exit__(self, *args):
        disable_trace()


def should_trace(item_id: Optional[int]) -> bool:
    """Check if an item should be traced."""
    if not TRACE_ENABLED:
        return False
    if not TRACE_ITEM_IDS:
        return True  # Trace all
    return item_id in TRACE_ITEM_IDS


def _format_json(obj: Any, indent: int = 2) -> str:
    """Format object as JSON for display."""
    def default_serializer(o):
        if isinstance(o, Decimal):
            return float(o)
        if hasattr(o, 'isoformat'):
            return o.isoformat()
        return str(o)
    return json.dumps(obj, indent=indent, default=default_serializer)


def _ordered_quantity(q: dict) -> dict:
    """Return quantity dict with keys in logical order."""
    key_order = (
        'on_hand', 'available', 'allocated',
        'sell_default', 'purchase_default',
        'on_po', 'on_wo', 'on_so', 'invoiced',
    )
    return {k: q.get(k, 0) for k in key_order if k in q}


# ---------------------------------------------------------------------------
# Trace Output Functions
# ---------------------------------------------------------------------------

def trace_line_add(
    transaction_type: str,
    transaction_pk: int,
    transaction_ida: str,
    item_id: int,
    item_ida: str,
    quantity: float,
    unit_price: float,
    unit_cost: float,
    line_pk: int,
):
    """Trace when a line is added to a transaction."""
    if not should_trace(item_id):
        return
    
    ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    _log_write(f"\n{BOLD}{CYAN}┌─────────────────────────────────────────────────────────────────┐{RESET}")
    _log_write(f"{BOLD}{CYAN}│  LINE ADD  │  {ts}                                           │{RESET}")
    _log_write(f"{BOLD}{CYAN}└─────────────────────────────────────────────────────────────────┘{RESET}")
    _log_write(f"  {YELLOW}Transaction:{RESET} {transaction_type} #{transaction_pk} ({transaction_ida})")
    _log_write(f"  {YELLOW}Item:{RESET}        #{item_id} ({item_ida})")
    _log_write(f"  {YELLOW}Line PK:{RESET}     {line_pk}")
    _log_write(f"  {YELLOW}Quantity:{RESET}    {GREEN}{quantity}{RESET}")
    _log_write(f"  {YELLOW}Unit Price:{RESET}  ${unit_price:.4f}")
    _log_write(f"  {YELLOW}Unit Cost:{RESET}   ${unit_cost:.4f}")


def trace_pending_created(
    purpose: str,
    pending_pk: int,
    item_id: int,
    item_ida: str,
    pending_type: str,
    data: dict,
):
    """Trace when a Pending record is created."""
    if not should_trace(item_id):
        return
    
    ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    _log_write(f"\n{BOLD}{MAGENTA}┌─────────────────────────────────────────────────────────────────┐{RESET}")
    _log_write(f"{BOLD}{MAGENTA}│  PENDING CREATED  │  {ts}                                    │{RESET}")
    _log_write(f"{BOLD}{MAGENTA}└─────────────────────────────────────────────────────────────────┘{RESET}")
    _log_write(f"  {YELLOW}Pending PK:{RESET}  {pending_pk}")
    _log_write(f"  {YELLOW}Purpose:{RESET}     {purpose}")
    _log_write(f"  {YELLOW}Type:{RESET}        {pending_type}")
    _log_write(f"  {YELLOW}Item:{RESET}        #{item_id} ({item_ida})")
    
    # Show relevant quantity deltas
    buckets = ['on_so', 'on_po', 'on_wo', 'invoiced']
    deltas = {k: data.get(k, 0) for k in buckets if data.get(k, 0) != 0}
    if deltas:
        _log_write(f"  {YELLOW}Deltas:{RESET}      {GREEN}{deltas}{RESET}")


def trace_pending_processing_start(
    item_id: int,
    item_ida: str,
    pending_count: int,
    current_quantity: dict,
):
    """Trace when pending processing begins for an item."""
    if not should_trace(item_id):
        return
    
    ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    _log_write(f"\n{BOLD}{BLUE}┌─────────────────────────────────────────────────────────────────┐{RESET}")
    _log_write(f"{BOLD}{BLUE}│  PENDING PROCESS START  │  {ts}                             │{RESET}")
    _log_write(f"{BOLD}{BLUE}└─────────────────────────────────────────────────────────────────┘{RESET}")
    _log_write(f"  {YELLOW}Item:{RESET}        #{item_id} ({item_ida})")
    _log_write(f"  {YELLOW}Records:{RESET}     {pending_count} pending record(s) to process")
    _log_write(f"  {YELLOW}Before:{RESET}")
    q = _ordered_quantity(current_quantity)
    _log_write(f"    {q}")


def trace_pending_processing_complete(
    item_id: int,
    item_ida: str,
    deltas: dict,
    new_quantity: dict,
):
    """Trace when pending processing completes for an item."""
    if not should_trace(item_id):
        return
    
    ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    _log_write(f"\n{BOLD}{GREEN}┌─────────────────────────────────────────────────────────────────┐{RESET}")
    _log_write(f"{BOLD}{GREEN}│  PENDING PROCESS COMPLETE  │  {ts}                          │{RESET}")
    _log_write(f"{BOLD}{GREEN}└─────────────────────────────────────────────────────────────────┘{RESET}")
    _log_write(f"  {YELLOW}Item:{RESET}        #{item_id} ({item_ida})")
    _log_write(f"  {YELLOW}Applied:{RESET}     {deltas}")
    _log_write(f"  {YELLOW}After:{RESET}")
    q = _ordered_quantity(new_quantity)
    _log_write(f"    {q}")


def trace_item_quantity_snapshot(
    item_id: int,
    item_ida: str,
    quantity: dict,
    context: str = "",
):
    """Trace a snapshot of item quantity at a specific point."""
    if not should_trace(item_id):
        return
    
    ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    ctx = f"  │  {context}" if context else ""
    _log_write(f"\n{BOLD}{YELLOW}┌─────────────────────────────────────────────────────────────────┐{RESET}")
    _log_write(f"{BOLD}{YELLOW}│  ITEM SNAPSHOT  │  {ts}{ctx:<24}│{RESET}")
    _log_write(f"{BOLD}{YELLOW}└─────────────────────────────────────────────────────────────────┘{RESET}")
    _log_write(f"  {YELLOW}Item:{RESET}        #{item_id} ({item_ida})")
    q = _ordered_quantity(quantity)
    _log_write(f"  {YELLOW}Quantity:{RESET}    {q}")


def trace_custom(message: str, item_id: Optional[int] = None, data: Any = None):
    """Trace a custom message."""
    if item_id and not should_trace(item_id):
        return
    if not TRACE_ENABLED:
        return
    
    ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    _log_write(f"\n{BOLD}[{ts}]{RESET} {message}")
    if data:
        _log_write(f"  {_format_json(data)}")
