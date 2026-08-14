import pytest

@pytest.mark.django_db
def test_comments_mixin_routes_to_linkage(django_user_model):
    from apps.docs.models.linkage_entry import LinkageEntry
    from apps.transactions.models import Proposal, ProposalLine
    from apps.core.models.setting import Setting

    # minimal permission for proposal
    Setting.objects.create(purpose='wc:view_edit', parent_model='proposal', data={'USER': {'view':['id'], 'edit':['id']}})
    prop = Proposal.objects.create(name='CMT-PROP')
    pl = ProposalLine.objects.create(proposal=prop, status='OPEN')
    # simulate linkage attachment
    lk = LinkageEntry.objects.create(
        group_id=LinkageEntry.next_group_id(),
        model_name='proposal_line',
        record_id=pl.pk,
        purpose='transaction_flow',
    )
    # Wire linkage id into refs so _get_linkage_id() returns lk.id
    pl.refresh_from_db()
    refs = pl.refs if isinstance(pl.refs, dict) else {}
    links = refs.setdefault('links', {})
    links['linkage'] = [lk.id]
    pl.refs = refs
    pl.save(update_fields=['refs'])
    # Verify linkage routing resolves
    assert pl._get_linkage_id() == lk.id
    # add comment — should route through linkage entry
    entry = pl.add_comment(channel='public', text='hello world', model='proposal_line', record_id=pl.pk)
    assert entry['text'] == 'hello world'
    lk.refresh_from_db()
    assert lk.comments['records'][f'proposal_line/{pl.pk}']['public'][0]['text'] == 'hello world'
