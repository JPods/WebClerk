"""
Management command for coding journal Q&A and queries.

Usage:
    # Ask a question
    python manage.py journal ask "How did we fix the order totals issue?"
    
    # Find similar sessions
    python manage.py journal find "signal post_delete"
    
    # Show recent sessions
    python manage.py journal recent --days 7
    
    # Show stats
    python manage.py journal stats
    
    # Log an error fix
    python manage.py journal error "TypeError: cannot unpack non-iterable NoneType" \\
        --cause "Function returning None" \\
        --fix "Added default return value"
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Query the coding journal'

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='action', help='Action to perform')
        
        # Ask subcommand
        ask_parser = subparsers.add_parser('ask', help='Ask a question about coding history')
        ask_parser.add_argument('question', type=str, help='Your question')
        
        # Find subcommand
        find_parser = subparsers.add_parser('find', help='Find similar sessions')
        find_parser.add_argument('query', type=str, help='Search query')
        find_parser.add_argument('--limit', '-n', type=int, default=5, help='Max results')
        
        # Recent subcommand
        recent_parser = subparsers.add_parser('recent', help='Show recent sessions')
        recent_parser.add_argument('--days', '-d', type=int, default=7, help='Days to look back')
        recent_parser.add_argument('--type', '-t', type=str, help='Filter by session type')
        
        # Stats subcommand
        stats_parser = subparsers.add_parser('stats', help='Show session statistics')
        stats_parser.add_argument('--days', '-d', type=int, default=30, help='Days to analyze')
        
        # Error subcommand
        error_parser = subparsers.add_parser('error', help='Log or find an error pattern')
        error_parser.add_argument('error_text', type=str, help='The error message')
        error_parser.add_argument('--cause', type=str, help='Root cause (if logging)')
        error_parser.add_argument('--fix', type=str, help='The fix (if logging)')
        error_parser.add_argument('--category', type=str, default='runtime', help='Error category')

    def handle(self, *args, **options):
        from apps.ai_assistant.services.coding_journal import CodingJournal
        
        journal = CodingJournal()
        action = options.get('action')
        
        if action == 'ask':
            self._handle_ask(journal, options)
        elif action == 'find':
            self._handle_find(journal, options)
        elif action == 'recent':
            self._handle_recent(journal, options)
        elif action == 'stats':
            self._handle_stats(journal, options)
        elif action == 'error':
            self._handle_error(journal, options)
        else:
            self.stdout.write(self.style.WARNING(
                "Usage: python manage.py journal <ask|find|recent|stats|error>"
            ))
    
    def _handle_ask(self, journal, options):
        """Handle the ask subcommand."""
        question = options['question']
        self.stdout.write(f"Thinking...\n")
        
        answer = journal.ask(question)
        
        self.stdout.write(self.style.SUCCESS("Answer:"))
        self.stdout.write(answer)
    
    def _handle_find(self, journal, options):
        """Handle the find subcommand."""
        query = options['query']
        limit = options['limit']
        
        results = journal.find_similar(query, limit=limit)
        
        if not results:
            self.stdout.write(self.style.WARNING("No matching sessions found."))
            return
        
        self.stdout.write(self.style.SUCCESS(f"Found {len(results)} sessions:\n"))
        
        for i, session in enumerate(results, 1):
            self.stdout.write(self.style.HTTP_INFO(f"─── Session {i} ───"))
            self.stdout.write(f"Type: {session['type']}")
            self.stdout.write(f"Date: {session['started_at'][:10]}")
            self.stdout.write(f"Problem: {session['problem']}")
            if session['solution']:
                self.stdout.write(f"Solution: {session['solution']}")
            if session['learnings']:
                self.stdout.write(f"Learnings: {session['learnings']}")
            if session['tags']:
                self.stdout.write(f"Tags: {', '.join(session['tags'])}")
            self.stdout.write("")
    
    def _handle_recent(self, journal, options):
        """Handle the recent subcommand."""
        days = options['days']
        session_type = options.get('type')
        
        sessions = journal.get_recent_sessions(days=days, session_type=session_type)
        
        if not sessions:
            self.stdout.write(self.style.WARNING(f"No sessions in the last {days} days."))
            return
        
        self.stdout.write(self.style.SUCCESS(f"Sessions in the last {days} days:\n"))
        
        for session in sessions:
            type_style = {
                'feature': self.style.SUCCESS,
                'bugfix': self.style.ERROR,
                'refactor': self.style.WARNING,
                'test': self.style.HTTP_INFO,
            }.get(session['type'], self.style.NOTICE)
            
            self.stdout.write(
                f"{session['started_at'][:10]} "
                f"[{type_style(session['type'].upper())}] "
                f"{session['problem']}"
            )
            if session['summary']:
                self.stdout.write(f"    {session['summary']}")
            self.stdout.write("")
    
    def _handle_stats(self, journal, options):
        """Handle the stats subcommand."""
        days = options['days']
        
        stats = journal.get_session_stats(days=days)
        
        self.stdout.write(self.style.SUCCESS(f"Coding Journal Stats ({days} days)\n"))
        
        self.stdout.write(f"Total Sessions: {stats['total_sessions']}")
        self.stdout.write("")
        
        self.stdout.write("By Type:")
        for session_type, count in stats['by_type'].items():
            bar = '█' * min(count, 20)
            self.stdout.write(f"  {session_type:12} {bar} ({count})")
        
        self.stdout.write("")
        self.stdout.write("Top Tags:")
        for tag, count in list(stats['top_tags'].items())[:10]:
            self.stdout.write(f"  {tag}: {count}")
        
        if stats['common_errors']:
            self.stdout.write("")
            self.stdout.write("Common Errors:")
            for err in stats['common_errors']:
                self.stdout.write(f"  [{err['count']}x] {err['error']}")
    
    def _handle_error(self, journal, options):
        """Handle the error subcommand."""
        error_text = options['error_text']
        
        # If cause and fix provided, log it. Otherwise, look it up.
        if options.get('cause') and options.get('fix'):
            pattern = journal.log_error_fix(
                error_text=error_text,
                cause=options['cause'],
                fix=options['fix'],
                category=options.get('category', 'runtime'),
            )
            self.stdout.write(self.style.SUCCESS(
                f"Error pattern logged: {pattern.pattern_id}"
            ))
        else:
            # Look up existing fix
            result = journal.find_error_fix(error_text)
            
            if result:
                self.stdout.write(self.style.SUCCESS("Found error pattern:\n"))
                self.stdout.write(f"Category: {result['category']}")
                self.stdout.write(f"Error: {result['error']}")
                self.stdout.write(f"Cause: {result['cause']}")
                self.stdout.write(self.style.SUCCESS(f"Fix: {result['fix']}"))
                if result['prevention']:
                    self.stdout.write(f"Prevention: {result['prevention']}")
                self.stdout.write(f"\nSeen {result['occurrences']} times, last: {result['last_seen'][:10]}")
            else:
                self.stdout.write(self.style.WARNING(
                    "No matching error pattern found.\n"
                    "To log a new pattern, provide --cause and --fix"
                ))
