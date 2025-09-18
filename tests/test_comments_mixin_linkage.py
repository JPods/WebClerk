import pytest
from apps.docs.models.linkage import Linkage
from apps.transactions.models import Proposal, ProposalLine
from apps.core.models.setting import Setting

@pytest.mark.django_db
def test_comments_mixin_routes_to_linkage(django_user_model):
    # minimal permission for proposal
    Setting.objects.create(purpose='view_edit', model_name='proposal', is_active=True, data={'USER': {'view':['id'], 'edit':['id']}})
    prop = Proposal.objects.create(name='CMT-PROP')
    pl = ProposalLine.objects.create(parent=prop, parent_ref_id=prop.pk, status='OPEN')
    # simulate linkage attachment
    lk = Linkage.objects.create(purpose='transaction_flow')
    refs = pl.refs if isinstance(pl.refs, dict) else {}
    links = refs.setdefault('links', {'linkage': []})
    links.setdefault('linkage', []).append(lk.id)
    # assign via model __dict__ to bypass strict type hints if descriptor blocks direct set
    setattr(pl, 'refs', refs)
    pl.save(update_fields=['refs'])
    # add comment
    entry = pl.add_comment(channel='public', text='hello world', model='proposal_line', record_id=pl.pk)
    assert entry['text'] == 'hello world'
    lk.refresh_from_db()
    assert lk.comments['records'][f'proposal_line/{pl.pk}']['public'][0]['text'] == 'hello world'
