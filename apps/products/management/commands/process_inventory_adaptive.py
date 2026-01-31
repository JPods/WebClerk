"""
Management command for adaptive inventory processing.

Usage:
    # Single run (for testing)
    python manage.py process_inventory_adaptive
    
    # Daemon mode (continuous with adaptive delay)
    python manage.py process_inventory_adaptive --daemon
    
    # Custom settings
    python manage.py process_inventory_adaptive --daemon --base-delay=2 --max-delay=30
    
    # Dry run
    python manage.py process_inventory_adaptive --dry-run
    
    # Verbose output
    python manage.py process_inventory_adaptive --daemon -v 2
"""

import signal
import sys
import time
from datetime import datetime

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Process pending inventory with adaptive delay (backs off when idle, speeds up when busy)"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._shutdown = False
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run continuously with adaptive delay between cycles'
        )
        parser.add_argument(
            '--base-delay',
            type=int,
            default=5,
            help='Minimum polling interval in seconds (default: 5)'
        )
        parser.add_argument(
            '--max-delay',
            type=int,
            default=120,
            help='Maximum polling interval in seconds (default: 120)'
        )
        parser.add_argument(
            '--increment',
            type=int,
            default=5,
            help='Delay increment when backing off (default: 5)'
        )
        parser.add_argument(
            '--idle-cycles',
            type=int,
            default=5,
            help='Consecutive empty cycles before increasing delay (default: 5)'
        )
        parser.add_argument(
            '--stale-timeout',
            type=int,
            default=300,
            help='Seconds before a record is considered stale (default: 300)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=200,
            help='Maximum records to process per cycle (default: 200)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate processing without making changes'
        )
        parser.add_argument(
            '--no-stale-check',
            action='store_true',
            help='Skip checking for stale records'
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset adaptive state to base delay before starting'
        )
    
    def handle(self, *args, **options):
        from apps.products import tasks
        
        # Apply custom settings
        tasks.INVENTORY_CLEAR_BASE_DELAY = options['base_delay']
        tasks.INVENTORY_CLEAR_MAX_DELAY = options['max_delay']
        tasks.INVENTORY_CLEAR_DELAY_INCREMENT = options['increment']
        tasks.INVENTORY_CLEAR_IDLE_CYCLES = options['idle_cycles']
        tasks.INVENTORY_CLEAR_STALE_TIMEOUT = options['stale_timeout']
        
        daemon = options['daemon']
        limit = options['limit']
        dry_run = options['dry_run']
        check_stale = not options['no_stale_check']
        verbosity = options['verbosity']
        
        # Print configuration
        self.stdout.write(self.style.NOTICE("=" * 60))
        self.stdout.write(self.style.NOTICE("Adaptive Inventory Processor"))
        self.stdout.write(self.style.NOTICE("=" * 60))
        self.stdout.write(f"  Base delay:     {options['base_delay']}s")
        self.stdout.write(f"  Max delay:      {options['max_delay']}s")
        self.stdout.write(f"  Increment:      {options['increment']}s")
        self.stdout.write(f"  Idle cycles:    {options['idle_cycles']}")
        self.stdout.write(f"  Stale timeout:  {options['stale_timeout']}s")
        self.stdout.write(f"  Limit per run:  {limit}")
        self.stdout.write(f"  Mode:           {'daemon' if daemon else 'single-run'}")
        if dry_run:
            self.stdout.write(self.style.WARNING("  DRY RUN MODE"))
        self.stdout.write("")
        
        # Reset state if requested
        if options['reset']:
            tasks.reset_adaptive_state()
            self.stdout.write(self.style.SUCCESS("Adaptive state reset to base delay"))
        
        # Setup signal handlers for graceful shutdown
        if daemon:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            self.stdout.write(self.style.NOTICE("Press Ctrl+C to stop gracefully\n"))
        
        cycle_count = 0
        total_processed = 0
        
        while not self._shutdown:
            cycle_count += 1
            cycle_start = datetime.now()
            
            # Process with adaptive delay
            result = tasks.process_pending_inventory_adaptive(
                limit=limit,
                dry_run=dry_run,
                check_stale=check_stale,
            )
            
            processed = result.get('processed', 0)
            total_processed += processed
            next_delay = result.get('next_delay', options['base_delay'])
            idle_count = result.get('idle_count', 0)
            stale_info = result.get('stale_info', {})
            
            # Format output
            timestamp = cycle_start.strftime('%H:%M:%S')
            
            if processed > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[{timestamp}] Cycle {cycle_count}: "
                        f"Processed {processed} records, "
                        f"delay → {next_delay}s"
                    )
                )
            else:
                if verbosity >= 2:
                    self.stdout.write(
                        f"[{timestamp}] Cycle {cycle_count}: "
                        f"No records, idle {idle_count}/{options['idle_cycles']}, "
                        f"next in {next_delay}s"
                    )
            
            # Report stale records
            stale_count = stale_info.get('stale_count', 0)
            if stale_count > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f"[{timestamp}] ⚠️  {stale_count} stale records detected!"
                    )
                )
            
            # Exit if not daemon mode
            if not daemon:
                break
            
            # Sleep until next cycle
            try:
                time.sleep(next_delay)
            except KeyboardInterrupt:
                break
        
        # Final summary
        self.stdout.write("")
        self.stdout.write(self.style.NOTICE("=" * 60))
        self.stdout.write(self.style.SUCCESS(
            f"Completed {cycle_count} cycles, processed {total_processed} total records"
        ))
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.stdout.write("")
        self.stdout.write(self.style.WARNING("Shutdown signal received, finishing current cycle..."))
        self._shutdown = True
