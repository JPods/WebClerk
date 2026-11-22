"""Folders outside the backend are named once, in settings (Bill, 2026-11-22: fix the
locations). The frontend moved beside the backend and the readmes moved to the site
repository; code that still spelled the old places found nothing and said nothing."""
import re
from pathlib import Path

from django.conf import settings

from apps.ai_assistant.management.commands import index_docs

BACKEND = Path(settings.BASE_DIR)
OLD_PLACES = re.compile(r"""['"/]React2025['"/]|00WebClerk19|Documents/CommerceExpert|\.copilot-context""")


def test_the_frontend_setting_points_at_the_react_app():
    assert (settings.FRONTEND_DIR / "src" / "apps").is_dir()
    assert (settings.FRONTEND_DIR / "package.json").is_file()


def test_readers_of_the_frontend_use_the_setting():
    from apps.ai_assistant.services import watch_code, watch_layouts, watch_schemas
    from apps.core.management.commands import create_layout_status
    assert watch_code.REACT_ROOT == settings.FRONTEND_DIR / "src"
    assert watch_layouts.R25_ROOT == watch_schemas.R25_ROOT == settings.FRONTEND_DIR
    assert create_layout_status.R25_APPS_DIR == str(settings.FRONTEND_DIR / "src" / "apps")


def test_every_code_source_of_the_index_exists():
    """A source folder that is not there is a stale location, except the published
    readmes, which an instance may not have."""
    missing = [f"{key}: {path}" for key, cfg in index_docs.SOURCE_CONFIGS.items()
               for path in cfg["paths"] if path != index_docs.DOCS and not path.exists()]
    assert missing == []


def test_every_code_source_of_the_index_finds_files():
    cmd = index_docs.Command()
    empty = [key for key, cfg in index_docs.SOURCE_CONFIGS.items()
             if not [p for p in cfg["paths"] if p != index_docs.DOCS] == [] and not cmd._collect_files(
                 {**cfg, "paths": [p for p in cfg["paths"] if p != index_docs.DOCS]})]
    assert empty == []


def test_set_aside_folders_are_not_indexed(tmp_path):
    for rel in ("guide.md", "archive/old.md", "_archive/older.md", "junkdrawer/note.md",
                "node_modules/pkg/readme.md"):
        f = tmp_path / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("x")
    found = index_docs.Command()._collect_files({"paths": [tmp_path], "extensions": {".md"}})
    assert [p.name for p in found] == ["guide.md"]


def test_a_document_name_carries_no_machine_folders():
    assert index_docs.doc_id_for(BACKEND / "apps" / "sync" / "models.py") == "backend/apps/sync/models.py"
    assert index_docs.doc_id_for(settings.FRONTEND_DIR / "src" / "App.tsx") == "frontend/src/App.tsx"
    if index_docs.DOCS:
        assert index_docs.doc_id_for(index_docs.DOCS / "ai" / "x.md") == "readmes/ai/x.md"


def test_no_code_names_the_old_places():
    offenders = []
    for path in list((BACKEND / "apps").rglob("*.py")) + list((BACKEND / "tools").rglob("*.sh")):
        if "migrations" in path.parts or "__pycache__" in path.parts:
            continue
        if OLD_PLACES.search(path.read_text(errors="ignore")):
            offenders.append(str(path.relative_to(BACKEND)))
    assert offenders == []
