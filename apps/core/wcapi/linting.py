from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional, Tuple

WCAPI_PREFIXES = ("wcapi/", "/wcapi/")
ALLOWED_URL_FILES = {"apps/core/wcapi/urls.py"}

SKIP_DIRS = {
    ".git", ".hg", ".svn", ".tox", ".mypy_cache", ".pytest_cache",
    "node_modules", "dist", "build", "static", "media",
    "lib", "venv", ".venv", "env", ".env",
}

EXEMPT_RE = re.compile(
    r"#\s*(wcapi\s*[-_ ]?\s*(?:noncompliant|exempt))\b.*?(?:owner|responsible)\s*=\s*([^\s,;]+).*?reason\s*=\s*(.+)",
    re.IGNORECASE,
)

@dataclass
class Finding:
    file: str
    line: int
    route: str
    exempt: bool
    owner: Optional[str] = None
    reason: Optional[str] = None
    context: Optional[str] = None

def _is_python_file(p: Path) -> bool:
    return p.suffix == ".py"

def _should_skip_dir(p: Path) -> bool:
    return p.name in SKIP_DIRS

def _is_allowed_file(p: Path, project_root: Path) -> bool:
    rel = str(p.relative_to(project_root)).replace("\\", "/")
    return rel in ALLOWED_URL_FILES

def _extract_route_str(node: ast.Call) -> Optional[str]:
    if not node.args:
        return None
    arg0 = node.args[0]
    if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
        return arg0.value
    return None

def _looks_like_wcapi(route: str) -> bool:
    s = route.strip()
    return s.startswith(WCAPI_PREFIXES)

def _func_is_path_like(node: ast.Call) -> bool:
    f = node.func
    if isinstance(f, ast.Name):
        return f.id in {"path", "re_path", "url"}
    if isinstance(f, ast.Attribute):
        return f.attr in {"path", "re_path", "url"}
    return False

def _read_lines(path: Path) -> List[str]:
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []

def _find_exemption(lines: List[str], call_lineno: int, lookback: int = 5) -> Tuple[bool, Optional[str], Optional[str]]:
    start = max(0, call_lineno - 1 - lookback)
    end = max(0, call_lineno - 1)
    window = lines[start:end]
    for line in reversed(window):
        m = EXEMPT_RE.search(line)
        if m:
            owner = (m.group(2) or "").strip()
            reason = (m.group(3) or "").strip()
            if owner and reason:
                return True, owner, reason
    return False, None, None

def scan_repository(root: Path, include_tests: bool = False, lookback_lines: int = 5) -> List[Finding]:
    findings: List[Finding] = []
    for p in root.rglob("*.py"):
        if any(_should_skip_dir(Path(part)) for part in p.parents):
            continue
        if not include_tests and ("tests" in p.parts or p.name.startswith("test_")):
            continue
        if not _is_python_file(p):
            continue
        if _is_allowed_file(p, root):
            continue

        try:
            src = p.read_text(encoding="utf-8")
        except Exception:
            continue

        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue

        lines = src.splitlines()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not _func_is_path_like(node):
                continue
            route = _extract_route_str(node)
            if not route:
                continue
            if not _looks_like_wcapi(route):
                continue

            exempt, owner, reason = _find_exemption(lines, getattr(node, "lineno", 1), lookback=lookback_lines)
            ctx = "\n".join(lines[max(0, node.lineno - 2): min(len(lines), node.lineno + 1)])
            findings.append(
                Finding(
                    file=str(p.relative_to(root)).replace("\\", "/"),
                    line=getattr(node, "lineno", 1),
                    route=route,
                    exempt=exempt,
                    owner=owner,
                    reason=reason,
                    context=ctx,
                )
            )
    return findings

def format_report(findings: List[Finding], as_json: bool = False) -> str:
    if as_json:
        return json.dumps([asdict(f) for f in findings], indent=2)
    if not findings:
        return "WCAPI route lint: no issues found."
    lines = ["WCAPI route lint: findings"]
    for f in findings:
        status = "EXEMPT" if f.exempt else "VIOLATION"
        who = f.owner or "unknown"
        why = f.reason or "no reason provided"
        lines.append(f"- {status}: {f.file}:{f.line} -> '{f.route}' (owner={who}; reason={why})")
    return "\n".join(lines)