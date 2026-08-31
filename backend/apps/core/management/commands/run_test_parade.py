"""
run_test_parade — Execute pytest and return structured JSON results.

Usage:
    ./manage.py run_test_parade              # run all tests
    ./manage.py run_test_parade --marker smoke   # run only smoke tests
    ./manage.py run_test_parade --json       # JSON output (for API consumption)

PRE-PRODUCTION NOTE:
    Migrations may be deleted at any time until production release.
    This command does not depend on migration file names or counts.
"""
import json
import subprocess
import sys
from pathlib import Path

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run pytest and return structured test results for the test parade."

    def add_arguments(self, parser):
        parser.add_argument(
            '--marker', '-m', type=str, default='',
            help='Pytest marker filter (e.g., smoke, wcapi, domain)',
        )
        parser.add_argument(
            '--json', action='store_true', default=False,
            help='Output as JSON (for API consumption)',
        )
        parser.add_argument(
            '--file', type=str, default='',
            help='Run a specific test file',
        )

    def handle(self, *args, **options):
        backend_root = Path(__file__).resolve().parents[4]  # up to app/backend/
        python = sys.executable

        # Build pytest command
        cmd = [
            python, '-m', 'pytest',
            '--no-cov',
            '--tb=line',
            '-q',
            '--no-header',
        ]

        if options['marker']:
            cmd.extend(['-m', options['marker']])

        if options['file']:
            cmd.append(options['file'])

        # Run pytest and capture output
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(backend_root),
            timeout=300,
        )

        # Parse the output into structured results
        tests = self._parse_pytest_output(result.stdout, result.stderr)

        # Count by status
        counts = {'pass': 0, 'fail': 0, 'error': 0, 'skip': 0}
        for t in tests:
            counts[t['status']] = counts.get(t['status'], 0) + 1

        output = {
            'tests': tests,
            'summary': {
                'total': len(tests),
                'passed': counts.get('pass', 0),
                'failed': counts.get('fail', 0),
                'errors': counts.get('error', 0),
                'skipped': counts.get('skip', 0),
                'return_code': result.returncode,
            },
            'marker_filter': options['marker'] or 'all',
            'file_filter': options['file'] or 'all',
        }

        if options['json']:
            self.stdout.write(json.dumps(output, indent=2))
        else:
            self._print_table(output)

    def _parse_pytest_output(self, stdout, stderr):
        """Parse pytest -q output into structured test records."""
        tests = []
        lines = stdout.strip().split('\n') if stdout.strip() else []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Skip summary lines
            if line.startswith('=') or 'passed' in line or 'failed' in line:
                continue
            if line.startswith('TOTAL') or line.startswith('--'):
                continue

            # PASSED lines (in -q mode, just a dot progression)
            # FAILED lines
            if line.startswith('FAILED '):
                path_and_test = line[7:].strip()
                # Remove the " - ..." suffix if present
                if ' - ' in path_and_test:
                    path_and_test = path_and_test.split(' - ')[0]
                file_path, test_name = self._split_test_path(path_and_test)
                tests.append({
                    'file': file_path,
                    'name': test_name,
                    'status': 'fail',
                    'message': line.split(' - ', 1)[1] if ' - ' in line else '',
                })
            elif line.startswith('ERROR '):
                path_and_test = line[6:].strip()
                if ' - ' in path_and_test:
                    path_and_test = path_and_test.split(' - ')[0]
                file_path, test_name = self._split_test_path(path_and_test)
                tests.append({
                    'file': file_path,
                    'name': test_name,
                    'status': 'error',
                    'message': line.split(' - ', 1)[1] if ' - ' in line else '',
                })
            elif line.startswith('SKIPPED'):
                # SKIPPED [N] path::test - reason
                rest = line.split('] ', 1)[1] if '] ' in line else line[8:]
                if ' - ' in rest:
                    path_and_test = rest.split(' - ')[0].strip()
                else:
                    path_and_test = rest.strip()
                file_path, test_name = self._split_test_path(path_and_test)
                tests.append({
                    'file': file_path,
                    'name': test_name,
                    'status': 'skip',
                    'message': line.split(' - ', 1)[1] if ' - ' in line else '',
                })

        # Also parse the short summary for passed tests (not individually listed in -q)
        # We need verbose output for individual pass info. For now, get passed count from summary.
        for line in lines:
            if 'passed' in line and ('failed' in line or 'error' in line or 'skip' in line or line.strip().endswith('passed')):
                # This is the summary line, e.g., "257 passed, 2 failed, 30 skipped"
                import re
                passed_match = re.search(r'(\d+) passed', line)
                if passed_match:
                    passed_count = int(passed_match.group(1))
                    # We already have fail/error/skip from above. Passed aren't individually listed.
                    # We'll note the count but can't list individual passed tests from -q output.

        return tests

    def _split_test_path(self, path_and_test):
        """Split 'path/to/file.py::ClassName::test_name' into (file, test_name)."""
        if '::' in path_and_test:
            parts = path_and_test.split('::')
            return parts[0], '::'.join(parts[1:])
        return path_and_test, ''

    def _print_table(self, output):
        """Print a human-readable table of test results."""
        s = output['summary']
        self.stdout.write(f"\nTest Parade — {s['total']} tests")
        self.stdout.write(f"  Passed:  {s['passed']}")
        self.stdout.write(f"  Failed:  {s['failed']}")
        self.stdout.write(f"  Errors:  {s['errors']}")
        self.stdout.write(f"  Skipped: {s['skipped']}")
        self.stdout.write('')

        for t in output['tests']:
            icon = {'pass': '✓', 'fail': '✗', 'error': '!', 'skip': '○'}.get(t['status'], '?')
            self.stdout.write(f"  {icon} {t['file']}::{t['name']}")
            if t.get('message'):
                self.stdout.write(f"    {t['message']}")
