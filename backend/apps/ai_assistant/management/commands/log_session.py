"""
Management command to log coding sessions.

Usage:
    # Interactive mode (prompts for details)
    python manage.py log_session
    
    # Quick log with args
    python manage.py log_session --type bugfix --problem "Order totals not updating"
    
    # Full log
    python manage.py log_session \\
        --type feature \\
        --problem "Need LLM to learn from coding sessions" \\
        --solution "Created CodingSession model and CodingJournal service" \\
        --learnings "Can reuse InventoryEvent patterns for other domains" \\
        --apps transactions products \\
        --tags "ai,observer,journal"
"""
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'Log a coding session to the journal'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type', '-t',
            choices=['feature', 'bugfix', 'refactor', 'test', 'docs', 'devops', 'debug', 'exploration', 'review'],
            help='Session type',
        )
        parser.add_argument(
            '--problem', '-p',
            type=str,
            help='What problem was being solved',
        )
        parser.add_argument(
            '--solution', '-s',
            type=str,
            help='How it was solved',
        )
        parser.add_argument(
            '--learnings', '-l',
            type=str,
            help='Key takeaways and learnings',
        )
        parser.add_argument(
            '--apps', '-a',
            nargs='+',
            help='Django apps touched (space-separated)',
        )
        parser.add_argument(
            '--models', '-m',
            nargs='+',
            help='Models touched (space-separated)',
        )
        parser.add_argument(
            '--files', '-f',
            nargs='+',
            help='Files changed (space-separated)',
        )
        parser.add_argument(
            '--tags',
            type=str,
            help='Tags (comma-separated)',
        )
        parser.add_argument(
            '--conversation',
            type=str,
            help='Path to file containing conversation log',
        )
        parser.add_argument(
            '--interactive', '-i',
            action='store_true',
            help='Interactive mode (prompts for all fields)',
        )

    def handle(self, *args, **options):
        from apps.ai_assistant.services.journal import CodingJournal
        
        journal = CodingJournal()
        
        # Interactive mode
        if options['interactive'] or not options['type']:
            self._interactive_mode(journal)
            return
        
        # Parse tags
        tags = []
        if options['tags']:
            tags = [t.strip() for t in options['tags'].split(',')]
        
        # Read conversation log if provided
        conversation_log = ''
        if options['conversation']:
            try:
                with open(options['conversation'], 'r') as f:
                    conversation_log = f.read()
            except Exception as e:
                self.stderr.write(f"Could not read conversation file: {e}")
        
        # Log the session
        session = journal.log_session(
            session_type=options['type'],
            problem=options['problem'] or '',
            solution=options['solution'] or '',
            learnings=options['learnings'] or '',
            apps=options['apps'] or [],
            models_touched=options['models'] or [],
            files_changed=options['files'] or [],
            tags=tags,
            conversation_log=conversation_log,
        )
        
        self.stdout.write(self.style.SUCCESS(
            f"Session logged: {session.session_id}"
        ))
        
        if session.llm_summary:
            self.stdout.write(f"\nSummary: {session.llm_summary}")
    
    def _interactive_mode(self, journal):
        """Interactive prompts for session details."""
        self.stdout.write(self.style.HTTP_INFO("\n=== Log Coding Session ===\n"))
        
        # Session type
        types = ['feature', 'bugfix', 'refactor', 'test', 'docs', 'devops', 'debug', 'exploration', 'review']
        self.stdout.write("Session types: " + ", ".join(f"{i+1}={t}" for i, t in enumerate(types)))
        type_input = input("Session type [1-9 or name]: ").strip()
        
        try:
            type_idx = int(type_input) - 1
            session_type = types[type_idx]
        except (ValueError, IndexError):
            session_type = type_input if type_input in types else 'exploration'
        
        # Problem
        self.stdout.write("")
        problem = input("Problem (what were you trying to solve?): ").strip()
        
        # Solution
        self.stdout.write("")
        solution = input("Solution (how did you solve it?): ").strip()
        
        # Learnings
        self.stdout.write("")
        learnings = input("Learnings (key takeaways?): ").strip()
        
        # Apps
        self.stdout.write("")
        apps_input = input("Apps touched (space-separated): ").strip()
        apps = apps_input.split() if apps_input else []
        
        # Tags
        self.stdout.write("")
        tags_input = input("Tags (comma-separated): ").strip()
        tags = [t.strip() for t in tags_input.split(',')] if tags_input else []
        
        # Multi-line conversation log
        self.stdout.write("")
        self.stdout.write("Conversation log (paste below, then Ctrl+D or empty line to finish):")
        
        conversation_lines = []
        try:
            while True:
                line = input()
                if not line:
                    break
                conversation_lines.append(line)
        except EOFError:
            pass
        
        conversation_log = '\n'.join(conversation_lines)
        
        # Confirm
        self.stdout.write("")
        self.stdout.write(self.style.WARNING("Session to log:"))
        self.stdout.write(f"  Type: {session_type}")
        self.stdout.write(f"  Problem: {problem[:80]}...")
        self.stdout.write(f"  Solution: {solution[:80]}...")
        self.stdout.write(f"  Apps: {apps}")
        self.stdout.write(f"  Tags: {tags}")
        self.stdout.write(f"  Conversation: {len(conversation_log)} chars")
        
        confirm = input("\nSave? [Y/n]: ").strip().lower()
        if confirm and confirm != 'y':
            self.stdout.write(self.style.ERROR("Cancelled"))
            return
        
        # Log it
        session = journal.log_session(
            session_type=session_type,
            problem=problem,
            solution=solution,
            learnings=learnings,
            apps=apps,
            tags=tags,
            conversation_log=conversation_log,
        )
        
        self.stdout.write(self.style.SUCCESS(
            f"\nSession logged: {session.session_id}"
        ))
        
        if session.llm_summary:
            self.stdout.write(f"\nLLM Summary:\n{session.llm_summary}")
