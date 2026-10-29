"""Internal AI agents — one Setting each (Bill, 2026-10-28).

An agent's behaviour is a Setting(purpose='wc:ai', ida='ai-<agent>'): model, endpoint,
timeout, temperature, max_tokens and its own system prompt. Alice's is made by migration;
users add others by adding a record. Outside agents are not here: they are Connections,
which carry the keys and the enumerated, revocable permissions (Settings refuse credentials).

The endpoint is optional: empty means this instance's own LLM (OLLAMA_BASE_URL, a fact about
the hardware; empty there too means the agent is a passenger).
"""
from django.conf import settings

AI_PURPOSE = 'wc:ai'
#: The fields an agent record holds; a record names only what it changes from these.
AGENT_DEFAULTS = {
    'endpoint': '',
    'model': '',
    'timeout': 120,
    'temperature': None,
    'max_tokens': None,
    'system_prompt': '',
}


def agent_ida(agent: str) -> str:
    return f'ai-{agent}'


def agent_config(agent: str) -> dict:
    """The agent's behaviour, read from its record each time it is asked, so an edit takes
    effect at the agent's next client without a restart. No record is a refusal, not a guess."""
    from apps.core.models import Setting
    record = (Setting.objects.filter(purpose=AI_PURPOSE, ida=agent_ida(agent), is_active=True)
              .only('config').first())
    if record is None:
        raise LookupError(f"No AI agent '{agent}': add a Setting with purpose {AI_PURPOSE} and "
                          f"ida {agent_ida(agent)} (Alice's dashboard, LLM tab).")
    config = {**AGENT_DEFAULTS, **(record.config or {})}
    config['endpoint'] = (config['endpoint'] or settings.OLLAMA_BASE_URL or '').rstrip('/')
    return config


def agents() -> list[str]:
    """The internal agents this instance defines."""
    from apps.core.models import Setting
    return sorted(ida[len('ai-'):] for ida in
                  Setting.objects.filter(purpose=AI_PURPOSE, is_active=True,
                                         ida__startswith='ai-').values_list('ida', flat=True))
