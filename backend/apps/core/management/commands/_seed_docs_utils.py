"""Shared utilities for Document seeding commands.

All seed_*_docs commands use this to:
- Read markdown body from git_path
- Set status='published' so HelpDashboard shows them
- Build consistent defaults dict
"""
import os
from pathlib import Path

# WC3 project root — parent of readmes/
WC3_ROOT = Path(__file__).resolve().parents[4]


def read_git_content(git_path: str) -> str:
    """Read markdown content from a git_path relative to WC3 root.

    Returns file content as string, or empty string if file not found.
    """
    full_path = WC3_ROOT / git_path
    if full_path.exists():
        return full_path.read_text(encoding='utf-8')
    return ''


def build_doc_defaults(doc: dict, doc_system: str) -> dict:
    """Build the defaults dict for Document.objects.update_or_create.

    Reads body content from git_path, sets status='published',
    calculates size_bytes.
    """
    body = read_git_content(doc['git_path'])

    defaults = {
        'name': doc['name'],
        'description': doc['description'],
        'status': 'published',
        'sequence': doc['sequence'],
        'mime_type': 'text/markdown',
        'body': body,
        'size_bytes': len(body.encode('utf-8')) if body else None,
        'path': {'git_path': doc['git_path']},
        'config': {
            'git_path': doc['git_path'],
            'doc_system': doc_system,
            'sync_from': 'wchq',
        },
        'refs': {
            'tags': doc.get('tags', []),
        },
    }

    if doc.get('qq_movie'):
        defaults['config']['qq_movie'] = doc['qq_movie']

    return defaults
