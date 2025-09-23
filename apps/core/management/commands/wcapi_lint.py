from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from apps.core.wcapi.linting import scan_repository, format_report

class Command(BaseCommand):
    help = "Scan for non-compliant wcapi routes outside apps/core/wcapi/urls.py. Allows explicit exemptions with owner and reason."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--root", type=str, default=".", help="Project root to scan (default: current dir)")
        parser.add_argument("--include-tests", action="store_true", help="Include tests in scanning")
        parser.add_argument("--lookback", type=int, default=5, help="How many lines above to search for exemption comment")
        parser.add_argument("--json", action="store_true", help="Output JSON findings")
        parser.add_argument("--no-fail", action="store_true", help="Do not exit non-zero on violations")

    def handle(self, *args: Any, **options: Any) -> None:
        root = Path(options["root"]).resolve()
        include_tests = bool(options["include_tests"])
        lookback = int(options["lookback"])
        as_json = bool(options["json"])
        no_fail = bool(options["no_fail"])

        findings = scan_repository(root, include_tests=include_tests, lookback_lines=lookback)
        violations = [f for f in findings if not f.exempt]
        report = format_report(findings, as_json=as_json)

        if as_json:
            self.stdout.write(report)
        else:
            if violations:
                self.stderr.write(self.style.ERROR(report))
            else:
                self.stdout.write(self.style.SUCCESS(report))

        if violations and not no_fail:
            sys.exit(2)