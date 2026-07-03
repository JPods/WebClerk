"""
Code Standards Enforcement — Alice watches for anti-patterns in React code.

Alice doesn't just coach users — she coaches developers. When new code is
committed that violates standards, she flags it. When existing code is touched,
she suggests migration.

Standards enforced:
  1. All data lists use DataGrid — no custom <table>, no AdvancedDataTable
  2. All fields use BehaviorField — no raw <input> for model fields
  3. All elements have data-wc attributes — required for help system
  4. All pages support dark mode — dark: prefixes on all colors
  5. All list pages redirect to DataBrowser unless they have model-specific features
  6. Protected layouts (alice_guess, alphabetical) cannot be overwritten
  7. No hardcoded field lists — use workbench_fields Settings
  8. All CRUD goes through wcapi — no direct model access

Run modes:
  - On git commit (hook) — scan changed .tsx files
  - On schedule (cron) — full codebase scan
  - On demand (manage action) — scan specific file or directory
"""
from __future__ import annotations

import os
import re
import time
from pathlib import Path

REACT_ROOT = Path('/Users/williamjames/Documents/CommerceExpert/React2025/src')

# Anti-patterns to detect
ANTI_PATTERNS = [
    {
        'id': 'custom-table',
        'pattern': r'<table\b',
        'exclude_files': ['DataGrid.tsx', 'PrintDocumentLayout.tsx'],
        'severity': 'warning',
        'message': 'Custom <table> found — use DataGrid for data lists. Tables are OK for layout/print templates.',
        'fix': 'Replace with <DataGrid records={...} columns={...} />',
    },
    {
        'id': 'deprecated-adt',
        'pattern': r'AdvancedDataTable',
        'exclude_files': ['AdvancedDataTable.tsx', 'AdvancedDataTable_DEPRECATED.tsx'],
        'severity': 'error',
        'message': 'AdvancedDataTable is deprecated — migrate to DataGrid.',
        'fix': 'Import DataGrid from @/components/common/DataGrid instead.',
    },
    {
        'id': 'missing-data-wc',
        'pattern': r'export default function \w+',
        'check': 'missing_data_wc',
        'severity': 'info',
        'message': 'Page component missing data-wc attribute on root element.',
        'fix': 'Add data-wc="{component-name}" to the outermost div.',
    },
    {
        'id': 'raw-select',
        'pattern': r'<select\b(?![^>]*data-wc)',
        'exclude_files': ['FilterSelect.tsx', 'FieldOrderDialog.tsx'],
        'severity': 'info',
        'message': 'Raw <select> found — consider using FilterSelect for model fields.',
        'fix': 'Replace with <FilterSelect options={...} value={...} onChange={...} />',
    },
    {
        'id': 'no-dark-mode',
        'pattern': r'(?:background|color|border):\s*["\']#[0-9a-fA-F]+["\']',
        'check': 'no_dark_variant',
        'severity': 'info',
        'message': 'Hardcoded color without dark mode variant.',
        'fix': 'Use theme object (t.bg, t.text, etc.) or add dark: prefix.',
    },
    {
        'id': 'direct-model-import',
        'pattern': r'from.*models.*import|\.objects\.',
        'exclude_files': [],
        'file_type': '.py',
        'severity': 'warning',
        'message': 'Direct model access — all CRUD should go through wcapi.',
        'fix': 'Use wcapi getRecords/saveRecord instead of direct model queries.',
    },
    {
        'id': 'hardcoded-fields',
        'pattern': r"columns\s*=\s*\[.*['\"]ida['\"].*['\"]name['\"]",
        'severity': 'info',
        'message': 'Hardcoded field list — use workbench_fields Setting for field configuration.',
        'fix': 'Load field list from workbench_fields Setting via getAllWorkbenchFieldsSettings().',
    },
    {
        'id': 'buttons-at-bottom',
        'pattern': r'borderTop.*button.*Cancel|borderTop.*button.*Apply|borderTop.*button.*Save',
        'severity': 'warning',
        'message': 'Action buttons at bottom of dialog/panel — move to top. Fewer mouse movements = better UI.',
        'fix': 'Place Cancel/Apply/Save buttons in the header area, aggregated together. Data below, buttons above.',
    },
]


def _now_ms():
    return int(time.time() * 1000)


def scan_file(filepath: str) -> list[dict]:
    """Scan a single file for anti-patterns.

    Returns: [{pattern_id, severity, message, fix, line_number, line_text}]
    """
    path = Path(filepath)
    if not path.exists():
        return []

    violations = []
    try:
        content = path.read_text(errors='replace')
        lines = content.split('\n')
    except Exception:
        return []

    filename = path.name

    for ap in ANTI_PATTERNS:
        # Check file type filter
        file_type = ap.get('file_type', '.tsx')
        if not filename.endswith(file_type):
            continue

        # Check exclusions
        if filename in ap.get('exclude_files', []):
            continue

        # Run pattern match
        pattern = ap.get('pattern', '')
        if not pattern:
            continue

        for i, line in enumerate(lines, 1):
            if re.search(pattern, line):
                # Special checks
                check = ap.get('check')
                if check == 'no_dark_variant':
                    # Only flag if no dark: variant nearby
                    context = '\n'.join(lines[max(0, i - 3):min(len(lines), i + 3)])
                    if 'dark:' in context or 'theme' in context or 'isDark' in context:
                        continue
                if check == 'missing_data_wc':
                    if 'data-wc' in content:
                        continue  # File has at least one data-wc

                violations.append({
                    'pattern_id': ap['id'],
                    'severity': ap['severity'],
                    'message': ap['message'],
                    'fix': ap['fix'],
                    'line_number': i,
                    'line_text': line.strip()[:120],
                    'file': str(path),
                })

    return violations


def scan_directory(directory: str = None, file_type: str = '.tsx') -> dict:
    """Scan a directory for anti-patterns.

    Returns: {total_files, files_with_violations, violations: [{file, pattern_id, ...}]}
    """
    root = Path(directory) if directory else REACT_ROOT
    if not root.exists():
        return {'error': f'Directory not found: {root}'}

    all_violations = []
    total_files = 0
    files_with_issues = set()

    for path in root.rglob(f'*{file_type}'):
        if 'node_modules' in str(path) or '__pycache__' in str(path):
            continue
        total_files += 1
        violations = scan_file(str(path))
        if violations:
            files_with_issues.add(str(path))
            all_violations.extend(violations)

    # Group by severity
    by_severity = {}
    for v in all_violations:
        sev = v['severity']
        by_severity[sev] = by_severity.get(sev, 0) + 1

    return {
        'total_files': total_files,
        'files_with_violations': len(files_with_issues),
        'total_violations': len(all_violations),
        'by_severity': by_severity,
        'violations': all_violations[:100],  # cap at 100 for response size
    }


def scan_changed_files(file_list: list[str]) -> dict:
    """Scan specific files (e.g., from a git commit hook).

    Args:
        file_list: list of file paths to scan

    Returns: same as scan_directory but only for listed files
    """
    all_violations = []
    for filepath in file_list:
        violations = scan_file(filepath)
        all_violations.extend(violations)

    return {
        'files_scanned': len(file_list),
        'total_violations': len(all_violations),
        'violations': all_violations,
    }


def get_migration_report() -> dict:
    """Full codebase report — what still needs migration.

    Returns counts of each anti-pattern across the codebase.
    """
    tsx_result = scan_directory(str(REACT_ROOT), '.tsx')

    # Count by pattern
    by_pattern = {}
    for v in tsx_result.get('violations', []):
        pid = v['pattern_id']
        if pid not in by_pattern:
            by_pattern[pid] = {'count': 0, 'files': set(), 'severity': v['severity'], 'message': v['message']}
        by_pattern[pid]['count'] += 1
        by_pattern[pid]['files'].add(v['file'])

    # Convert sets to lists for JSON
    summary = []
    for pid, data in sorted(by_pattern.items(), key=lambda x: -x[1]['count']):
        summary.append({
            'pattern_id': pid,
            'count': data['count'],
            'files_affected': len(data['files']),
            'severity': data['severity'],
            'message': data['message'],
        })

    return {
        'total_files': tsx_result['total_files'],
        'files_with_violations': tsx_result['files_with_violations'],
        'total_violations': tsx_result['total_violations'],
        'summary': summary,
        'dt_scanned': _now_ms(),
    }
