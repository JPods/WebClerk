"""Internal AI agents are wc:ai Settings, one each (Bill, 2026-10-28); Alice's client reads hers."""
import pytest

from apps.core.models import Setting
from tests.conftest import make_setting

pytestmark = pytest.mark.django_db


@pytest.fixture
def alice(settings):
    settings.OLLAMA_BASE_URL = 'http://llm.local:11434'
    Setting.objects.filter(purpose='wc:ai', ida='ai-alice').delete()
    return make_setting(purpose='wc:ai', ida='ai-alice', name='Alice', config={
        'agent': 'alice', 'endpoint': '', 'model': 'gpt-oss:20b', 'timeout': 60,
        'temperature': 0.2, 'system_prompt': 'You are Alice.'})


def test_an_agent_reads_its_record_and_the_instance_llm(alice):
    from apps.ai_assistant.services.ai_agents import agent_config, agents
    config = agent_config('alice')
    assert config['model'] == 'gpt-oss:20b' and config['timeout'] == 60
    assert config['endpoint'] == 'http://llm.local:11434'        # empty: this instance's LLM
    assert config['max_tokens'] is None                            # unset: the model's default
    assert 'alice' in agents()


def test_an_agent_with_no_record_is_refused():
    from apps.ai_assistant.services.ai_agents import agent_config
    with pytest.raises(LookupError, match='ai-nobody'):
        agent_config('nobody')


def test_users_add_an_agent_with_its_own_endpoint(alice):
    from apps.ai_assistant.services.ai_agents import agent_config, agents
    make_setting(purpose='wc:ai', ida='ai-scout', name='scout',
                 config={'agent': 'scout', 'endpoint': 'http://gpu.local:11434/', 'model': 'small'})
    assert agent_config('scout')['endpoint'] == 'http://gpu.local:11434'
    assert set(agents()) >= {'alice', 'scout'}


def test_alices_client_uses_her_record(alice):
    from apps.ai_assistant.services.ollama_client import OllamaClient
    client = OllamaClient()
    assert (client.model, client.timeout, client.base_url) == ('gpt-oss:20b', 60, 'http://llm.local:11434')
    assert client.options == {'temperature': 0.2}
    system = client._build_messages('hello')[0]['content']
    assert system.startswith('You are Alice.')
