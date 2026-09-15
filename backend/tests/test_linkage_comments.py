import pytest

@pytest.mark.django_db
def test_linkage_comment_add_and_clip():
    from apps.docs.models.linkage import Linkage

    lk = Linkage.objects.create(purpose='transaction_flow')
    long_text = 'x' * 400
    entry = lk.add_comment(channel='public', text=long_text, by='tester')
    assert len(entry['text']) == 255
    assert lk.comments['general']['public']
    # Record scoped
    entry2 = lk.add_comment(channel='process', text='proc', model='order_line', record_id=123)
    assert 'order_line/123' in lk.comments['records']
    assert lk.comments['records']['order_line/123']['process']
