"""Claude is called by WCHQ, or by an owner's own key — never by the subscription from an
installation (Bill, 2026-11-01). One subscription: $9 per staff user a month."""
from types import SimpleNamespace
from unittest import mock

import pytest

from apps.ai_assistant.services import rag as rag_mod
from apps.ai_assistant.services.rag import RAGService
from apps.core.views.register_installation_view import calculate_monthly_price


def _rag(answer='not sure'):
    store = SimpleNamespace(search=lambda q, n_results=6: [])
    llm = SimpleNamespace(generate=lambda **kw: answer, model='local')
    return RAGService(vector_store=store, llm_client=llm)


def test_nine_dollars_per_staff_user():
    assert [calculate_monthly_price(n) for n in (0, 1, 12)] == [0, 900, 10800]


@pytest.mark.django_db
def test_low_confidence_asks_wchq_when_the_owner_has_no_claude_key():
    with mock.patch.object(rag_mod, 'own_claude', return_value=False), \
         mock.patch.object(rag_mod, 'ask_claude') as claude, \
         mock.patch.object(rag_mod, 'escalate_to_wchq',
                           return_value={'answer': 'hq', 'tier': 'wchq_claude', 'model': 'm'}) as hq:
        result = _rag().ask('What is the discount tier?')
    assert hq.called and not claude.called
    assert result['answer'] == 'hq' and result['tier_used'] == 'wchq_claude'


@pytest.mark.django_db
def test_an_owner_with_their_own_key_calls_claude_direct():
    with mock.patch.object(rag_mod, 'own_claude', return_value=True), \
         mock.patch.object(rag_mod, 'ask_claude', return_value=('direct', {}, 'm')) as claude, \
         mock.patch.object(rag_mod, 'escalate_to_wchq') as hq:
        result = _rag().ask('What is the discount tier?')
    assert claude.called and not hq.called
    assert result['answer'] == 'direct' and result['tier_used'] == 'claude_direct'


def test_there_is_one_upstream_door():
    from django.urls import NoReverseMatch, reverse
    assert reverse('ai_assistant:alice-ask-upstream')
    with pytest.raises(NoReverseMatch):
        reverse('ai_assistant:alice-ask-claude-upstream')
