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
