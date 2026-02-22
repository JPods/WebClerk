"""
Management command: index_docs

Crawls the project's documentation, code docstrings, and 4D methods,
then indexes them into ChromaDB for RAG retrieval.

Usage:
    python manage.py index_docs                  # index everything
    python manage.py index_docs --source readmes # only readmes
    python manage.py index_docs --reset          # wipe and rebuild
    python manage.py index_docs --stats          # show index stats
"""
import os
import time
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.ai_assistant.services.vector_store import VectorStoreManager

# ── Source directories ──────────────────────────────────────────────

BASE = Path(settings.BASE_DIR)

# Workspace roots (relative to the workspace, not just wc3)
WORKSPACE_ROOT = BASE.parent  # /Users/.../CommerceExpert/

SOURCE_CONFIGS = {
    "readmes": {
        "label": "Readmes & Documentation",
        "paths": [
            BASE / "readmes",
            WORKSPACE_ROOT / "React2025" / "readmes",
        ],
        "extensions": {".md", ".txt", ".rst"},
        "type": "documentation",
    },
    "instructions": {
        "label": "Copilot / Team Instructions",
        "paths": [
            BASE / ".github" / "instructions",
            WORKSPACE_ROOT / "React2025" / ".github" / "instructions",
        ],
        "extensions": {".md"},
        "type": "instructions",
    },
    "models": {
        "label": "Django Model Definitions",
        "paths": [
            BASE / "apps",
            BASE / "common",
        ],
        "extensions": {".py"},
        "file_patterns": ["models.py", "models/"],
        "type": "code_models",
    },
    "services": {
        "label": "Django Services & Business Logic",
        "paths": [
            BASE / "apps",
        ],
        "extensions": {".py"},
        "file_patterns": ["services/"],
        "type": "code_services",
    },
    "views": {
        "label": "Django Views & API Endpoints",
        "paths": [
            BASE / "apps",
        ],
        "extensions": {".py"},
        "file_patterns": ["views.py", "views/", "urls.py"],
        "type": "code_views",
    },
    "settings": {
        "label": "Django Settings & Configuration",
        "paths": [
            BASE / "webclerk3_api",
        ],
        "extensions": {".py"},
        "file_patterns": ["settings.py", "urls.py", "celery.py"],
        "type": "code_config",
    },
    "tasks": {
        "label": "Celery Tasks & Management Commands",
        "paths": [
            BASE / "apps",
        ],
        "extensions": {".py"},
        "file_patterns": ["tasks.py", "tasks/", "management/commands/"],
        "type": "code_tasks",
    },
    "tests": {
        "label": "Test Files",
        "paths": [
            BASE / "tests",
            BASE,  # root-level test_*.py files
        ],
        "extensions": {".py"},
        "file_patterns": ["test_", "conftest.py"],
        "type": "code_tests",
    },
    "common": {
        "label": "Common / Shared Utilities",
        "paths": [
            BASE / "common",
        ],
        "extensions": {".py"},
        "type": "code_common",
    },
    "4d_methods": {
        "label": "4D Legacy Methods",
        "paths": [
            WORKSPACE_ROOT / "00WebClerk19" / "Project" / "Sources" / "Methods",
            WORKSPACE_ROOT / "00WebClerk19" / "Project" / "Sources" / "Classes",
            WORKSPACE_ROOT / "00WebClerk19" / "Project" / "Sources" / "DatabaseMethods",
        ],
        "extensions": {".4dm"},
        "type": "4d_code",
    },
    "react_types": {
        "label": "React TypeScript Types & Interfaces",
        "paths": [
            WORKSPACE_ROOT / "React2025" / "src" / "model",
            WORKSPACE_ROOT / "React2025" / "src" / "type",
        ],
        "extensions": {".ts", ".tsx"},
        "type": "code_types",
    },
    "react_services": {
        "label": "React API Services & SDK",
        "paths": [
            WORKSPACE_ROOT / "React2025" / "src" / "api",
            WORKSPACE_ROOT / "React2025" / "src" / "apps",
        ],
        "extensions": {".ts", ".tsx"},
        "file_patterns": ["Api.ts", "api.ts", "Service.ts", "service.ts", "SDK", "sdk"],
        "type": "code_react_services",
    },
    "react_pages": {
        "label": "React Pages & Components",
        "paths": [
            WORKSPACE_ROOT / "React2025" / "src" / "apps",
        ],
        "extensions": {".ts", ".tsx"},
        "file_patterns": ["Page.tsx", "page.tsx"],
        "type": "code_react_pages",
    },
    "copilot_context": {
        "label": "Copilot Context Files",
        "paths": [
            BASE / ".copilot-context",
        ],
        "extensions": {".md", ".json"},
        "type": "copilot_context",
    },
}


class Command(BaseCommand):
    help = "Index project documentation and code into ChromaDB for AI assistant RAG"

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            type=str,
            choices=list(SOURCE_CONFIGS.keys()) + ["all"],
            default="all",
            help="Which source category to index (default: all)",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Wipe the vector store before indexing",
        )
        parser.add_argument(
            "--stats",
            action="store_true",
            help="Show index statistics and exit",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be indexed without actually indexing",
        )

    def handle(self, *args, **options):
        vs = VectorStoreManager()

        if options["stats"]:
            stats = vs.stats()
            self.stdout.write(self.style.SUCCESS(
                f"Collection: {stats['collection']}\n"
                f"Chunks indexed: {stats['count']}\n"
                f"Persist dir: {stats['persist_dir']}"
            ))
            return

        if options["reset"]:
            self.stdout.write(self.style.WARNING("Resetting vector store..."))
            vs.reset()

        sources = (
            SOURCE_CONFIGS
            if options["source"] == "all"
            else {options["source"]: SOURCE_CONFIGS[options["source"]]}
        )

        total_files = 0
        total_chunks = 0
        start_time = time.time()

        for key, config in sources.items():
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(self.style.HTTP_INFO(f"Indexing: {config['label']}"))
            self.stdout.write(f"{'='*60}")

            files = self._collect_files(config)
            self.stdout.write(f"Found {len(files)} files")

            if options["dry_run"]:
                for f in files[:10]:
                    self.stdout.write(f"  {f}")
                if len(files) > 10:
                    self.stdout.write(f"  ... and {len(files) - 10} more")
                continue

            for filepath in files:
                try:
                    content = filepath.read_text(encoding="utf-8", errors="ignore")
                    if not content.strip():
                        continue

                    # Build a doc_id that's workspace-relative
                    try:
                        doc_id = str(filepath.relative_to(WORKSPACE_ROOT))
                    except ValueError:
                        doc_id = str(filepath)

                    metadata = {
                        "source": key,
                        "type": config["type"],
                        "file_ext": filepath.suffix,
                        "filename": filepath.name,
                    }

                    chunks = vs.index_document(doc_id, content, metadata)
                    total_chunks += chunks
                    total_files += 1

                    if total_files % 25 == 0:
                        self.stdout.write(f"  ... indexed {total_files} files ({total_chunks} chunks)")

                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"  Error indexing {filepath}: {e}"))

        elapsed = time.time() - start_time
        stats = vs.stats()

        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(self.style.SUCCESS(
            f"Indexing complete in {elapsed:.1f}s\n"
            f"  Files indexed: {total_files}\n"
            f"  Chunks created: {total_chunks}\n"
            f"  Total in store: {stats['count']}"
        ))

    def _collect_files(self, config: dict) -> list[Path]:
        """Collect all matching files for a source config."""
        files = []
        extensions = config.get("extensions", set())
        file_patterns = config.get("file_patterns", [])

        for search_path in config["paths"]:
            if not search_path.exists():
                self.stdout.write(self.style.WARNING(f"  Path not found: {search_path}"))
                continue

            for filepath in search_path.rglob("*"):
                if not filepath.is_file():
                    continue
                if filepath.suffix not in extensions:
                    continue

                # Skip common noise
                if any(
                    part in filepath.parts
                    for part in ("__pycache__", "node_modules", ".git", "migrations", "venv", "venv312")
                ):
                    continue

                # If file_patterns specified, only include matching paths
                if file_patterns:
                    rel = str(filepath)
                    if not any(pat in rel for pat in file_patterns):
                        continue

                files.append(filepath)

        return sorted(files)
