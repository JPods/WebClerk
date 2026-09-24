"""Document delete goes through the delete door, and the file goes only after the record.

Defect B-1 (2026-09-23): DocumentDeleteView removed the file first, then crashed on
``hasattr(doc)`` — so every delete left a record pointing at a file that no longer existed.
"""
import pytest

from tests.helpers.auth import make_authenticated_client

pytestmark = pytest.mark.django_db(transaction=True)   # on_commit must really fire


def _doc(tmp_path, name='zz-doc-delete.txt'):
    from apps.docs.models import Document
    f = tmp_path / name
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
