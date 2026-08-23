"""
Git Observer Service — Learns from code changes, detects schema drift.

Watches git commits to:
- Track file co-change patterns
- Detect deprecated field/API usage
- Alert on outdated code patterns
- Learn from commit messages

Usage:
    from apps.ai_assistant.services.git_observer import GitObserver
    
    observer = GitObserver()
    
    # Analyze a specific commit
    event = observer.analyze_commit('abc123')
    
    # Check recent commits for drift
    issues = observer.scan_recent_commits(days=7)
    
    # Get co-change patterns
    patterns = observer.get_cochange_patterns('apps/inventory/models.py')
"""

import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from django.db import models as db_models
from django.utils import timezone

from apps.ai_assistant.models import GitEvent, SchemaDrift


# =============================================================================
# DRIFT DETECTION RULES
# =============================================================================

# Deprecated field names → current names
DEPRECATED_FIELDS = {
    'quantity.placed': 'quantity.staged',
    'quantity_placed': 'quantity_staged',
    'qtyPlaced': 'qtyStaged',
    'qty_placed': 'qty_staged',
    'placedQty': 'stagedQty',
    'placed_qty': 'staged_qty',
    # Add more as they arise
}

# Banned patterns (regex → description)
BANNED_PATTERNS = {
    r'from\s+rest_framework\.serializers\s+import\s+Serializer\b': 
        'Use ModelSerializer or BaseSerializer, not bare Serializer',
    r'\.save\(\s*commit\s*=\s*False\s*\)': 
        'Prefer atomic transactions over commit=False',
    r'print\s*\(': 
        'Use logging instead of print statements',
}

# File patterns that suggest schema changes
SCHEMA_FILES = [
    r'apps/\w+/models\.py$',
    r'apps/\w+/migrations/\d+_.*\.py$',
]


class GitObserver:
    """
    Observes git activity, detects drift, learns patterns.
    """
    
    def __init__(self, repo_path: str | None = None):
        """
        Initialize observer.
        
        Args:
            repo_path: Path to git repository (defaults to current directory)
        """
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
    
    # -------------------------------------------------------------------------
    # COMMIT ANALYSIS
    # -------------------------------------------------------------------------
    
    def analyze_commit(self, commit_hash: str) -> GitEvent | None:
        """
        Analyze a commit and store as GitEvent.
        
        Args:
            commit_hash: Full or short commit hash
            
        Returns:
            GitEvent record (created or existing)
        """
        # Check if already recorded
        existing = GitEvent.objects.filter(
            commit_hash__startswith=commit_hash[:7]
        ).first()
        if existing:
            return existing
        
        # Get commit info
        info = self._get_commit_info(commit_hash)
        if not info:
            return None
        
        # Get file changes
        files = self._get_commit_files(commit_hash)
        
        # Classify commit type
        commit_type = self._classify_commit(info['message'], files)
        
        # Infer apps/models touched
        apps_touched = self._extract_apps(files)
        models_touched = self._extract_models(files)
        
        # Create event
        event = GitEvent.objects.create(
            commit_hash=info['hash'],
            committed_at=info['date'],
            author_name=info['author_name'],
            author_email=info['author_email'],
            message=info['message'],
            branch=info.get('branch', ''),
            files_added=files.get('added', []),
            files_modified=files.get('modified', []),
            files_deleted=files.get('deleted', []),
            lines_added=info.get('additions', 0),
            lines_deleted=info.get('deletions', 0),
            commit_type=commit_type,
            apps_touched=apps_touched,
            models_touched=models_touched,
        )
        
        # Check for drift issues
        drift_issues = self._detect_drift_in_commit(commit_hash, files)
        if drift_issues:
            event.has_drift_issues = True
            event.drift_issues = drift_issues
            event.save()
            
            # Create SchemaDrift records
            for issue in drift_issues:
                SchemaDrift.objects.create(
                    git_event=event,
                    file_path=issue['file'],
                    line_number=issue.get('line'),
                    drift_type=issue['type'],
                    severity=issue.get('severity', 'warning'),
                    description=issue['description'],
                    current_value=issue.get('found', ''),
                    expected_value=issue.get('expected', ''),
                    fix_suggestion=issue.get('fix', ''),
                )
        
        return event
    
    def scan_recent_commits(self, days: int = 7) -> list[SchemaDrift]:
        """
        Scan recent commits for drift issues.
        
        Args:
            days: How many days back to scan
            
        Returns:
            List of SchemaDrift records created
        """
        since = datetime.now() - timedelta(days=days)
        commits = self._get_commits_since(since)
        
        all_drifts = []
        for commit_hash in commits:
            event = self.analyze_commit(commit_hash)
            if event and event.has_drift_issues:
                all_drifts.extend(event.drift_records.all())
        
        return all_drifts
    
    # -------------------------------------------------------------------------
    # DRIFT DETECTION
    # -------------------------------------------------------------------------
    
    def _detect_drift_in_commit(
        self, 
        commit_hash: str, 
        files: dict[str, list[str]]
    ) -> list[dict[str, Any]]:
        """
        Check commit diff for drift issues.
        """
        issues = []
        
        # Get diff content
        all_files = (
            files.get('added', []) + 
            files.get('modified', [])
        )
        
        for file_path in all_files:
            # Skip non-Python files
            if not file_path.endswith('.py'):
                continue
            
            # Get diff for this file
            diff = self._get_file_diff(commit_hash, file_path)
            if not diff:
                continue
            
            # Check for deprecated fields
            for old_name, new_name in DEPRECATED_FIELDS.items():
                if old_name in diff:
                    # Find line number
                    line_num = self._find_line_in_diff(diff, old_name)
                    issues.append({
                        'type': 'deprecated_field',
                        'file': file_path,
                        'line': line_num,
                        'description': f"Uses deprecated field '{old_name}'",
                        'found': old_name,
                        'expected': new_name,
                        'fix': f"Replace '{old_name}' with '{new_name}'",
                        'severity': 'error',
                    })
            
            # Check for banned patterns
            for pattern, description in BANNED_PATTERNS.items():
                if re.search(pattern, diff):
                    line_num = self._find_pattern_line(diff, pattern)
                    issues.append({
                        'type': 'banned_pattern',
                        'file': file_path,
                        'line': line_num,
                        'description': description,
                        'severity': 'warning',
                    })
        
        return issues
    
    def check_file_for_drift(self, file_path: str) -> list[dict[str, Any]]:
        """
        Check a file's current content for drift issues.
        
        Useful for checking working directory before commit.
        """
        full_path = self.repo_path / file_path
        if not full_path.exists():
            return []
        
        content = full_path.read_text()
        issues = []
        
        # Check deprecated fields
        for old_name, new_name in DEPRECATED_FIELDS.items():
            matches = list(re.finditer(re.escape(old_name), content))
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                issues.append({
                    'type': 'deprecated_field',
                    'file': file_path,
                    'line': line_num,
                    'description': f"Uses deprecated field '{old_name}'",
                    'found': old_name,
                    'expected': new_name,
                    'fix': f"Replace '{old_name}' with '{new_name}'",
                    'severity': 'error',
                })
        
        # Check banned patterns
        for pattern, description in BANNED_PATTERNS.items():
            for match in re.finditer(pattern, content):
                line_num = content[:match.start()].count('\n') + 1
                issues.append({
                    'type': 'banned_pattern',
                    'file': file_path,
                    'line': line_num,
                    'description': description,
                    'severity': 'warning',
                })
        
        return issues
    
    # -------------------------------------------------------------------------
    # CO-CHANGE PATTERNS
    # -------------------------------------------------------------------------
    
    def get_cochange_patterns(
        self, 
        file_path: str, 
        limit: int = 10
    ) -> list[dict[str, Any]]:
        """
        Find files that frequently change together with given file.
        
        Args:
            file_path: File to find co-changes for
            limit: Max number of related files to return
            
        Returns:
            List of {file: str, count: int, pct: float}
        """
        # Get all commits touching this file
        events = GitEvent.objects.filter(
            db_models.Q(files_added__contains=[file_path]) |
            db_models.Q(files_modified__contains=[file_path])
        ).order_by('-committed_at')[:100]
        
        if not events:
            return []
        
        # Count co-occurrences
        cochange_counts: dict[str, int] = {}
        total_commits = len(events)
        
        for event in events:
            all_files = event.files_added + event.files_modified
            for other_file in all_files:
                if other_file != file_path:
                    cochange_counts[other_file] = cochange_counts.get(other_file, 0) + 1
        
        # Sort by frequency
        sorted_files = sorted(
            cochange_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        
        return [
            {
                'file': f,
                'count': count,
                'pct': round(100 * count / total_commits, 1),
            }
            for f, count in sorted_files
        ]
    
    # -------------------------------------------------------------------------
    # GIT COMMAND HELPERS
    # -------------------------------------------------------------------------
    
    def _run_git(self, *args: str) -> str | None:
        """Run git command and return output."""
        try:
            result = subprocess.run(
                ['git', *args],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None
    
    def _get_commit_info(self, commit_hash: str) -> dict[str, Any] | None:
        """Get commit metadata."""
        # Format: hash|author_name|author_email|date|subject
        fmt = '%H|%an|%ae|%aI|%s'
        output = self._run_git('log', '-1', f'--format={fmt}', commit_hash)
        if not output:
            return None
        
        parts = output.split('|', 4)
        if len(parts) < 5:
            return None
        
        # Get stats
        stat_output = self._run_git('log', '-1', '--format=', '--numstat', commit_hash)
        additions, deletions = 0, 0
        if stat_output:
            for line in stat_output.strip().split('\n'):
                if line:
                    parts_stat = line.split('\t')
                    if len(parts_stat) >= 2:
                        try:
                            additions += int(parts_stat[0]) if parts_stat[0] != '-' else 0
                            deletions += int(parts_stat[1]) if parts_stat[1] != '-' else 0
                        except ValueError:
                            pass
        
        return {
            'hash': parts[0],
            'author_name': parts[1],
            'author_email': parts[2],
            'date': datetime.fromisoformat(parts[3]),
            'message': parts[4],
            'additions': additions,
            'deletions': deletions,
        }
    
    def _get_commit_files(self, commit_hash: str) -> dict[str, list[str]]:
        """Get files changed in commit."""
        output = self._run_git(
            'diff-tree', '--no-commit-id', '--name-status', '-r', commit_hash
        )
        if not output:
            return {'added': [], 'modified': [], 'deleted': []}
        
        files: dict[str, list[str]] = {'added': [], 'modified': [], 'deleted': []}
        
        for line in output.strip().split('\n'):
            if not line:
                continue
            parts = line.split('\t', 1)
            if len(parts) != 2:
                continue
            
            status, file_path = parts
            if status.startswith('A'):
                files['added'].append(file_path)
            elif status.startswith('M'):
                files['modified'].append(file_path)
            elif status.startswith('D'):
                files['deleted'].append(file_path)
        
        return files
    
    def _get_file_diff(self, commit_hash: str, file_path: str) -> str | None:
        """Get diff for a specific file in a commit."""
        return self._run_git('show', f'{commit_hash}:{file_path}')
    
    def _get_commits_since(self, since: datetime) -> list[str]:
        """Get commit hashes since a date."""
        output = self._run_git(
            'log', 
            f'--since={since.isoformat()}',
            '--format=%H',
        )
        if not output:
            return []
        return output.strip().split('\n')
    
    def _find_line_in_diff(self, diff: str, text: str) -> int | None:
        """Find line number where text appears in diff."""
        for i, line in enumerate(diff.split('\n'), 1):
            if text in line:
                return i
        return None
    
    def _find_pattern_line(self, diff: str, pattern: str) -> int | None:
        """Find line number where pattern matches in diff."""
        for i, line in enumerate(diff.split('\n'), 1):
            if re.search(pattern, line):
                return i
        return None
    
    # -------------------------------------------------------------------------
    # CLASSIFICATION HELPERS
    # -------------------------------------------------------------------------
    
    def _classify_commit(
        self, 
        message: str, 
        files: dict[str, list[str]]
    ) -> str:
        """Classify commit type from message and files."""
        msg_lower = message.lower()
        
        # Check message prefixes (conventional commits)
        prefixes = {
            'feat': 'feature',
            'fix': 'bugfix',
            'bug': 'bugfix',
            'refactor': 'refactor',
            'docs': 'docs',
            'test': 'test',
            'chore': 'chore',
            'style': 'style',
            'perf': 'perf',
            'ci': 'ci',
        }
        for prefix, commit_type in prefixes.items():
            if msg_lower.startswith(f'{prefix}:') or msg_lower.startswith(f'{prefix}('):
                return commit_type
        
        # Infer from files
        all_files = files.get('added', []) + files.get('modified', [])
        
        if any('test' in f for f in all_files):
            return 'test'
        if any('readme' in f.lower() or f.endswith('.md') for f in all_files):
            return 'docs'
        if any('.yml' in f or '.yaml' in f or 'Dockerfile' in f for f in all_files):
            return 'ci'
        
        # Infer from message content
        if any(word in msg_lower for word in ['add', 'new', 'create', 'implement']):
            return 'feature'
        if any(word in msg_lower for word in ['fix', 'bug', 'issue', 'error']):
            return 'bugfix'
        if any(word in msg_lower for word in ['refactor', 'clean', 'rename', 'move']):
            return 'refactor'
        
        return 'unknown'
    
    def _extract_apps(self, files: dict[str, list[str]]) -> list[str]:
        """Extract Django app names from changed files."""
        apps = set()
        all_files = (
            files.get('added', []) + 
            files.get('modified', []) + 
            files.get('deleted', [])
        )
        
        for f in all_files:
            match = re.match(r'apps/(\w+)/', f)
            if match:
                apps.add(match.group(1))
        
        return sorted(apps)
    
    def _extract_models(self, files: dict[str, list[str]]) -> list[str]:
        """Extract model names from changed model files."""
        models = set()
        all_files = files.get('added', []) + files.get('modified', [])
        
        for f in all_files:
            if f.endswith('models.py'):
                # Read file and extract class names
                full_path = self.repo_path / f
                if full_path.exists():
                    content = full_path.read_text()
                    for match in re.finditer(r'class (\w+)\(.*Model\)', content):
                        models.add(match.group(1))
        
        return sorted(models)
