"""
Test Parade — guided walk through every automated test.

Same parade pattern as Setting Parade and Form Parade:
  GET  /wcapi/_test_parade_manifest/   — all tests grouped by tier/marker
  GET  /wcapi/_test_parade_run/        — run tests and return results
  POST /wcapi/_test_parade_feedback/   — save feedback on a test

Users see: test name, what it verifies, pass/fail/error/skip,
recommended action. Alice uses the results for coaching.
"""
import json
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import Setting

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parents[3]  # app/backend/

# ── Test tier definitions ───────────────────────────────────────────

TEST_TIERS = [
    {
        'name': 'Smoke',
        'marker': 'smoke',
        'description': 'Structural health — Django boots, migrations clean, hook signatures',
        'time_budget': '< 10s',
    },
    {
        'name': 'Envelope',
        'marker': 'envelope',
        'description': 'API contract — every endpoint returns {status, code, message, data}',
        'time_budget': '< 30s',
    },
    {
        'name': 'Schema',
        'marker': 'schema',
        'description': 'Pydantic validates at save gate, BaseModel JSON correct',
        'time_budget': '< 60s',
    },
    {
        'name': 'WCAPI',
        'marker': 'wcapi',
        'description': 'All CRUD through wcapi endpoints, no direct model access',
        'time_budget': '< 120s',
    },
    {
        'name': 'Domain',
        'marker': 'domain',
        'description': 'Business rules — transactions, inventory, GL, pricing, BOM',
        'time_budget': '< 180s',
    },
    {
        'name': 'Integration',
        'marker': 'integration',
        'description': 'Full commerce cycle — proposal to payment to GL',
        'time_budget': '< 300s',
    },
]

# ── Recommended actions ─────────────────────────────────────────────

def _recommend_action(test):
    """Generate a recommended action based on test status."""
    status = test['status']
    if status == 'pass':
        return {'actor': 'none', 'action': 'No action needed'}
    if status == 'skip':
        return {
            'actor': 'system',
            'action': 'Skipped — check if the skip condition is still valid',
        }
    if status == 'error':
        msg = test.get('message', '')
        if 'migration' in msg.lower() or 'OperationalError' in msg:
            return {
                'actor': 'system',
                'action': 'Database/migration error — run makemigrations --check',
            }
        if 'ImportError' in msg or 'ModuleNotFoundError' in msg:
            return {
                'actor': 'system',
                'action': 'Missing import — a module was moved or deleted',
            }
        return {
            'actor': 'system',
            'action': 'Test setup error — review the test fixture or database state',
        }
    if status == 'fail':
        msg = test.get('message', '')
        if 'AssertionError' in msg or 'assert' in msg.lower():
            return {
                'actor': 'user',
                'action': 'Assertion failed — the test expected a different result. Review the tested feature.',
            }
        if 'TypeError' in msg:
            return {
                'actor': 'system',
                'action': 'Type error — a field name or argument changed. Update the test.',
            }
        return {
            'actor': 'user',
            'action': 'Test failed — review the feature this test covers',
        }
    return {'actor': 'unknown', 'action': 'Unknown status'}


def _test_explanation(test):
    """Generate a human-readable explanation of what a test verifies."""
    name = test.get('name', '')
    file_path = test.get('file', '')

    # Extract from file path
    area = 'general'
    if 'transactions' in file_path:
        area = 'transactions'
    elif 'accounts' in file_path:
        area = 'accounting'
    elif 'inventory' in file_path:
        area = 'inventory'
    elif 'products' in file_path:
        area = 'products'
    elif 'communications' in file_path:
        area = 'communications'
    elif 'sync' in file_path:
        area = 'sync'
    elif 'wcapi' in file_path:
        area = 'API'
    elif 'bom' in file_path:
        area = 'BOM'
    elif 'gl_' in file_path:
        area = 'GL/accounting'
    elif 'commerce_cycle' in file_path:
        area = 'commerce cycle'

    # Clean up test name for display
    display = name.replace('::', ' > ').replace('test_', '').replace('_', ' ')

    return {'area': area, 'description': display}


# ── Collect tests without running ───────────────────────────────────

def _collect_tests(marker=''):
    """Use pytest --collect-only to list tests without running them.

    Quiet mode outputs 'file.py: N' per file. We collect file-level
    entries since individual test names require verbose mode (slow).
    """
    cmd = [
        sys.executable, '-m', 'pytest',
        '--collect-only', '-q', '--no-cov', '--no-header',
    ]
    if marker:
        cmd.extend(['-m', marker])

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            cwd=str(BACKEND_ROOT), timeout=30,
        )
        tests = []
        for line in result.stdout.strip().split('\n'):
            line = line.strip()
            if not line or line.startswith('=') or line.startswith('-'):
                continue
            if line.startswith('no tests') or 'warning' in line.lower():
                continue
            # Format: "path/to/file.py: N" (quiet mode)
            if ': ' in line and line.endswith(tuple('0123456789')):
                parts = line.rsplit(': ', 1)
                file_path = parts[0].strip()
                try:
                    count = int(parts[1].strip())
                except ValueError:
                    continue
                for i in range(count):
                    tests.append({
                        'file': file_path,
                        'name': f'test_{i + 1}',
                    })
            # Format: "path/to/file.py::Class::test" (verbose mode)
            elif '::' in line:
                file_parts = line.split('::')
                tests.append({
                    'file': file_parts[0],
                    'name': '::'.join(file_parts[1:]),
                })
        return tests
    except Exception as e:
        logger.error("Failed to collect tests: %s", e)
        return []


# ── Run tests ───────────────────────────────────────────────────────

def _run_tests(marker='', file_path=''):
    """Run pytest and return structured results."""
    cmd = [
        sys.executable, '-m', 'pytest',
        '--no-cov', '--tb=line', '-v', '--no-header',
    ]
    if marker:
        cmd.extend(['-m', marker])
    if file_path:
        cmd.append(file_path)

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            cwd=str(BACKEND_ROOT), timeout=300,
        )
    except subprocess.TimeoutExpired:
        return [], {'total': 0, 'passed': 0, 'failed': 0, 'errors': 0,
                    'skipped': 0, 'timed_out': True}

    tests = []
    for line in result.stdout.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('=') or line.startswith('-'):
            continue

        # Verbose output format: path::test PASSED/FAILED/ERROR/SKIPPED
        if ' PASSED' in line:
            path_test = line.rsplit(' PASSED', 1)[0].strip()
            file_p, name = _split_path(path_test)
            tests.append({'file': file_p, 'name': name, 'status': 'pass', 'message': ''})
        elif ' FAILED' in line:
            path_test = line.rsplit(' FAILED', 1)[0].strip()
            file_p, name = _split_path(path_test)
            tests.append({'file': file_p, 'name': name, 'status': 'fail', 'message': ''})
        elif ' ERROR' in line:
            path_test = line.rsplit(' ERROR', 1)[0].strip()
            file_p, name = _split_path(path_test)
            tests.append({'file': file_p, 'name': name, 'status': 'error', 'message': ''})
        elif ' SKIPPED' in line:
            path_test = line.rsplit(' SKIPPED', 1)[0].strip()
            file_p, name = _split_path(path_test)
            tests.append({'file': file_p, 'name': name, 'status': 'skip', 'message': ''})

    # Extract error messages from the short summary section
    in_summary = False
    for line in result.stdout.strip().split('\n'):
        if 'short test summary' in line:
            in_summary = True
            continue
        if in_summary and line.startswith('FAILED '):
            path_msg = line[7:].strip()
            if ' - ' in path_msg:
                path_part, msg = path_msg.split(' - ', 1)
                for t in tests:
                    full = f"{t['file']}::{t['name']}"
                    if path_part.strip() == full:
                        t['message'] = msg.strip()
                        break
        elif in_summary and line.startswith('ERROR '):
            path_msg = line[6:].strip()
            if ' - ' in path_msg:
                path_part, msg = path_msg.split(' - ', 1)
                for t in tests:
                    full = f"{t['file']}::{t['name']}"
                    if path_part.strip() == full:
                        t['message'] = msg.strip()
                        break

    counts = {}
    for t in tests:
        counts[t['status']] = counts.get(t['status'], 0) + 1

    summary = {
        'total': len(tests),
        'passed': counts.get('pass', 0),
        'failed': counts.get('fail', 0),
        'errors': counts.get('error', 0),
        'skipped': counts.get('skip', 0),
    }

    return tests, summary


def _split_path(path_test):
    """Split 'path/file.py::Class::test' into (file, name)."""
    if '::' in path_test:
        parts = path_test.split('::')
        return parts[0], '::'.join(parts[1:])
    return path_test, ''


# ── Get stored results ──────────────────────────────────────────────

def _get_stored_results():
    """Get the most recent stored test parade results from Setting."""
    try:
        s = Setting.objects.filter(
            ida='test-parade-results',
            is_active=True,
        ).first()
        if s and isinstance(s.config, dict):
            return s.config
    except Exception:
        pass
    return None


def _store_results(data):
    """Store test parade results in a Setting record."""
    s, _ = Setting.objects.update_or_create(
        ida='test-parade-results',
        defaults={
            'name': 'Test Parade Results',
            'purpose': 'wc:test_parade',
            'is_active': True,
            'config': data,
        },
    )
    return s


def _get_feedback():
    """Get stored test feedback from Setting."""
    try:
        s = Setting.objects.filter(
            ida='test-parade-feedback',
            is_active=True,
        ).first()
        if s and isinstance(s.config, dict):
            return s.config
    except Exception:
        pass
    return {}


def _store_feedback(feedback_map):
    """Store test feedback in a Setting record."""
    s, _ = Setting.objects.update_or_create(
        ida='test-parade-feedback',
        defaults={
            'name': 'Test Parade Feedback',
            'purpose': 'wc:test_parade',
            'is_active': True,
            'config': feedback_map,
        },
    )
    return s


# ── Views ───────────────────────────────────────────────────────────

class TestParadeManifestView(APIView):
    """GET /wcapi/_test_parade_manifest/ — list all tests grouped by tier."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get stored results and feedback
        stored = _get_stored_results()
        feedback_map = _get_feedback()

        # Build test map from stored results for quick lookup
        result_map = {}
        if stored and 'tests' in stored:
            for t in stored['tests']:
                key = f"{t['file']}::{t['name']}"
                result_map[key] = t

        # Collect all tests (fast, no execution)
        all_tests = _collect_tests()

        # Group by file area
        groups = {}
        for t in all_tests:
            info = _test_explanation(t)
            area = info['area']
            if area not in groups:
                groups[area] = {
                    'name': area.title(),
                    'description': f'Tests for {area}',
                    'tests': [],
                    'count': 0,
                }

            key = f"{t['file']}::{t['name']}"
            stored_result = result_map.get(key, {})
            status = stored_result.get('status', 'unknown')

            test_entry = {
                'id': key,
                'file': t['file'],
                'name': t['name'],
                'description': info['description'],
                'area': area,
                'status': status,
                'message': stored_result.get('message', ''),
                'recommendation': _recommend_action({'status': status, 'message': stored_result.get('message', '')}),
                'feedback': feedback_map.get(key),
            }
            groups[area]['tests'].append(test_entry)
            groups[area]['count'] += 1

        # Sort groups by name
        group_list = sorted(groups.values(), key=lambda g: g['name'])

        # Counts
        total = sum(g['count'] for g in group_list)
        reviewed = sum(1 for g in group_list for t in g['tests'] if t.get('feedback'))
        status_counts = {}
        for g in group_list:
            for t in g['tests']:
                s = t['status']
                status_counts[s] = status_counts.get(s, 0) + 1

        return Response({
            'groups': group_list,
            'total_tests': total,
            'reviewed_count': reviewed,
            'summary': status_counts,
            'last_run': stored.get('run_at') if stored else None,
            'tiers': TEST_TIERS,
        })


class TestParadeRunView(APIView):
    """GET /wcapi/_test_parade_run/ — run tests and return results."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        marker = request.query_params.get('marker', '')
        file_path = request.query_params.get('file', '')

        tests, summary = _run_tests(marker=marker, file_path=file_path)

        # Enrich each test with explanation and recommendation
        for t in tests:
            info = _test_explanation(t)
            t['description'] = info['description']
            t['area'] = info['area']
            t['recommendation'] = _recommend_action(t)

        run_data = {
            'tests': tests,
            'summary': summary,
            'marker_filter': marker or 'all',
            'file_filter': file_path or 'all',
            'run_at': datetime.now(timezone.utc).isoformat(),
        }

        # Store results
        _store_results(run_data)

        return Response(run_data)


class TestParadeFeedbackView(APIView):
    """POST /wcapi/_test_parade_feedback/ — save feedback on a test."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        test_id = request.data.get('test_id')  # "file::name"
        choice = request.data.get('feedback')
        notes = request.data.get('notes', '')

        if not test_id:
            return Response({'error': 'test_id required'}, status=400)

        valid_choices = ('understood', 'investigate', 'needs_fix', 'wont_fix')
        if choice not in valid_choices:
            return Response({
                'error': f'feedback must be one of: {", ".join(valid_choices)}',
            }, status=400)

        # Load and update feedback map
        feedback_map = _get_feedback()
        feedback_map[test_id] = {
            'choice': choice,
            'notes': notes,
            'reviewed_by': request.user.username if request.user else '',
            'reviewed_at': datetime.now(timezone.utc).isoformat(),
        }
        _store_feedback(feedback_map)

        return Response({'ok': True, 'test_id': test_id, 'feedback': choice})
