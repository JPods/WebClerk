"""
Coding Journal — Captures development sessions for LLM learning.

This service logs our coding sessions so the LLM can learn from:
- What problems we solve and how
- Error patterns and their fixes
- Design decisions and rationale
- Workflows and habits

Usage:
    from apps.ai_assistant.services.journal import CodingJournal
    
    journal = CodingJournal()
    
    # Log a session
    session = journal.log_session(
        session_type='bugfix',
        problem="Order totals not updating after line delete",
        solution="Added post_delete signal to recalculate totals",
        learnings="Always wire both post_save and post_delete for totals",
        files_changed=['apps/transactions/signals.py'],
        apps=['transactions'],
        tags=['signals', 'totals', 'order'],
    )
    
    # Log an error fix
    journal.log_error_fix(
        session=session,
        error_text="TypeError: cannot unpack non-iterable NoneType object",
        cause="Function returning None instead of tuple",
        fix="Added default return value: return (0, 0)",
    )
    
    # Query for similar sessions
    results = journal.find_similar("order total calculation issue")
"""
from __future__ import annotations

import logging
import subprocess
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from django.db.models import Count, Q
from django.utils import timezone

if TYPE_CHECKING:
    from apps.ai_assistant.models import CodingSession, ErrorPattern

logger = logging.getLogger(__name__)


class CodingJournal:
    """
    Service for logging and querying development sessions.
    Builds institutional knowledge from our coding efforts.
    """
    
    def __init__(self):
        self._llm_observer = None
    
    def _get_observer(self):
        """Lazy load LLM observer for summarization."""
        if self._llm_observer is None:
            from apps.ai_assistant.services.llm_observer import LLMInventoryObserver
            self._llm_observer = LLMInventoryObserver()
        return self._llm_observer
    
    # ─────────────────────────────────────────────────────────────────
    # Session Logging
    # ─────────────────────────────────────────────────────────────────
    
    def log_session(
        self,
        session_type: str,
        *,
        problem: str = '',
        solution: str = '',
        learnings: str = '',
        files_changed: list | None = None,
        apps: list | None = None,
        models_touched: list | None = None,
        tags: list | None = None,
        conversation_log: str = '',
        started_at: datetime | None = None,
        ended_at: datetime | None = None,
    ) -> 'CodingSession':
        """
        Log a development session.
        
        Args:
            session_type: Type of session (feature, bugfix, refactor, etc.)
            problem: What problem was being solved
            solution: How it was solved
            learnings: Key takeaways
            files_changed: List of file paths modified
            apps: Django apps touched
            models_touched: Model names touched
            tags: Semantic tags for categorization
            conversation_log: Raw AI conversation (optional)
            started_at: When session started (defaults to now)
            ended_at: When session ended (defaults to now)
            
        Returns:
            CodingSession instance
        """
        from apps.ai_assistant.models import CodingSession
        
        now = timezone.now()
        
        session = CodingSession.objects.create(
            session_type=session_type,
            problem=problem,
            solution=solution,
            learnings=learnings,
            files_changed=files_changed or [],
            apps=apps or [],
            models_touched=models_touched or [],
            tags=tags or [],
            conversation_log=conversation_log,
            started_at=started_at or now,
            ended_at=ended_at or now,
            git_commits=self._get_recent_commits(),
        )
        
        # Generate LLM summary
        self._summarize_session(session)
        
        return session
    
    def log_error_fix(
        self,
        error_text: str,
        cause: str,
        fix: str,
        *,
        session: 'CodingSession | None' = None,
        category: str = 'runtime',
        prevention: str = '',
        related_files: list | None = None,
        tags: list | None = None,
    ) -> 'ErrorPattern':
        """
        Log an error and its fix.
        
        Either adds to an existing pattern or creates a new one.
        Also records in the session's error_fixes if provided.
        
        Args:
            error_text: The error message
            cause: Root cause explanation
            fix: How to fix it
            session: Optional session to attach to
            category: Error category (import, type, runtime, etc.)
            prevention: How to prevent in future
            related_files: Files commonly involved
            tags: Semantic tags
            
        Returns:
            ErrorPattern instance (new or updated)
        """
        from apps.ai_assistant.models import ErrorPattern
        
        # Check for existing pattern
        pattern = self._find_similar_error(error_text)
        
        if pattern:
            # Update existing pattern
            pattern.occurrences += 1
            pattern.last_seen = timezone.now()
            if prevention and not pattern.prevention:
                pattern.prevention = prevention
            pattern.save(update_fields=['occurrences', 'last_seen', 'prevention'])
        else:
            # Create new pattern
            pattern = ErrorPattern.objects.create(
                error_text=error_text,
                category=category,
                cause=cause,
                fix=fix,
                prevention=prevention,
                related_files=related_files or [],
                tags=tags or [],
            )
        
        # Record in session
        if session:
            session.errors_encountered = session.errors_encountered + [error_text]
            session.error_fixes[error_text[:100]] = fix
            session.save(update_fields=['errors_encountered', 'error_fixes'])
        
        return pattern
    
    # ─────────────────────────────────────────────────────────────────
    # Session Queries
    # ─────────────────────────────────────────────────────────────────
    
    def find_similar(self, query: str, limit: int = 5) -> list[dict]:
        """
        Find sessions similar to the query using keyword matching.
        
        Args:
            query: Natural language description of what you're looking for
            limit: Maximum results to return
            
        Returns:
            List of session dicts with relevance scores
        """
        from apps.ai_assistant.models import CodingSession
        
        # Extract keywords from query
        keywords = self._extract_keywords(query)
        
        if not keywords:
            return []
        
        # Build Q objects for each keyword
        q_objects = Q()
        for keyword in keywords:
            q_objects |= (
                Q(problem__icontains=keyword) |
                Q(solution__icontains=keyword) |
                Q(learnings__icontains=keyword) |
                Q(tags__contains=[keyword]) |
                Q(apps__contains=[keyword]) |
                Q(llm_summary__icontains=keyword)
            )
        
        sessions = CodingSession.objects.filter(q_objects).order_by('-started_at')[:limit]
        
        results = []
        for session in sessions:
            results.append({
                'session_id': str(session.session_id),
                'type': session.session_type,
                'problem': session.problem,
                'solution': session.solution,
                'learnings': session.learnings,
                'summary': session.llm_summary,
                'started_at': session.started_at.isoformat(),
                'tags': session.tags,
            })
        
        return results
    
    def find_error_fix(self, error_text: str) -> dict | None:
        """
        Find a fix for an error based on known patterns.
        
        Args:
            error_text: The error message to look up
            
        Returns:
            Dict with cause, fix, prevention if found
        """
        pattern = self._find_similar_error(error_text)
        
        if pattern:
            return {
                'error': pattern.error_text,
                'category': pattern.category,
                'cause': pattern.cause,
                'fix': pattern.fix,
                'prevention': pattern.prevention,
                'occurrences': pattern.occurrences,
                'last_seen': pattern.last_seen.isoformat(),
                'related_files': pattern.related_files,
            }
        
        return None
    
    def get_recent_sessions(self, days: int = 7, session_type: str | None = None) -> list[dict]:
        """
        Get recent coding sessions.
        
        Args:
            days: Number of days to look back
            session_type: Optional filter by session type
            
        Returns:
            List of session summaries
        """
        from apps.ai_assistant.models import CodingSession
        
        since = timezone.now() - timedelta(days=days)
        
        queryset = CodingSession.objects.filter(started_at__gte=since)
        if session_type:
            queryset = queryset.filter(session_type=session_type)
        
        return [
            {
                'session_id': str(s.session_id),
                'type': s.session_type,
                'problem': s.problem[:100],
                'summary': s.llm_summary[:200] if s.llm_summary else '',
                'started_at': s.started_at.isoformat(),
                'apps': s.apps,
                'tags': s.tags,
            }
            for s in queryset.order_by('-started_at')[:20]
        ]
    
    def get_session_stats(self, days: int = 30) -> dict:
        """
        Get statistics about coding sessions.
        
        Returns:
            Dict with session counts by type, common tags, etc.
        """
        from apps.ai_assistant.models import CodingSession, ErrorPattern
        
        since = timezone.now() - timedelta(days=days)
        
        sessions = CodingSession.objects.filter(started_at__gte=since)
        
        by_type = (
            sessions
            .values('session_type')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        
        # Flatten tags
        all_tags = []
        for s in sessions.values_list('tags', flat=True):
            all_tags.extend(s or [])
        
        tag_counts = {}
        for tag in all_tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        top_tags = sorted(tag_counts.items(), key=lambda x: -x[1])[:10]
        
        error_patterns = ErrorPattern.objects.order_by('-occurrences')[:5]
        
        return {
            'period_days': days,
            'total_sessions': sessions.count(),
            'by_type': {item['session_type']: item['count'] for item in by_type},
            'top_tags': dict(top_tags),
            'common_errors': [
                {'error': e.error_text[:80], 'count': e.occurrences}
                for e in error_patterns
            ],
        }
    
    # ─────────────────────────────────────────────────────────────────
    # Q&A Interface
    # ─────────────────────────────────────────────────────────────────
    
    def ask(self, question: str) -> str:
        """
        Ask a question about our coding history.
        
        Args:
            question: Natural language question
            
        Returns:
            LLM-generated answer based on session history
        """
        from apps.ai_assistant.models import CodingSession, ErrorPattern
        
        # Gather context
        context_parts = []
        
        # Check for error-related questions
        question_lower = question.lower()
        if any(word in question_lower for word in ['error', 'fix', 'bug', 'issue', 'problem']):
            # Pull recent error patterns
            patterns = ErrorPattern.objects.order_by('-last_seen')[:5]
            if patterns:
                context_parts.append("Recent Error Patterns:")
                for p in patterns:
                    context_parts.append(f"- {p.category}: {p.error_text[:60]}")
                    context_parts.append(f"  Fix: {p.fix[:100]}")
        
        # Find relevant sessions
        similar = self.find_similar(question, limit=5)
        if similar:
            context_parts.append("\nRelevant Past Sessions:")
            for s in similar:
                context_parts.append(f"- [{s['type']}] {s['problem'][:80]}")
                if s['solution']:
                    context_parts.append(f"  Solution: {s['solution'][:100]}")
                if s['learnings']:
                    context_parts.append(f"  Learning: {s['learnings'][:100]}")
        
        # Get stats
        stats = self.get_session_stats(days=30)
        context_parts.append(f"\nRecent Activity (30 days):")
        context_parts.append(f"- Total sessions: {stats['total_sessions']}")
        context_parts.append(f"- By type: {stats['by_type']}")
        
        context = "\n".join(context_parts)
        
        prompt = f"""You are a coding assistant with knowledge of our development history.
Answer this question based on our past coding sessions and error patterns.

Question: {question}

Context from our coding journal:
{context}

Provide a helpful answer. If you can't answer from the available data, suggest what might help."""

        try:
            observer = self._get_observer()
            client = observer._get_client()
            return client.generate(prompt)
        except Exception as e:
            logger.error(f"LLM Q&A failed: {e}")
            # Return plain context as fallback
            return f"Unable to generate answer. Here's what I found:\n\n{context}"
    
    # ─────────────────────────────────────────────────────────────────
    # Private Helpers
    # ─────────────────────────────────────────────────────────────────
    
    def _summarize_session(self, session: 'CodingSession') -> None:
        """Generate LLM summary for a session."""
        if not session.problem and not session.solution:
            return
        
        prompt = f"""Summarize this coding session in 2-3 sentences:

Type: {session.session_type}
Problem: {session.problem}
Solution: {session.solution}
Learnings: {session.learnings}
Apps: {session.apps}
Files: {session.files_changed[:5] if session.files_changed else []}

Focus on the key technical insight that would help someone facing a similar issue."""

        try:
            observer = self._get_observer()
            client = observer._get_client()
            session.llm_summary = client.generate(prompt).strip()
            session.llm_processed_at = timezone.now()
            session.save(update_fields=['llm_summary', 'llm_processed_at'])
        except Exception as e:
            logger.debug(f"Session summarization failed: {e}")
    
    def _find_similar_error(self, error_text: str) -> 'ErrorPattern | None':
        """Find an existing error pattern that matches."""
        from apps.ai_assistant.models import ErrorPattern
        
        # Normalize error text
        normalized = error_text.strip().lower()
        
        # Try exact match first
        pattern = ErrorPattern.objects.filter(
            error_text__iexact=error_text.strip()
        ).first()
        
        if pattern:
            return pattern
        
        # Try substring match on the first line
        first_line = error_text.strip().split('\n')[0]
        return ErrorPattern.objects.filter(
            error_text__icontains=first_line[:80]
        ).first()
    
    def _extract_keywords(self, text: str) -> list[str]:
        """Extract keywords from text for search."""
        # Simple keyword extraction - filter stopwords
        stopwords = {
            'a', 'an', 'the', 'is', 'was', 'were', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'shall',
            'and', 'but', 'or', 'nor', 'for', 'yet', 'so',
            'in', 'on', 'at', 'to', 'from', 'by', 'with', 'about',
            'into', 'through', 'during', 'before', 'after',
            'above', 'below', 'between', 'under', 'again',
            'it', 'its', 'this', 'that', 'these', 'those',
            'i', 'me', 'my', 'we', 'our', 'you', 'your', 'he', 'she',
            'how', 'what', 'when', 'where', 'why', 'which', 'who',
            'not', 'no', 'can', 'cannot',
        }
        
        words = text.lower().split()
        keywords = [
            w.strip('.,!?;:()[]{}"\'-')
            for w in words
            if w.strip('.,!?;:()[]{}"\'-') not in stopwords
            and len(w.strip('.,!?;:()[]{}"\'-')) > 2
        ]
        
        return keywords[:10]  # Limit to top 10 keywords
    
    def _get_recent_commits(self, hours: int = 4) -> list[str]:
        """Get git commit hashes from the recent period."""
        try:
            result = subprocess.run(
                ['git', 'log', f'--since={hours} hours ago', '--format=%H', '--max-count=20'],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[:20]
        except Exception:
            pass
        return []
