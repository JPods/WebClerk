"""
Django system checks for copilot instruction file sync.

Runs automatically during `runserver` and `python manage.py check`.
Warns when git_bypass/copilot.instructions.md has been updated (pulled)
but not copied to .github/instructions/copilot.instructions.md (the
location VS Code / Copilot actually reads).
"""
import hashlib
from pathlib import Path

from django.conf import settings
from django.core.checks import Warning, register


BYPASS = Path(settings.BASE_DIR) / "git_bypass" / "copilot.instructions.md"
ACTIVE = (
    Path(settings.BASE_DIR)
    / ".github"
    / "instructions"
    / "copilot.instructions.md"
)


def _file_hash(path: Path) -> str | None:
    """Return SHA-256 hex digest of a file, or None if missing."""
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


@register()
def check_instructions_sync(app_configs, **kwargs):
    """W001: git_bypass instructions updated but not synced to .github."""
    errors = []

    bypass_hash = _file_hash(BYPASS)
    active_hash = _file_hash(ACTIVE)

    if bypass_hash is None:
        # git_bypass file doesn't exist — nothing to check
        return errors

    if active_hash is None:
        errors.append(
            Warning(
                "Copilot instructions missing from active location.",
                hint=(
                    f"Copy git_bypass/copilot.instructions.md → "
                    f".github/instructions/copilot.instructions.md\n"
                    f"  cp git_bypass/copilot.instructions.md "
                    f".github/instructions/copilot.instructions.md"
                ),
                id="copilot.W001",
            )
        )
    elif bypass_hash != active_hash:
        errors.append(
            Warning(
                "git_bypass/copilot.instructions.md has been updated but "
                ".github/instructions/copilot.instructions.md is out of sync.",
                hint=(
                    "Run:\n"
                    "  cp git_bypass/copilot.instructions.md "
                    ".github/instructions/copilot.instructions.md\n"
                    "This ensures Copilot reads the latest team instructions."
                ),
                id="copilot.W002",
            )
        )

    return errors
