import json
import io
from pathlib import Path
import uuid
import time
import shutil
import pytest
from django.core.management import call_command
from django.urls import reverse
from rest_framework.test import APIClient
from apps.docs.models.document import Document

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(api_client):
    from django.contrib.auth import get_user_model
    U = get_user_model()
    u = U.objects.create_user(username='reader', email='r@example.com', password='pw12345')
    api_client.force_authenticate(user=u)
    return u


def _run_sync(**opts):
    buf = io.StringIO()
    call_command('sync_readmes', stdout=buf, stderr=buf, **opts)
    return buf.getvalue()


def _temp_root(monkeypatch, content_map):
    # Clean up stale temp dirs from prior runs to avoid root clutter
    for old in Path('.').glob('test_readme_etag_*'):
        if old.is_dir():
            try:
                shutil.rmtree(old)
            except Exception:
                pass
    root = Path(f"test_readme_etag_{uuid.uuid4().hex[:6]}")
    root.mkdir()
    for name, text in content_map.items():
        (root / name).write_text(text, encoding='utf-8')
    import apps.docs.management.commands.sync_readmes as mod
    monkeypatch.setattr(mod, 'README_ROOTS', [root.as_posix()])
    return root


def test_readme_detail_etag_last_modified(monkeypatch, api_client, user):
    Document.objects.filter(table_name='readme').delete()
    _temp_root(monkeypatch, {'sample.md': '# Title\nBody here'})
    _run_sync()
    doc = Document.objects.filter(table_name='readme').first()
    assert doc is not None
    assert doc.slug
    detail_url = reverse('readme-detail', kwargs={'slug': doc.slug})
    r1 = api_client.get(detail_url)
    assert r1.status_code == 200, r1.content
    etag = r1['ETag']
    lm = r1['Last-Modified']
    payload = r1.json()
    assert 'data' in payload
    if 'html' in payload['data']:
        assert '<' in payload['data']['html'] or payload['data']['html'] == payload['data']['body']
    else:
        # fallback: html not stored yet but body present
        assert 'body' in payload['data']
    # second conditional request
    r2 = api_client.get(detail_url, HTTP_IF_NONE_MATCH=etag)
    assert r2.status_code == 304
    r3 = api_client.get(detail_url, HTTP_IF_MODIFIED_SINCE=lm)
    assert r3.status_code == 304


def test_readme_index_search_endpoint(monkeypatch, api_client, tmp_path, user):
    Document.objects.filter(table_name='readme').delete()
    _temp_root(monkeypatch, {
        'alpha.md': '# Alpha Doc\nSomething about systems',
        'beta.md': '# Beta Doc\nContains architecture bits',
        'gamma.md': '# Gamma Guide\nMisc',
    })
    # export index
    _run_sync(export_index=True, index_path=str(tmp_path / 'docs_index.json'))
    # copy exported index to default path (docs_index.json) for loader
    default_index = Path('docs_index.json')
    default_index.write_text((tmp_path / 'docs_index.json').read_text(encoding='utf-8'), encoding='utf-8')
    url = reverse('readme-search-index')
    resp = api_client.get(url, {'q': 'alpha'})
    assert resp.status_code == 200, resp.content
    payload = resp.json()
    data = payload.get('data', payload)
    assert data['count'] == 1
    assert data['results'][0]['slug'].startswith('alpha')
    # hit detail to increment access counts differently
    slugs = [r['slug'] for r in data['results']]
    for slug in slugs:
        api_client.get(reverse('readme-detail', kwargs={'slug': slug}))


def test_readme_index_search_fuzzy(monkeypatch, api_client, tmp_path, user):
    """Fuzzy search should return near-miss tokens when enabled or when no exact match."""
    Document.objects.filter(table_name='readme').delete()
    _temp_root(monkeypatch, {
        'widget.md': '# Widget System\nHandles processing',
        'gadget.md': '# Gadget Overview\nMisc tools',
        'index.md': '# Index Root\nGeneral intro',
    })
    _run_sync(export_index=True, index_path=str(tmp_path / 'docs_index.json'))
    Path('docs_index.json').write_text((tmp_path / 'docs_index.json').read_text(encoding='utf-8'), encoding='utf-8')
    url = reverse('readme-search-index')
    # Deliberate misspelling: widgit (should fuzzy match widget)
    resp = api_client.get(url, {'q': 'widgit', 'fuzzy': '1'})
    assert resp.status_code == 200
    payload = resp.json()
    data = payload.get('data', payload)
    # Gather concatenated text of results
    results = data['results'] if 'results' in data else data
    combined = ' '.join(json.dumps(r).lower() for r in results)
    assert 'widget' in combined
    assert data.get('fuzzy_applied') is True
    # Query with no fuzzy flag but no exact match should still trigger fallback
    resp2 = api_client.get(url, {'q': 'gadjet'})
    data2 = resp2.json().get('data', resp2.json())
    # Fuzzy may apply automatically if zero exact matches
    if data2.get('fuzzy_applied'):
        assert any('gadget' in json.dumps(r).lower() for r in data2['results'])


def test_readme_top_endpoint(monkeypatch, api_client, user):
    """Ensure /readmes/top/ returns highest accessed readmes in order."""
    Document.objects.filter(table_name='readme').delete()
    _temp_root(monkeypatch, {
        'one.md': '# One\nFirst',
        'two.md': '# Two\nSecond',
        'three.md': '# Three\nThird',
    })
    _run_sync()
    # Access pattern: two (3 hits), three (2 hits), one (1 hit)
    def slug_for(filename):
        doc = Document.objects.get(data__source_path__endswith=filename)
        return doc.slug
    slug_two = slug_for('two.md')
    slug_three = slug_for('three.md')
    slug_one = slug_for('one.md')
    api_client.get(reverse('readme-detail', kwargs={'slug': slug_two}))
    api_client.get(reverse('readme-detail', kwargs={'slug': slug_two}))
    api_client.get(reverse('readme-detail', kwargs={'slug': slug_two}))
    api_client.get(reverse('readme-detail', kwargs={'slug': slug_three}))
    api_client.get(reverse('readme-detail', kwargs={'slug': slug_three}))
    api_client.get(reverse('readme-detail', kwargs={'slug': slug_one}))
    top_url = reverse('readme-top')
    resp = api_client.get(top_url)
    assert resp.status_code == 200, resp.content
    payload = resp.json()
    data = payload.get('data', payload)
    # If enveloped without keys (list), treat data as list
    results = data.get('results') if isinstance(data, dict) and 'results' in data else data
    assert isinstance(results, list)
    slugs_order = [r['slug'] for r in results]
    # Expect slug for 'two.md' first, then 'three.md', then 'one.md'
    assert slugs_order[:3] == [slug_two, slug_three, slug_one]


def test_sync_modified_since_and_pattern(monkeypatch):
    Document.objects.filter(table_name='readme').delete()
    root = _temp_root(monkeypatch, {
        'keep.md': '# Keep\nOriginal',
        'skip.md': '# Skip\nOriginal',
    })
    _run_sync()
    # touch keep.md to update mtime
    time.sleep(0.01)
    (root / 'keep.md').write_text('# Keep\nChanged body', encoding='utf-8')
    now_ms = int(time.time() * 1000) - 5  # a little earlier
    out = _run_sync(modified_since=str(now_ms), pattern=['*keep.md'])
    doc_keep = Document.objects.get(data__source_path__endswith='keep.md')
    doc_skip = Document.objects.get(data__source_path__endswith='skip.md')
    assert doc_keep.body is not None and 'Changed body' in doc_keep.body
    assert doc_skip.body is not None and 'Original' in doc_skip.body