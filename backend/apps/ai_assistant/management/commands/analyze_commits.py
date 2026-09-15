"""
Management command to analyze git commits for schema drift.

Usage:
    # Analyze a specific commit
    python manage.py analyze_commits --commit abc123
    
    # Scan recent commits (last 7 days)
    python manage.py analyze_commits
    
    # Scan commits from last 30 days
    python manage.py analyze_commits --days 30
    
    # Check working directory for drift (pre-commit check)
    python manage.py analyze_commits --check-staged
    
    # Show drift issues only
    python manage.py analyze_commits --drift-only
    
    # Quiet mode (for git hooks)
    python manage.py analyze_commits --commit abc123 --quiet
"""

from django.core.management.base import BaseCommand

from apps.ai_assistant.models import GitEvent, SchemaDrift
from apps.ai_assistant.services.watch_git import GitObserver


class Command(BaseCommand):
    help = 'Analyze git commits for schema drift and code patterns'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--commit',
            help='Specific commit hash to analyze',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to scan (default: 7)',
        )
        parser.add_argument(
            '--check-staged',
            action='store_true',
            help='Check staged files for drift (pre-commit check)',
        )
        parser.add_argument(
            '--drift-only',
            action='store_true',
            help='Show only drift issues, skip clean commits',
        )
        parser.add_argument(
            '--quiet', '-q',
            action='store_true',
            help='Quiet mode - only show errors',
        )
    
    def handle(self, *args, **options):
        observer = GitObserver()
        quiet = options['quiet']
        drift_only = options['drift_only']
        
        if options['check_staged']:
            self._check_staged(observer, quiet)
        elif options['commit']:
            self._analyze_single(observer, options['commit'], quiet)
        else:
            self._scan_recent(observer, options['days'], drift_only, quiet)
    
    def _analyze_single(self, observer: GitObserver, commit_hash: str, quiet: bool):
        """Analyze a single commit."""
        event = observer.analyze_commit(commit_hash)
        
        if not event:
            if not quiet:
                self.stderr.write(f"Could not analyze commit: {commit_hash}")
            return
        
        if quiet:
            # In quiet mode, only output if there are issues
            if event.has_drift_issues:
                for drift in event.drift_records.all():
                    self.stderr.write(
                        f"DRIFT [{drift.severity.upper()}] {drift.file_path}:{drift.line_number or '?'} - {drift.description}"
                    )
            return
        
        # Normal output
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"Commit: {event.commit_hash[:8]}")
        self.stdout.write(f"Author: {event.author_name} <{event.author_email}>")
        self.stdout.write(f"Date:   {event.committed_at}")
        self.stdout.write(f"Type:   {event.commit_type}")
        self.stdout.write(f"\n    {event.message}")
        
        if event.files_added:
            self.stdout.write(f"\nAdded:    {', '.join(event.files_added)}")
        if event.files_modified:
            self.stdout.write(f"Modified: {', '.join(event.files_modified)}")
        if event.files_deleted:
            self.stdout.write(f"Deleted:  {', '.join(event.files_deleted)}")
        
        self.stdout.write(f"\nStats: +{event.lines_added} -{event.lines_deleted}")
        
        if event.apps_touched:
            self.stdout.write(f"Apps:   {', '.join(event.apps_touched)}")
        if event.models_touched:
            self.stdout.write(f"Models: {', '.join(event.models_touched)}")
        
        if event.has_drift_issues:
            self.stdout.write(self.style.WARNING(f"\n⚠️  DRIFT ISSUES DETECTED:"))
            for drift in event.drift_records.all():
                severity_style = (
                    self.style.ERROR if drift.severity == 'error'
                    else self.style.WARNING
                )
                self.stdout.write(severity_style(
                    f"  [{drift.severity.upper()}] {drift.file_path}:{drift.line_number or '?'}"
                ))
                self.stdout.write(f"    {drift.description}")
                if drift.fix_suggestion:
                    self.stdout.write(self.style.SUCCESS(f"    Fix: {drift.fix_suggestion}"))
        else:
            self.stdout.write(self.style.SUCCESS("\n✓ No drift issues detected"))
    
    def _scan_recent(
        self, 
        observer: GitObserver, 
        days: int, 
        drift_only: bool,
        quiet: bool
    ):
        """Scan recent commits."""
        if not quiet:
            self.stdout.write(f"Scanning commits from last {days} days...")
        
        drifts = observer.scan_recent_commits(days=days)
        
        if quiet:
            for drift in drifts:
                self.stderr.write(
                    f"DRIFT [{drift.severity.upper()}] {drift.file_path}:{drift.line_number or '?'} - {drift.description}"
                )
            return
        
        # Get recent events
        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(days=days)
        events = GitEvent.objects.filter(committed_at__gte=cutoff)
        
        self.stdout.write(f"\nFound {events.count()} commits")
        
        drift_count = events.filter(has_drift_issues=True).count()
        if drift_count:
            self.stdout.write(self.style.WARNING(f"⚠️  {drift_count} commits with drift issues"))
        
        for event in events:
            if drift_only and not event.has_drift_issues:
                continue
            
            status = '⚠️ ' if event.has_drift_issues else '✓ '
            self.stdout.write(
                f"{status}{event.commit_hash[:8]} {event.committed_at.strftime('%Y-%m-%d')} "
                f"[{event.commit_type}] {event.message[:50]}"
            )
            
            if event.has_drift_issues:
                for drift in event.drift_records.all():
                    self.stdout.write(self.style.WARNING(
                        f"    [{drift.severity}] {drift.file_path}: {drift.description}"
                    ))
        
        # Summary
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"Total commits: {events.count()}")
        self.stdout.write(f"With issues:   {drift_count}")
        
        if drifts:
            self.stdout.write(self.style.WARNING(
                f"\nUnresolved drift issues: {SchemaDrift.objects.filter(is_resolved=False).count()}"
            ))
    
    def _check_staged(self, observer: GitObserver, quiet: bool):
        """Check staged files for drift issues."""
        import subprocess
        
        # Get staged files
        result = subprocess.run(
            ['git', 'diff', '--cached', '--name-only'],
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            if not quiet:
                self.stderr.write("Could not get staged files")
            return
        
        staged_files = [f for f in result.stdout.strip().split('\n') if f]
        
        if not staged_files:
            if not quiet:
                self.stdout.write("No staged files to check")
            return
        
        if not quiet:
            self.stdout.write(f"Checking {len(staged_files)} staged files...")
        
        all_issues = []
        for file_path in staged_files:
            if file_path.endswith('.py'):
                issues = observer.check_file_for_drift(file_path)
                all_issues.extend(issues)
        
        if all_issues:
            if not quiet:
                self.stdout.write(self.style.ERROR(f"\n⚠️  Found {len(all_issues)} drift issues:"))
            
            for issue in all_issues:
                msg = f"[{issue['severity'].upper()}] {issue['file']}:{issue.get('line', '?')} - {issue['description']}"
                if quiet:
                    self.stderr.write(msg)
                else:
                    style = self.style.ERROR if issue['severity'] == 'error' else self.style.WARNING
                    self.stdout.write(style(f"  {msg}"))
                    if issue.get('fix'):
                        self.stdout.write(self.style.SUCCESS(f"    Fix: {issue['fix']}"))
            
            # Exit with error code to block commit if there are errors
            error_issues = [i for i in all_issues if i['severity'] == 'error']
            if error_issues:
                raise SystemExit(1)
        else:
            if not quiet:
                self.stdout.write(self.style.SUCCESS("✓ No drift issues in staged files"))
