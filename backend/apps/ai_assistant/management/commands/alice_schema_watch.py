"""
Alice schema watcher command.

Detects likely wc3 schema changes from git files, runs schema drift assessment,
logs observations to Alice notes, and reports React pages likely affected.

Usage:
    python manage.py alice_schema_watch
    python manage.py alice_schema_watch --commit <hash>
    python manage.py alice_schema_watch --files apps/core/models.py apps/orgs/migrations/0002_auto.py
    python manage.py alice_schema_watch --quiet
"""

from __future__ import annotations

import re
import subprocess
from datetime import timezone
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.ai_assistant.services.alice_notes import create_note
from apps.ai_assistant.services.schema_drift_detector import SchemaDriftDetector
from apps.ai_assistant.services.to_alice_overrides import load_validated_to_alice_overrides


SCHEMA_FILE_PATTERNS = (
    r"^apps/.+/models\.py$",
    r"^apps/.+/migrations/.+\.py$",
    r"^common/models\.py$",
    r"^common/.+schema.+\.py$",
    r"^readmes/model-fields\.json$",
    r"^readmes/model-registry\.json$",
    r"^\.copilot-context/models/.+\.md$",
)


def _run_git(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=20,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _changed_files(repo_root: Path, commit: str | None) -> list[str]:
    if commit:
        out = _run_git(repo_root, "show", "--name-only", "--pretty=format:", commit)
    else:
        staged = _run_git(repo_root, "diff", "--cached", "--name-only")
        unstaged = _run_git(repo_root, "diff", "--name-only")
        out = "\n".join([staged, unstaged]).strip()
    return [line.strip() for line in out.splitlines() if line.strip()]


def _is_schema_related(path: str) -> bool:
    return any(re.match(pattern, path) for pattern in SCHEMA_FILE_PATTERNS)


def _model_names_from_paths(paths: list[str]) -> list[str]:
    found: set[str] = set()
    for path in paths:
        m = re.search(r"apps/[^/]+/models/([^/]+)\.py$", path)
        if m:
            found.add(m.group(1).lower())
    return sorted(found)


def _react_pages_for_models(r25_root: Path, model_names: list[str]) -> list[str]:
    pages: set[str] = set()
    if not r25_root.exists() or not model_names:
        return []

    for model_name in model_names:
        pattern = f"src/apps/**/models/{model_name}/pages/*.tsx"
        for file_path in r25_root.glob(pattern):
            pages.add(str(file_path.relative_to(r25_root)))

        # Fallback: route-level and top pages containing the model key.
        for file_path in r25_root.glob("src/pages/**/*.tsx"):
            try:
                text = file_path.read_text(encoding="utf-8")
            except OSError:
                continue
            if re.search(rf"\b{re.escape(model_name)}\b", text):
                pages.add(str(file_path.relative_to(r25_root)))

    return sorted(pages)


def _collect_model_pages(r25_root: Path, model_name: str) -> list[Path]:
    pages = sorted(r25_root.glob(f"src/apps/**/models/{model_name}/pages/*.tsx"))
    return [p for p in pages if p.is_file()]


def _page_field_hits(page_path: Path, fields: list[str]) -> tuple[int, list[str]]:
    try:
        text = page_path.read_text(encoding="utf-8")
    except OSError:
        return 0, []

    hits: list[str] = []
    for field in fields:
        if not field or field == "*":
            continue
        # Prefer exact token matches to reduce false positives.
        if re.search(rf"(?<![A-Za-z0-9_]){re.escape(field)}(?![A-Za-z0-9_])", text):
            hits.append(field)
    return len(hits), sorted(set(hits))


def _assess_impacted_pages(
    r25_root: Path,
    model_names: list[str],
    drift_report: dict[str, Any],
) -> list[dict[str, Any]]:
    assessments: list[dict[str, Any]] = []

    for model_name in model_names:
        model_data = drift_report.get("per_model", {}).get(model_name, {})
        issue_fields = [i.get("field", "") for i in model_data.get("issues", []) if i.get("field") not in ("", "*")]

        # If there are no issue fields, use Django field names as a broad fallback.
        if not issue_fields:
            django_field_map = model_data.get("django_field_map", {})
            issue_fields = list(django_field_map.keys())

        issue_fields = sorted(set(issue_fields))
        if not issue_fields:
            continue

        for page_path in _collect_model_pages(r25_root, model_name):
            score, matched_fields = _page_field_hits(page_path, issue_fields)
            if score <= 0:
                continue
            assessments.append(
                {
                    "model": model_name,
                    "page": str(page_path.relative_to(r25_root)),
                    "score": score,
                    "matched_fields": matched_fields,
                }
            )

    assessments.sort(key=lambda row: (row["score"], row["model"], row["page"]), reverse=True)
    return assessments


def _write_markdown_report(
    repo_root: Path,
    *,
    commit: str | None,
    schema_files: list[str],
    model_names: list[str],
    drift_report: dict[str, Any],
    impacted_pages: list[dict[str, Any]],
) -> str:
    reports_dir = repo_root / "readmes" / "topics" / "ai" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    now = __import__("datetime").datetime.now(tz=timezone.utc)
    stamp = now.strftime("%Y%m%d-%H%M%S")
    file_name = f"alice-schema-watch-{stamp}.md"
    report_path = reports_dir / file_name
    latest_path = reports_dir / "alice-schema-watch-latest.md"

    sev = drift_report.get("severity_counts", {})
    lines = [
        "# Alice Schema Watch Report",
        "",
        f"- Timestamp (UTC): {now.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Commit: {commit or 'working-tree'}",
        f"- Schema files touched: {len(schema_files)}",
        f"- Models touched: {', '.join(model_names) if model_names else '(none inferred)'}",
        f"- Drift issues: total={drift_report.get('total_issues', 0)}, high={sev.get('high', 0)}, medium={sev.get('medium', 0)}, low={sev.get('low', 0)}",
        "",
        "## Schema Files",
    ]

    if schema_files:
        lines.extend([f"- {p}" for p in schema_files])
    else:
        lines.append("- (none)")

    lines.append("")
    lines.append("## Likely Impacted Pages (Field-Level)")
    if impacted_pages:
        for row in impacted_pages[:80]:
            matched = ", ".join(row.get("matched_fields", [])[:12])
            lines.append(f"- [{row['model']}] {row['page']} (score={row['score']})")
            lines.append(f"  fields: {matched}")
    else:
        lines.append("- (none detected)")

    lines.append("")
    lines.append("## Per-Model Drift Summary")
    for model_name in sorted(drift_report.get("per_model", {}).keys()):
        data = drift_report["per_model"][model_name]
        lines.append(f"- {model_name}: {len(data.get('issues', []))} issues")

    content = "\n".join(lines).strip() + "\n"
    report_path.write_text(content, encoding="utf-8")
    latest_path.write_text(content, encoding="utf-8")
    return str(report_path.relative_to(repo_root))


def _snake_to_pascal(name: str) -> str:
    return "".join(part.capitalize() for part in name.split("_") if part)


def _extract_admin_usage(repo_root: Path, model_names: list[str]) -> dict[str, list[dict[str, Any]]]:
    usage: dict[str, list[dict[str, Any]]] = {m: [] for m in model_names}
    admin_files = sorted(repo_root.glob("apps/**/admin.py"))

    for admin_file in admin_files:
        try:
            lines = admin_file.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue

        for model_name in model_names:
            pascal = _snake_to_pascal(model_name)
            token_hits = (
                re.search(rf"\b{re.escape(model_name)}\b", "\n".join(lines))
                or re.search(rf"\b{re.escape(pascal)}\b", "\n".join(lines))
            )
            if not token_hits:
                continue

            key_lines: list[dict[str, Any]] = []
            for idx, line in enumerate(lines, start=1):
                stripped = line.strip()
                if re.search(r"\b(list_display|fields|fieldsets|readonly_fields|search_fields)\b", stripped):
                    key_lines.append({"line": idx, "text": stripped})

            if key_lines:
                usage[model_name].append(
                    {
                        "file": str(admin_file.relative_to(repo_root)),
                        "lines": key_lines[:20],
                    }
                )

    return usage


def _pick_useful_scalar(scalars: list[str]) -> str:
    preferred = [
        "name",
        "display_name",
        "company",
        "title",
        "number",
        "code",
        "status",
        "email",
        "phone",
        "ida",
    ]
    scalar_set = set(scalars)
    for field in preferred:
        if field in scalar_set:
            return field

    # Avoid purely technical/system columns if possible.
    less_useful_prefixes = ("dt_",)
    less_useful_exact = {"id", "uuid", "ida", "version", "row_version", "is_active", "is_deleted", "is_archived"}
    candidates = [
        f for f in scalars
        if f not in less_useful_exact and not any(f.startswith(prefix) for prefix in less_useful_prefixes)
    ]
    if candidates:
        return sorted(candidates)[0]
    return scalars[0] if scalars else "id"


def _build_admin_field_plan(
    model_names: list[str],
    drift_report: dict[str, Any],
    override_map: dict[str, dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    plan: dict[str, dict[str, Any]] = {}
    override_map = override_map or {}

    for model_name in model_names:
        model_data = drift_report.get("per_model", {}).get(model_name, {})
        field_map: dict[str, Any] = model_data.get("django_field_map", {}) or {}

        scalars = sorted(
            [name for name, info in field_map.items() if info.get("django_type") != "JSONField"]
        )
        jsonb = sorted(
            [name for name, info in field_map.items() if info.get("django_type") == "JSONField"]
        )

        useful = _pick_useful_scalar(scalars)
        list_display = ["ida", useful] if "ida" in scalars else [useful]
        if useful == "ida" and "id" in scalars:
            list_display = ["ida", "id"]

        details_order = scalars + jsonb
        override = override_map.get(model_name, {})
        if override.get("list_display"):
            list_display = list(override["list_display"])
        if override.get("detail_order"):
            details_order = list(override["detail_order"])

        plan[model_name] = {
            "list_display": list_display,
            "details_order": details_order,
            "scalar_fields": scalars,
            "jsonb_fields": jsonb,
            "to_alice_sources": list(override.get("sources", [])),
        }

    return plan


class Command(BaseCommand):
    help = "Alice watches wc3 schema changes and reports likely affected React pages"

    def add_arguments(self, parser):
        parser.add_argument(
            "--commit",
            type=str,
            default="",
            help="Analyze changed files from a specific commit hash",
        )
        parser.add_argument(
            "--files",
            nargs="*",
            default=None,
            help="Explicit file paths to analyze instead of git diff",
        )
        parser.add_argument(
            "--quiet",
            action="store_true",
            help="Minimal console output",
        )
        parser.add_argument(
            "--no-report",
            action="store_true",
            help="Skip writing markdown report artifact",
        )

    def handle(self, *args, **options):
        quiet = bool(options.get("quiet"))
        commit = (options.get("commit") or "").strip() or None
        files_opt = options.get("files")
        no_report = bool(options.get("no_report"))

        repo_root = Path(settings.BASE_DIR)
        r25_root = repo_root.parent / "React2025"

        changed = list(files_opt) if files_opt is not None else _changed_files(repo_root, commit)
        changed = sorted(set(changed))
        schema_files = [path for path in changed if _is_schema_related(path)]

        if not quiet:
            self.stdout.write(f"Changed files: {len(changed)}")
            self.stdout.write(f"Schema-related files: {len(schema_files)}")

        if not schema_files:
            create_note(
                "log",
                role="system",
                name="Alice schema watch: no schema-related changes",
                parent_model="",
                details={
                    "source": "alice_schema_watch",
                    "commit": commit or "working-tree",
                    "changed_files_count": len(changed),
                    "schema_files": [],
                },
            )
            if not quiet:
                self.stdout.write(self.style.SUCCESS("No schema-related changes detected."))
            return

        model_names = _model_names_from_paths(schema_files)
        detector = SchemaDriftDetector(use_llm=False)

        if model_names:
            per_model: dict[str, Any] = {}
            severity_counts = {"high": 0, "medium": 0, "low": 0}
            total_issues = 0
            for model_name in model_names:
                model_report = detector.detect_model(model_name)

                # Include Django field map for field-level page impact fallback.
                field_map = detector._get_django_fields(model_name) or {}
                model_report["django_field_map"] = field_map

                per_model[model_name] = model_report
                for issue in model_report.get("issues", []):
                    sev = issue.get("severity", "low")
                    if sev in severity_counts:
                        severity_counts[sev] += 1
                total_issues += len(model_report.get("issues", []))

            drift_report = {
                "models_checked": len(model_names),
                "total_issues": total_issues,
                "severity_counts": severity_counts,
                "per_model": per_model,
            }
        else:
            drift_report = detector.detect_all()

        effective_models = list(model_names)
        if not effective_models:
            ranked = sorted(
                drift_report.get("per_model", {}).items(),
                key=lambda item: len(item[1].get("issues", [])),
                reverse=True,
            )
            effective_models = [name for name, data in ranked if data.get("issues")][:12]

        for model_name in effective_models:
            model_block = drift_report.get("per_model", {}).setdefault(model_name, {})
            if not model_block.get("django_field_map"):
                model_block["django_field_map"] = detector._get_django_fields(model_name) or {}

        model_fields = {
            model_name: {
                "scalar_fields": sorted(
                    [name for name, info in drift_report.get("per_model", {}).get(model_name, {}).get("django_field_map", {}).items() if info.get("django_type") != "JSONField"]
                ),
                "jsonb_fields": sorted(
                    [name for name, info in drift_report.get("per_model", {}).get(model_name, {}).get("django_field_map", {}).items() if info.get("django_type") == "JSONField"]
                ),
            }
            for model_name in effective_models
        }
        to_alice_overrides, to_alice_audit = load_validated_to_alice_overrides(repo_root, model_fields)

        field_level_impacts = _assess_impacted_pages(r25_root, effective_models, drift_report)
        if field_level_impacts:
            impacted_pages = [row["page"] for row in field_level_impacts]
        else:
            impacted_pages = _react_pages_for_models(r25_root, effective_models)

        admin_usage = _extract_admin_usage(repo_root, effective_models)
        admin_field_plan = _build_admin_field_plan(effective_models, drift_report, to_alice_overrides)

        report_file = ""
        if not no_report:
            report_file = _write_markdown_report(
                repo_root,
                commit=commit,
                schema_files=schema_files,
                model_names=effective_models,
                drift_report=drift_report,
                impacted_pages=field_level_impacts,
            )

            # Append admin usage + field plan and user-instruction comment template.
            report_abspath = repo_root / report_file
            report_text = report_abspath.read_text(encoding="utf-8")
            lines = [report_text.rstrip(), "", "## Admin.py Field Usage"]
            for model_name in effective_models:
                lines.append("")
                lines.append(f"### {model_name}")
                entries = admin_usage.get(model_name, [])
                if not entries:
                    lines.append("- No admin.py usage snippets found for this model.")
                else:
                    for entry in entries:
                        lines.append(f"- {entry['file']}")
                        for snippet in entry.get("lines", [])[:20]:
                            lines.append(f"  - L{snippet['line']}: {snippet['text']}")

                model_plan = admin_field_plan.get(model_name, {})
                list_display = model_plan.get("list_display", [])
                details_order = model_plan.get("details_order", [])
                scalar_fields = model_plan.get("scalar_fields", [])
                jsonb_fields = model_plan.get("jsonb_fields", [])

                lines.append("- Recommended list display: " + ", ".join(list_display))
                lines.append(
                    "- Recommended detail order (all fields): "
                    + ", ".join(details_order)
                )
                lines.append("- Scalar fields (alphabetical): " + ", ".join(scalar_fields))
                lines.append("- JSONB fields (alphabetical): " + ", ".join(jsonb_fields))
                if model_plan.get("to_alice_sources"):
                    lines.append("- To_Alice sources applied: " + ", ".join(model_plan["to_alice_sources"]))

            lines.extend(["", "## To_Alice Consumption"])
            if to_alice_audit.get("applied"):
                for item in to_alice_audit["applied"]:
                    lines.append(
                        "- Applied "
                        f"[{item.get('source')}] model={item.get('model')} "
                        f"list_display={','.join(item.get('list_display', [])) or '(unchanged)'} "
                        f"detail_order={','.join(item.get('detail_order', [])[:8]) or '(unchanged)'}"
                    )
                    if item.get("invalid_list_display") or item.get("invalid_detail_order"):
                        lines.append(
                            "  invalid_fields: "
                            + ", ".join(item.get("invalid_list_display", []) + item.get("invalid_detail_order", []))
                        )
            else:
                lines.append("- No To_Alice overrides were applied.")
            for item in to_alice_audit.get("ignored", []):
                lines.append(
                    "- Ignored "
                    f"[{item.get('source')}] model={item.get('model') or '(unknown)'} reason={item.get('reason')}"
                )

            lines.extend(
                [
                    "",
                    "## User Overrides",
                    "<!-- To_Alice: -->",
                    "- Example To_Alice payload: model=customer; list_display=ida,display_name; detail_order=display_name,status,addresses,contacts",
                    "- To provide alternative instructions, add a note via /wcapi/ai/note/ with:",
                    "  category=pending, role=config_suggestion, name='Schema report override',",
                    "  details={model, list_display, detail_order, rationale}",
                ]
            )

            final_text = "\n".join(lines).strip() + "\n"
            report_abspath.write_text(final_text, encoding="utf-8")
            latest_path = repo_root / "readmes" / "topics" / "ai" / "reports" / "alice-schema-watch-latest.md"
            latest_path.write_text(final_text, encoding="utf-8")

        high_issues = int(drift_report.get("severity_counts", {}).get("high", 0))

        log_note = create_note(
            "log",
            role="system",
            name="Alice schema watch: wc3 schema change assessed",
            parent_model="",
            details={
                "source": "alice_schema_watch",
                "commit": commit or "working-tree",
                "schema_files": schema_files,
                "models_touched": effective_models,
                "drift": {
                    "models_checked": drift_report.get("models_checked", 0),
                    "total_issues": drift_report.get("total_issues", 0),
                    "severity_counts": drift_report.get("severity_counts", {}),
                },
                "impacted_pages": impacted_pages,
                "impacted_pages_count": len(impacted_pages),
                "field_level_impacts": field_level_impacts[:120],
                "report_file": report_file,
                "admin_usage": admin_usage,
                "admin_field_plan": admin_field_plan,
                "to_alice_overrides": to_alice_overrides,
                "to_alice_audit": to_alice_audit,
            },
        )

        pending_id: int | None = None
        if high_issues > 0:
            pending = create_note(
                "pending",
                role="action_required",
                name="Schema drift high-severity issues need page review",
                parent_model="",
                details={
                    "source": "alice_schema_watch",
                    "high_issues": high_issues,
                    "models_touched": effective_models,
                    "impacted_pages": impacted_pages,
                    "field_level_impacts": field_level_impacts[:120],
                    "report_file": report_file,
                    "admin_usage": admin_usage,
                    "admin_field_plan": admin_field_plan,
                    "to_alice_overrides": to_alice_overrides,
                },
            )
            pending_id = pending.pk

        if not quiet:
            self.stdout.write(self.style.SUCCESS("Alice schema watch completed."))
            self.stdout.write(f"alice_log id: {log_note.pk}")
            if pending_id:
                self.stdout.write(self.style.WARNING(f"alice_pending id: {pending_id}"))
            self.stdout.write(
                f"drift issues: total={drift_report.get('total_issues', 0)} "
                f"high={drift_report.get('severity_counts', {}).get('high', 0)} "
                f"medium={drift_report.get('severity_counts', {}).get('medium', 0)} "
                f"low={drift_report.get('severity_counts', {}).get('low', 0)}"
            )
            if report_file:
                self.stdout.write(f"report: {report_file}")
            if impacted_pages:
                self.stdout.write("Likely impacted React pages:")
                for row in field_level_impacts[:40]:
                    fields = ", ".join(row.get("matched_fields", [])[:8])
                    self.stdout.write(f"  - [{row['model']}] {row['page']} (score={row['score']})")
                    self.stdout.write(f"    fields: {fields}")
