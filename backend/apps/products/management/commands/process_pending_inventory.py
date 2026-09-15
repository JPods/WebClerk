import signal
import time
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = "Process all pending inventory records (Pending with purpose='inventory_*')."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._running = True

    def add_arguments(self, parser):  # pragma: no cover
        parser.add_argument('--limit', type=int, default=100)
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--daemon', action='store_true', help='Run continuously as background daemon.')
        parser.add_argument('--interval', type=int,
                          default=getattr(settings, 'INVENTORY_PENDING_PROCESS_DELAY', 5),
                          help='Seconds between runs in daemon mode (default: 5)')

    def handle(self, *args, **opts):  # pragma: no cover
        if opts['daemon']:
            self._run_daemon(opts)
        else:
            self._run_once(opts)

    def _run_once(self, opts):
        """Single processing run — retry unprocessed Pending records."""
        from apps.transactions.services.inventory_pending_process import process_line_item_pending
        limit = opts['limit']
        dry_run = bool(opts.get('dry_run'))

        summary = process_line_item_pending(limit=limit, dry_run=dry_run)
        self.stdout.write(f"Pending inventory: {summary}")
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

            for _ in range(interval):
                if not self._running:
                    break
                time.sleep(1)

        self.stdout.write(self.style.SUCCESS(f"Daemon stopped after {runs} runs."))

    def _signal_handler(self, signum, frame):
        self.stdout.write("\nShutting down...")
        self._running = False
