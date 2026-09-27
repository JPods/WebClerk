"""Alice's nightly look for records whose file is gone (Bill: people move folders without changing links)."""
import json

import pytest

pytestmark = pytest.mark.django_db


@pytest.fixture
def roots(settings, tmp_path):
    settings.DATA_DIR = str(tmp_path / 'data')
    settings.WORK_DIR = str(tmp_path / 'work')
    settings.MEDIA_ROOT = str(tmp_path / 'data' / 'media')
    return tmp_path


def test_each_kind_of_stored_path_is_checked_and_only_the_missing_are_named(roots):
    from apps.docs.models import Document
    from apps.products.models import Item
    from apps.sync.models import Bundle, Connection
    from apps.core.services.file_pointers import audit

    (roots / 'data/uploads/document').mkdir(parents=True)
    (roots / 'data/uploads/document/here.pdf').write_bytes(b'x')
    Document.objects.create(name='here', path={'storage': 'local', 'key': 'uploads/document/here.pdf'})
    gone_doc = Document.objects.create(name='gone', path={'storage': 'local', 'key': 'uploads/document/gone.pdf'})

    conn = Connection.objects.create(name='c', type='manual')
    (roots / 'work/bundles/item/incoming/pending').mkdir(parents=True)
    (roots / 'work/bundles/item/incoming/pending/1.json').write_text('{}')
    Bundle.objects.create(connection=conn, direction='push', model_name='item',
                          config={'payload_path': 'bundles/item/incoming/pending/1.json'})
    gone_bundle = Bundle.objects.create(connection=conn, direction='push', model_name='item',
                                        config={'payload_path': 'bundles/item/incoming/pending/2.json'})

    moved = Item.objects.create(name='Renamed', sku='R-1')
    Item.objects.filter(pk=moved.pk).update(metadata={'images': {'source': 'local', 'tn': True}})

    result = audit()
    assert (result['document']['missing'], result['bundle']['missing'], result['item_image']['missing']) == (1, 1, 1)
    assert result['document']['examples'][0]['id'] == gone_doc.pk
    assert result['bundle']['examples'][0]['id'] == gone_bundle.pk
    assert result['item_image']['examples'][0]['sizes'] == ['tn']
    saved = json.loads(open(result['path']).read())
    assert saved['missing'] == 3 and '/work/audits/' in result['path']
    assert Document.objects.filter(pk=gone_doc.pk).exists(), 'reported, never deleted'
