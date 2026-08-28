"""alice_admin_update — Update all admin.py list_display and detail ordering.

For every registered ModelAdmin in apps/:
  • Adds  # Scalar fields: ...  reference comment to each admin class.
  • Updates list_display to the 8 most useful scalar DB fields.
  • Adds ScalarFirstFieldsetMixin to the inheritance chain for classes that
    don't already have a fieldsets mixin (ScalarFirstFieldsetMixin,
    JSONBFieldsetMixin, or an explicit fieldsets attribute).

Usage:
  manage.py alice_admin_update               # dry-run, show what would change
  manage.py alice_admin_update --apply       # write changes to admin.py files
"""
from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path

from django.contrib import admin
from django.core.management.base import BaseCommand
from django.db import models as dj_models

from apps.ai_assistant.services.setting_overrides import load_validated_to_alice_overrides

# ---------------------------------------------------------------------------
# Field preference heuristics
# ---------------------------------------------------------------------------

# Scalars pulled toward the front of list_display (in order of preference)
PREFERRED = [
    "ida",
    "name", "display_name",
    "number", "code", "title", "sku",
    "description", "status", "type", "kind",
    "email", "phone", "company",
]

# Always appended last (after the 6 preferred slots are filled)
APPEND_LAST = ["is_active", "dt_created"]

# Never appear in list_display (system / audit fields)
SYSTEM = {"id", "uuid", "version", "is_deleted", "is_archived", "dt_modified"}

# A fieldsets-style mixin already present in the codebase; don't double-add.
FIELDSET_MIXIN_NAMES = {"ScalarFirstFieldsetMixin", "JSONBFieldsetMixin"}

WC3_ROOT = Path(__file__).resolve().parents[4]  # webClerk3/


# ---------------------------------------------------------------------------
# Field utilities
# ---------------------------------------------------------------------------

def _model_fields(model) -> tuple[list[str], list[str]]:
    """Return (sorted_scalar_names, sorted_json_names) for *model*."""
    scalars: list[str] = []
    json_fields: list[str] = []
    for field in model._meta.get_fields():
        if not hasattr(field, "column"):
            continue  # skip reverse-relations
        if isinstance(field, dj_models.JSONField):
            json_fields.append(field.name)
        elif isinstance(field, (dj_models.ForeignKey, dj_models.OneToOneField)):
            pass  # skip FK _id columns
        else:
            scalars.append(field.name)
    return sorted(set(scalars) - {"id"}), sorted(json_fields)


def _pick_8(scalars: list[str]) -> list[str]:
    """Return up to 8 scalars: preferred order first, then alpha, then append_last."""
    result: list[str] = []
    remaining = list(scalars)

    for pref in PREFERRED:
        if pref in remaining and pref not in SYSTEM:
            result.append(pref)
            remaining.remove(pref)
        if len(result) >= 6:
            break

    if len(result) < 6:
        filler = sorted(f for f in remaining if f not in SYSTEM and f not in APPEND_LAST)
        for f in filler:
            result.append(f)
            if len(result) >= 6:
                break

    for f in APPEND_LAST:
        if f in scalars and f not in result:
            result.append(f)

    return result


# ---------------------------------------------------------------------------
# Source-file text manipulation
# ---------------------------------------------------------------------------

def _format_list_display(fields: list[str], indent: str) -> str:
    fields_str = ", ".join(f'"{f}"' for f in fields)
    return f"{indent}list_display = ({fields_str})"


def _class_has_fieldsets_mixin(class_node: ast.ClassDef) -> bool:
    """True if any base class name is a known fieldsets mixin."""
    for base in class_node.bases:
        name = None
        if isinstance(base, ast.Name):
            name = base.id
        elif isinstance(base, ast.Attribute):
            name = base.attr
        if name and name in FIELDSET_MIXIN_NAMES:
            return True
    return False


def _class_has_explicit_fieldsets(class_node: ast.ClassDef) -> bool:
    """True if the class body directly assigns fieldsets = ..."""
    for stmt in class_node.body:
        if isinstance(stmt, ast.Assign):
            for t in stmt.targets:
                if isinstance(t, ast.Name) and t.id == "fieldsets":
                    return True
    return False


def _find_list_display_node(class_node: ast.ClassDef):
    """Return the Assign AST node for list_display, or None."""
    for stmt in class_node.body:
        if isinstance(stmt, ast.Assign):
            for t in stmt.targets:
                if isinstance(t, ast.Name) and t.id == "list_display":
                    return stmt
    return None


def _find_assign_node(class_node: ast.ClassDef, target_name: str):
    for stmt in class_node.body:
        if isinstance(stmt, ast.Assign):
            for t in stmt.targets:
                if isinstance(t, ast.Name) and t.id == target_name:
                    return stmt
    return None


def _format_detail_order_override(fields: list[str], indent: str) -> str:
    fields_str = ", ".join(f'"{field}"' for field in fields)
    return f"{indent}detail_order_override = ({fields_str})"


def _indent_of_line(line: str) -> str:
    return line[: len(line) - len(line.lstrip())]


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = (
        "Update admin.py files: set list_display to 8 best scalars, add "
        "scalar reference comment, add ScalarFirstFieldsetMixin where needed."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            default=False,
            help="Actually write changes (default: dry-run, show diff only)",
        )
        parser.add_argument(
            "--app",
            default=None,
            help="Restrict to a single app label (e.g. products)",
        )

    def handle(self, *args, **options):
        apply = options["apply"]
        dry_run = not apply
        app_filter = options.get("app")

        # ---- Build file → [(model, admin_class)] map --------------------
        model_fields_by_name: dict[str, dict[str, list[str]]] = {}
        for model, admin_obj in admin.site._registry.items():
            if not model.__module__.startswith("apps."):
                continue
            model_fields_by_name[model._meta.model_name] = {
                "scalar_fields": _model_fields(model)[0],
                "jsonb_fields": _model_fields(model)[1],
            }

        override_map, override_audit = load_validated_to_alice_overrides(WC3_ROOT, model_fields_by_name)

        file_map: dict[Path, list[tuple]] = {}
        for model, admin_obj in admin.site._registry.items():
            if not model.__module__.startswith("apps."):
                continue
            if app_filter and not model.__module__.startswith(f"apps.{app_filter}."):
                continue

            admin_cls = type(admin_obj)

            # Skip dynamically-generated classes (e.g. _proxy_admin closures)
            try:
                src_file = Path(inspect.getfile(admin_cls)).resolve()
            except (TypeError, OSError):
                continue

            if not src_file.suffix == ".py":
                continue
            if not src_file.exists():
                continue
            # Only files within our WC3 apps/
            try:
                src_file.relative_to(WC3_ROOT / "apps")
            except ValueError:
                continue

            file_map.setdefault(src_file, []).append((model, admin_cls))

        # ---- Check if we need to add mixin import to each file ----------
        # (done after the per-file loop below; track which files need it)

        total_files = 0
        total_classes = 0

        for src_file, entries in sorted(file_map.items()):
            rel = src_file.relative_to(WC3_ROOT)

            # Parse AST once per file
            text = src_file.read_text(encoding="utf-8")
            try:
                tree = ast.parse(text)
            except SyntaxError as exc:
                self.stderr.write(f"  SyntaxError in {rel}: {exc}")
                continue

            # Build name→ClassDef map for classes in this file
            class_nodes: dict[str, ast.ClassDef] = {
                node.name: node
                for node in ast.walk(tree)
                if isinstance(node, ast.ClassDef)
            }

            class_updates = []
            file_needs_mixin_import = False

            for model, admin_cls in entries:
                node = class_nodes.get(admin_cls.__name__)
                if node is None:
                    continue  # dynamic/proxy class not found in AST

                # Skip classes defined inside function bodies (e.g. proxy admin
                # factories). They inherit from a named parent that we do update.
                if "<locals>" in getattr(admin_cls, "__qualname__", ""):
                    continue

                scalars, json_fields = _model_fields(model)
                best_8 = _pick_8(scalars)
                override = override_map.get(model._meta.model_name, {})
                if override.get("list_display"):
                    best_8 = list(override["list_display"])

                # Determine whether to add ScalarFirstFieldsetMixin
                has_mixin = _class_has_fieldsets_mixin(node)
                has_explicit = _class_has_explicit_fieldsets(node)
                need_mixin = not has_mixin and not has_explicit

                # Runtime MRO check: if any *app* parent class already defines
                # fieldsets (e.g. OrgBaseAdmin), don't add the mixin — the proxy
                # inherits that fieldsets definition.
                has_inherited_fieldsets = any(
                    cls.__dict__.get("fieldsets") is not None
                    for cls in admin_cls.__mro__[1:]
                    if getattr(cls, "__module__", "").startswith("apps.")
                )
                if has_inherited_fieldsets:
                    need_mixin = False

                if need_mixin:
                    file_needs_mixin_import = True

                class_updates.append(
                    {
                        "node": node,
                        "model": model,
                        "scalars": scalars,
                        "json_fields": json_fields,
                        "best_8": best_8,
                        "detail_order_override": list(override.get("detail_order", [])),
                        "need_mixin": need_mixin,
                    }
                )

            # Deduplicate: proxy models may share the same admin class name.
            # Process each class name only once to prevent stacked patches.
            seen_class_names: set = set()
            unique_updates = []
            for info in class_updates:
                cname = info["node"].name
                if cname not in seen_class_names:
                    seen_class_names.add(cname)
                    unique_updates.append(info)
            class_updates = unique_updates

            if not class_updates:
                continue

            n = _apply_combined(
                src_file, text, class_updates,
                file_needs_mixin_import, dry_run, self.stdout
            )

            if n:
                total_files += 1
                total_classes += n
                self.stdout.write(f"  {'[dry-run] ' if dry_run else ''}updated {n} class(es) in {rel}")

        verb = "Would update" if dry_run else "Updated"
        self.stdout.write(
            f"\n{verb} {total_classes} admin class(es) across {total_files} file(s)."
        )
        if override_audit["applied"]:
            self.stdout.write(f"Consumed {len(override_audit['applied'])} To_Alice override(s).")
        if dry_run:
            self.stdout.write("Run with --apply to write changes.")


# ---------------------------------------------------------------------------
# Combined patch helper (handles both import insertion + class body changes)
# ---------------------------------------------------------------------------

_MIXIN_IMPORT = "from common.admin_mixins import ScalarFirstFieldsetMixin\n"


def _ensure_mixin_import(text: str, dry_run: bool, rel, stdout) -> str:
    """Return text with ScalarFirstFieldsetMixin import present (or already there)."""
    if "ScalarFirstFieldsetMixin" in text:
        return text  # already imported (maybe from local def or existing import)
    # Insert after the last 'from common.' or 'from django.' import line, else at top
    lines = text.splitlines(keepends=True)
    insert_at = 0
    for i, line in enumerate(lines):
        if line.startswith("from common.") or line.startswith("from django."):
            insert_at = i + 1
    lines.insert(insert_at, _MIXIN_IMPORT)
    return "".join(lines)


def _apply_combined(
    src_file: Path,
    text: str,
    class_updates: list[dict],
    need_import: bool,
    dry_run: bool,
    stdout,
) -> int:
    """Build final patched text from *text* (possibly already import-patched) and write it."""
    # Re-parse the (possibly import-patched) text because line numbers shifted
    if need_import:
        patched_text = _ensure_mixin_import(text, dry_run=False, rel=None, stdout=stdout)
    else:
        patched_text = text

    try:
        tree = ast.parse(patched_text)
    except SyntaxError:
        return 0

    # Rebuild class node map from new text
    class_nodes: dict[str, ast.ClassDef] = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
    }

    # Re-associate updates with new AST nodes
    refreshed_updates = []
    for info in class_updates:
        cls_name = info["node"].name
        new_node = class_nodes.get(cls_name)
        if new_node is None:
            continue
        refreshed_updates.append({**info, "node": new_node})

    lines = patched_text.splitlines(keepends=True)
    patches: list[tuple[int, int, list[str]]] = []

    for info in refreshed_updates:
        node: ast.ClassDef = info["node"]
        scalars: list[str] = info["scalars"]
        best_8: list[str] = info["best_8"]
        detail_order_override: list[str] = info.get("detail_order_override", [])
        need_mixin: bool = info["need_mixin"]

        first_body_lineno = node.body[0].lineno
        body_line = lines[first_body_lineno - 1]
        indent = _indent_of_line(body_line)

        # 1. list_display replacement / insertion
        ld_node = _find_list_display_node(node)
        new_display = _format_list_display(best_8, indent) + "\n"
        if ld_node is not None:
            ld_0 = ld_node.lineno - 1        # 0-based start (inclusive)
            ld_1 = ld_node.end_lineno        # 0-based end (exclusive)
            patches.append((ld_0, ld_1, [new_display]))
        else:
            # No list_display at all — insert at start of class body
            ld_0 = first_body_lineno - 1
            patches.append((ld_0, ld_0, [new_display]))

        # 2. Scalar reference comment — goes RIGHT BEFORE list_display.
        #    Check if one already exists on the line immediately above ld_0.
        scalar_comment_text = f"{indent}# Scalar fields: {', '.join(scalars)}\n"
        comment_above = lines[ld_0 - 1] if ld_0 > 0 else ""
        if "# Scalar fields:" in comment_above:
            # Update existing comment in-place (one line above list_display)
            patches.append((ld_0 - 1, ld_0, [scalar_comment_text]))
        else:
            # Insert comment immediately before list_display.
            # Both insert (ld_0, ld_0) and replace (ld_0, ld_1) have start=ld_0.
            # Sorting DESC by (start, end) ensures replacement runs first so the
            # insert lands above the new list_display, not the old one.
            patches.append((ld_0, ld_0, [scalar_comment_text]))

        # 3. detail_order_override for ScalarFirstFieldsetMixin-backed admins.
        detail_node = _find_assign_node(node, "detail_order_override")
        if detail_order_override:
            new_detail_line = _format_detail_order_override(detail_order_override, indent) + "\n"
            insert_line = ld_1 if ld_node is not None else ld_0 + 1
            if detail_node is not None:
                patches.append((detail_node.lineno - 1, detail_node.end_lineno, [new_detail_line]))
            else:
                patches.append((insert_line, insert_line, [new_detail_line]))
        elif detail_node is not None:
            patches.append((detail_node.lineno - 1, detail_node.end_lineno, []))

        # 4. Mixin in inheritance
        if need_mixin:
            class_line_idx = node.lineno - 1
            class_line = lines[class_line_idx]
            new_class_line = re.sub(
                r"(class\s+\w+\s*\()",
                r"\1ScalarFirstFieldsetMixin, ",
                class_line,
                count=1,
            )
            if new_class_line != class_line:
                patches.append((class_line_idx, class_line_idx + 1, [new_class_line]))

    if not patches:
        return 0

    # Sort DESC by (start, end) so that at equal start positions, replacements
    # (larger end) run before insertions (end == start), preserving correctness.
    patches.sort(key=lambda x: (x[0], x[1]), reverse=True)
    new_lines = list(lines)
    for start, end, replacement in patches:
        new_lines[start:end] = replacement

    new_text = "".join(new_lines)

    if new_text == text and not need_import:
        return 0

    if dry_run:
        import difflib
        orig_lines = text.splitlines(keepends=True)
        diff = difflib.unified_diff(orig_lines, new_lines, n=2)
        stdout.write("".join(list(diff)[:140]))
    else:
        src_file.write_text(new_text, encoding="utf-8")

    return len(refreshed_updates)
