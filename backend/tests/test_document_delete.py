"""Document delete goes through the delete door, and the file goes only after the record.

Defect B-1 (2026-09-23): DocumentDeleteView removed the file first, then crashed on
``hasattr(doc)`` — so every delete left a record pointing at a file that no longer existed.
"""
import pytest

from tests.helpers.auth import make_authenticated_client

pytestmark = pytest.mark.django_db(transaction=True)   # on_commit must really fire


@pytest.fixture(autouse=True)
def _uploads_in_tmp(tmp_path, settings):
    settings.DATA_DIR = str(tmp_path / 'data')


def _doc(tmp_path, name='zz-doc-delete.txt', outside=False):
    """A document whose file WebClerk stored (under the uploads root), or one pointing at
    a file it does not own."""
    from apps.docs.models import Document
    from apps.docs.views.upload_view import _uploads_root
    folder = tmp_path / 'elsewhere' if outside else __import__('pathlib').Path(_uploads_root())
    folder.mkdir(parents=True, exist_ok=True)
    f = folder / name
    f.write_bytes(b'content')
    return Document.objects.create(name=name, path={'full': str(f)}), f


def test_delete_removes_the_record_and_then_the_file(tmp_path):
    from apps.docs.models import Document
    doc, f = _doc(tmp_path)

    response = make_authenticated_client().delete(f'/wcapi/document/{doc.pk}/delete/')

    assert response.status_code == 200, response.content
    assert not Document.objects.filter(pk=doc.pk).exists()
    assert not f.exists()


def test_a_refused_delete_keeps_both_the_record_and_the_file(tmp_path, monkeypatch):
    from apps.docs.models import Document
    doc, f = _doc(tmp_path, 'zz-doc-keep.txt')

    def _refuse(self, *args, **kwargs):
        raise RuntimeError('This document is cited by a posted invoice.')
    monkeypatch.setattr(Document, 'delete', _refuse)

    response = make_authenticated_client().delete(f'/wcapi/document/{doc.pk}/delete/')

    assert response.status_code == 409
    assert response.json()['error']['code'] == 'delete_refused'
    assert Document.objects.filter(pk=doc.pk).exists()
    assert f.exists(), "the file must outlive a refused delete"


def test_deleting_a_missing_document_is_404():
    response = make_authenticated_client().delete('/wcapi/document/99999999/delete/')
    assert response.status_code == 404


def test_a_file_webclerk_does_not_own_is_left_alone(tmp_path):
    """A document pointing at the user's own file (a SketchUp plugin, say): the record goes,
    the file stays."""
    from apps.docs.models import Document
    doc, f = _doc(tmp_path, 'my_geom.rb', outside=True)

    response = make_authenticated_client().delete(f'/wcapi/document/{doc.pk}/delete/')

    assert response.status_code == 200
    assert not Document.objects.filter(pk=doc.pk).exists()
    assert f.exists(), "deleting a record must never delete a file WebClerk did not store"
