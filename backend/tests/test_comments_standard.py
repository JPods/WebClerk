import pytest


@pytest.mark.django_db
def test_a_core_model_carries_the_standard_flat_comments():
    """One comments standard (Bill, 2026-09-25): CoreModel declares comments, so a thin model
    — Pending — has it with nothing of its own. comments.<channel> → [{user, mgs, time,
    user_id}]; the nested general/records scopes and their writer were removed."""
    from apps.core.models.pending import Pending
    from apps.core.services.comment_stamp import append_comment

    p = Pending.objects.create(purpose='comments_standard_test', model_name='test', record_id='1')
    assert p.comments == {}
    append_comment(p, 'public', 'hello', source='test')
    Pending.objects.filter(pk=p.pk).update(comments=p.comments)
    p.refresh_from_db()
    [entry] = p.comments['public']
    assert entry['mgs'] == 'hello' and entry['user'] == 'system' and entry['user_id'] is None
    assert {'general', 'records'}.isdisjoint(p.comments)


def test_the_third_channel_is_partner():
    """Bill, 2026-09-25: the third channel is 'partner' — the key the panel writes and 93
    wc_demo records hold. The schema said 'foreign', so a guarded save dropped it (Fable L5 M-4)."""
    from common.schemas.envelopes import CommentsBase
    assert set(CommentsBase.model_fields) == {'public', 'process', 'partner'}
    ok = CommentsBase(partner=[{'user': 'Vendor Rep', 'mgs': 'ships Tuesday', 'time': 'Sep 26, 2026'}])
    assert ok.partner[0].mgs == 'ships Tuesday'


@pytest.mark.django_db
def test_an_inquiry_followup_lands_on_the_partner_channel():
    from unittest import mock
    from apps.core.models import Action
    from apps.core.views.inquiry_view import InquiryView
    action = Action.objects.create(action={'en': 'Inquiry'})
    view = InquiryView()
    with mock.patch('apps.core.views.inquiry_view._token_id', return_value='t1'):
        view._add_followup(mock.Mock(), action, {'email': 'v@example.com', 'name': 'Vi',
                                                'company': 'Co'}, 'tok', 'second message')
    action.refresh_from_db()
    [entry] = action.comments['partner']
    assert 'second message' in entry['mgs'] and entry['source'] == 'web inquiry: v@example.com'
    assert 'general' not in action.comments
