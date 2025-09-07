import io
import json
import shutil
import uuid
from pathlib import Path

import pytest
from django.core.management import call_command
from apps.docs.models.document import Document


pytestmark = pytest.mark.django_db


def _parse_summary(out: str) -> dict:
    """Extract Created/Updated/Unchanged/Discovered counts from summary line."""
    metrics = {}
    for line in out.splitlines():
        if line.startswith("Sync complete."):
            parts = line.split()
            for p in parts:
                if '=' in p:
                    k, v = p.split('=')
                    v = v.rstrip('.')
                    if v.isdigit():
                        metrics[k] = int(v)
    return metrics


def _make_root() -> Path:
    root_name = f"test_readmes_{uuid.uuid4().hex[:8]}"
    root = Path(root_name)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _run_command(**opts):
    buf = io.StringIO()
    call_command('sync_readmes', stdout=buf, stderr=buf, **opts)
    return buf.getvalue()


def test_sync_readmes_create_and_slug_collision(monkeypatch):
    # Isolate existing docs
    Document.objects.filter(model_name='readme').delete()
    root = _make_root()
    # create two README.md in different subfolders -> different slugs
    (root / 'a').mkdir()
    (root / 'b').mkdir()
    (root / 'a' / 'README.md').write_text('# Alpha Title\nBody A', encoding='utf-8')
    (root / 'b' / 'README.md').write_text('# Beta Title\nBody B', encoding='utf-8')

    # monkeypatch the command roots
    import apps.docs.management.commands.sync_readmes as mod
    monkeypatch.setattr(mod, 'README_ROOTS', [root.as_posix()])

    out = _run_command()
    metrics = _parse_summary(out)
    assert metrics.get('Created') == 2, out
    docs = list(Document.objects.filter(model_name='readme'))
    slugs = {d.slug for d in docs}
    # Expect slugs to incorporate parent folder names (a-readme / b-readme or similar)
    assert len(slugs) == 2
    for s in slugs:
        assert s and 'readme' in s


def test_sync_readmes_update_and_unchanged(monkeypatch):
    Document.objects.filter(model_name='readme').delete()
    root = _make_root()
    f1 = root / 'guide.md'
    f2 = root / 'plan.md'
    f1.write_text('# Guide\nInitial', encoding='utf-8')
    f2.write_text('# Plan\nInitial', encoding='utf-8')
    import apps.docs.management.commands.sync_readmes as mod
    monkeypatch.setattr(mod, 'README_ROOTS', [root.as_posix()])
    _run_command()
    # modify one file
    f1.write_text('# Guide\nChanged content', encoding='utf-8')
    out = _run_command()
    metrics = _parse_summary(out)
    # One updated, one unchanged
    assert metrics.get('Updated') == 1, out
    assert metrics.get('Unchanged') == 1, out


def test_sync_readmes_delete_missing(monkeypatch):
    Document.objects.filter(model_name='readme').delete()
    root = _make_root()
    f1 = root / 'keep.md'
    f2 = root / 'drop.md'
    f1.write_text('# Keep\nBody', encoding='utf-8')
    f2.write_text('# Drop\nBody', encoding='utf-8')
    import apps.docs.management.commands.sync_readmes as mod
    monkeypatch.setattr(mod, 'README_ROOTS', [root.as_posix()])
    _run_command()
    # remove second file
    f2.unlink()
    out = _run_command(delete_missing=True)
    metrics = _parse_summary(out)
    assert Document.objects.filter(model_name='readme').count() == 1
    # No new creations expected
    assert metrics.get('Created') == 0


def test_sync_readmes_truncate_and_export_index(monkeypatch, tmp_path):
    Document.objects.filter(model_name='readme').delete()
    root = _make_root()
    big_content = '# Big File\n' + ('A' * 5000)
    (root / 'big.md').write_text(big_content, encoding='utf-8')
    import apps.docs.management.commands.sync_readmes as mod
    monkeypatch.setattr(mod, 'README_ROOTS', [root.as_posix()])
    index_path = tmp_path / 'test_docs_index.json'
    out = _run_command(max_bytes=100, truncate=True, export_index=True, index_path=str(index_path))
    metrics = _parse_summary(out)
    assert metrics.get('Created') == 1
    doc = Document.objects.filter(model_name='readme').first()
    assert doc is not None
    assert doc.body is not None
    assert len(doc.body.encode('utf-8')) <= 100  # truncated
    assert isinstance(doc.data, dict)
    assert doc.data.get('truncated') is True
    # Index file produced
    assert index_path.exists()
    data = json.loads(index_path.read_text(encoding='utf-8'))
    assert len(data) == 1
    assert data[0]['slug'] == doc.slug


@pytest.fixture(autouse=True)
def _cleanup_dirs():
    # After each test, remove any test_readmes_* directories
    yield
    for p in Path('.').glob('test_readmes_*'):
        try:
            shutil.rmtree(p)
        except Exception:
            pass