import signal
import time
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.products.services.inventory_adjustment_processor import process_pending_inventory as process_stack_adjustments


class Command(BaseCommand):
    help = "Process all pending inventory records (stack adjustments + line item changes)."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._running = True

    def add_arguments(self, parser):  # pragma: no cover
        parser.add_argument('--limit', type=int, default=100)
        parser.add_argument('--apply-insufficient', action='store_true', help='Force apply even if remaining < qty (may drive negative).')
        parser.add_argument('--cancel-on-insufficient', action='store_true', help='Cancel rows that cannot be applied due to insufficient qty.')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--daemon', action='store_true', help='Run continuously as background daemon.')
        parser.add_argument('--interval', type=int, 
                          default=getattr(settings, 'INVENTORY_PENDING_PROCESS_DELAY', 5),
                          help='Seconds between runs in daemon mode (default: 5)')
        parser.add_argument('--skip-stacks', action='store_true', help='Skip stack-level adjustments, only process line items.')
        parser.add_argument('--skip-lines', action='store_true', help='Skip line-item pending, only process stack adjustments.')

    def handle(self, *args, **opts):  # pragma: no cover
        if opts['daemon']:
            self._run_daemon(opts)
        else:
            self._run_once(opts)

    def _run_once(self, opts):
        """Single processing run."""
        dry_run = bool(opts.get('dry_run'))
        limit = opts['limit']
        
        # 1. Process stack-level adjustments (PendingInventoryAdjustment)
        if not opts.get('skip_stacks'):
            stack_summary = process_stack_adjustments(
                limit=limit,
                apply_insufficient=bool(opts.get('apply_insufficient')),
                cancel_on_insufficient=bool(opts.get('cancel_on_insufficient')),
                dry_run=dry_run,
            )
            self.stdout.write(f"Stack adjustments: {stack_summary}")
        
        # 2. Process line-item pending (Pending with purpose='inventory_line_add')
        if not opts.get('skip_lines'):
            try:
                from apps.transactions.services.pending_inventory_processor import process_line_item_pending
                line_summary = process_line_item_pending(limit=limit, dry_run=dry_run)
                self.stdout.write(f"Line item pending: {line_summary}")
            except ImportError:
                self.stdout.write(self.style.WARNING("Line item processor not available"))
        
        self.stdout.write(self.style.SUCCESS("Processing complete."))

    def _run_daemon(self, opts):
        """Run continuously as daemon."""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        interval = opts['interval']
        self.stdout.write(self.style.SUCCESS(
            f"Starting inventory pending daemon (interval={interval}s)"
        ))
        self.stdout.write("Press Ctrl+C to stop...")
        
        runs = 0
        while self._running:
            runs += 1
            try:
                self._run_once(opts)
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error in run {runs}: {e}"))
            
            # Sleep in 1s increments for responsive shutdown
            for _ in range(interval):
                if not self._running:
                    break
                time.sleep(1)
        
        self.stdout.write(self.style.SUCCESS(f"Daemon stopped after {runs} runs."))

    def _signal_handler(self, signum, frame):
        self.stdout.write("\nShutting down...")
        self._running = False
