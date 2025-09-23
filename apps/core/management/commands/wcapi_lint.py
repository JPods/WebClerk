from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from apps.core.wcapi.linting import scan_repository, format_report

class Command(BaseCommand):
    help = "Scan for non-compliant wcapi routes outside apps/core/wcapi/urls.py. Allows explicit exemptions with owner and reason."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--root", type=str, default=".", help="Project root to scan")
        parser.add_argument("--include-tests", action="store_true", help="Include tests in scanning")
        parser.add_argument("--lookback", type=int, default=5, help="Lines above to search for exemption comment")
        parser.add_argument("--json", action="store_true", help="Output JSON findings")
        parser.add_argument("--no-fail", action="store_true", help="Do not exit non-zero on violations")

    def handle(self, *args: Any, **options: Any) -> None:
        root = Path(options["root"]).resolve()
        findings = scan_repository(root, include_tests=bool(options["include_tests"]), lookback_lines=int(options["lookback"]))
        violations = [f for f in findings if not f.exempt]
        report = format_report(findings, as_json=bool(options["json"]))

        stream = self.stdout if not violations else self.stderr
        stream.write(report)
        if violations and not options["no_fail"]:
            sys.exit(2)