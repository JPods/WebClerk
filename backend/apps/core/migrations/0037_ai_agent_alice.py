"""Alice's behaviour is a Setting (Bill, 2026-10-28): one wc:ai record per internal agent,
read by her LLM client. Her model was OLLAMA_MODEL in the environment; the record carries
this instance's value forward, and the environment no longer names it."""

from decouple import config
from django.db import migrations

ALICE = {
    'agent': 'alice',
    'endpoint': '',            # empty: this instance's own LLM (OLLAMA_BASE_URL)
    'model': config('OLLAMA_MODEL', default='gpt-oss:20b'),
    'timeout': int(config('OLLAMA_TIMEOUT', default=120)),
    'temperature': None,
    'max_tokens': None,
    'system_prompt': '',
}


def add_alice(apps, schema_editor):
    Setting = apps.get_model('core', 'Setting')
    if not Setting.objects.filter(purpose='wc:ai', ida='ai-alice').exists():
        Setting.objects.create(
            purpose='wc:ai', ida='ai-alice', name='Alice', scope='system',
            explanation="Alice's LLM: model, endpoint, timeout, sampling and her own prompt. "
                        "Read each time her client is made (ai_assistant/services/ai_agents.py).",
            config=ALICE)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0036_setting_one_wc_model_per_model'),
    ]

    operations = [
        migrations.RunPython(add_alice, migrations.RunPython.noop),
    ]
