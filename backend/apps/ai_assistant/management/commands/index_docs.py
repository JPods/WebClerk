"""
Management command: index_docs

Reads the published readmes, the backend code and the React app,
then indexes them into the document index (DocChunk rows) for RAG retrieval.

Usage:
    python manage.py index_docs                  # index everything
    python manage.py index_docs --source readmes # only readmes
    python manage.py index_docs --reset          # wipe and rebuild
    python manage.py index_docs --stats          # show index stats
"""
import time
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.ai_assistant.services.vector_store import VectorStoreManager

# ── Where the sources are ───────────────────────────────────────────
# Three roots, each named once in settings: the backend (BASE_DIR), the React app
# (FRONTEND_DIR) and the published readmes (DOCS_DIR, which an instance may not have).

BASE = Path(settings.BASE_DIR)
FRONTEND = Path(settings.FRONTEND_DIR)
DOCS = Path(settings.DOCS_DIR) if settings.DOCS_DIR else None
REPO_ROOT = BASE.parent

# Folders never indexed: build output, dependencies, and set-aside material that would
# teach Alice what we no longer do.
SKIP_PARTS = frozenset({"__pycache__", "node_modules", ".git", "migrations", "venv", "venv312",
                        "archive", "_archive", "junkdrawer", "__tests__", "dist"})

SOURCE_CONFIGS = {
    "readmes": {
        "label": "Readmes & Documentation",
        "paths": ([DOCS] if DOCS else []) + [FRONTEND / "src"],
        "extensions": {".md", ".txt", ".rst"},
        "type": "documentation",
    },
    "instructions": {
        "label": "Team Instructions",
        "paths": [BASE / ".github" / "instructions", FRONTEND / ".github" / "instructions"],
        "extensions": {".md"},
        "type": "instructions",
    },
    "models": {
        "label": "Django Model Definitions",
        "paths": [BASE / "apps", BASE / "common"],
        "extensions": {".py"},
        "file_patterns": ["models.py", "models/"],
        "type": "code_models",
    },
    "services": {
        "label": "Django Services & Business Logic",
        "paths": [BASE / "apps"],
        "extensions": {".py"},
        "file_patterns": ["services/"],
        "type": "code_services",
    },
    "views": {
        "label": "Django Views & API Endpoints",
        "paths": [BASE / "apps"],
        "extensions": {".py"},
        "file_patterns": ["views.py", "views/", "urls.py"],
        "type": "code_views",
    },
    "settings": {
        "label": "Django Settings & Configuration",
        "paths": [BASE / "webclerk3_api"],
        "extensions": {".py"},
        "file_patterns": ["settings.py", "urls.py", "celery.py"],
        "type": "code_config",
    },
    "tasks": {
        "label": "Celery Tasks & Management Commands",
        "paths": [BASE / "apps"],
        "extensions": {".py"},
        "file_patterns": ["tasks.py", "tasks/", "management/commands/"],
        "type": "code_tasks",
    },
    "tests": {
        "label": "Test Files",
        "paths": [BASE / "tests"],
        "extensions": {".py"},
        "file_patterns": ["test_", "conftest.py"],
        "type": "code_tests",
    },
    "common": {
        "label": "Common / Shared Utilities",
        "paths": [BASE / "common"],
        "extensions": {".py"},
        "type": "code_common",
    },
    "react_api": {
        "label": "React API Layer & Types",
        "paths": [FRONTEND / "src" / "api", FRONTEND / "src" / "type"],
        "extensions": {".ts", ".tsx"},
        "type": "code_react_api",
    },
    "react_apps": {
        "label": "React Pages & Components",
        "paths": [FRONTEND / "src" / "apps"],
        "extensions": {".ts", ".tsx"},
        "type": "code_react_apps",
    },
    "alice_knowledge": {
        "label": "Alice Knowledge Base",
        "paths": [BASE / "apps" / "ai_assistant" / "data"],
        "extensions": {".md", ".json"},
        "type": "alice_knowledge",
    },
}


def doc_id_for(filepath: Path) -> str:
    """A stable name for a file that does not carry this machine's folders: readmes/<path>
    under DOCS_DIR, else the path inside the repository."""
    if DOCS:
        try:
            return "readmes/" + filepath.relative_to(DOCS).as_posix()
        except ValueError:
            pass
    return filepath.relative_to(REPO_ROOT).as_posix()


class Command(BaseCommand):
    help = "Index project documentation and code into the document index for AI assistant RAG"

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
            help="Wipe the document index before indexing",
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
                f"Documents: {stats['documents']}\n"
                f"Embedding model: {stats['embed_model']}"
            ))
            return

        if options["reset"]:
            self.stdout.write(self.style.WARNING("Emptying the document index..."))
            vs.reset()

        sources = (
            SOURCE_CONFIGS
            if options["source"] == "all"
            else {options["source"]: SOURCE_CONFIGS[options["source"]]}
        )

        total_files = 0
        total_chunks = 0
        empty = []
        start_time = time.time()

        for key, config in sources.items():
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(self.style.HTTP_INFO(f"Indexing: {config['label']}"))
            self.stdout.write(f"{'='*60}")

            files = self._collect_files(config)
            self.stdout.write(f"Found {len(files)} files")
            if not files:
                empty.append(key)

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

                    doc_id = doc_id_for(filepath)

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
        if not DOCS:
            self.stdout.write(self.style.WARNING(
                "DOCS_DIR is not set: no published readmes are in the index."))
        if empty:
            self.stdout.write(self.style.WARNING(
                f"Sources that found no files: {', '.join(empty)}. Check FRONTEND_DIR and DOCS_DIR."))

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

                if SKIP_PARTS.intersection(filepath.relative_to(search_path).parts):
                    continue

                # If file_patterns specified, only include matching paths
                if file_patterns:
                    rel = str(filepath)
                    if not any(pat in rel for pat in file_patterns):
                        continue

                files.append(filepath)

        return sorted(files)
