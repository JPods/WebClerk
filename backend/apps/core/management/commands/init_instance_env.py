"""init_instance_env — give this instance its identity and agent logins in .env.

Writes only what is missing, never prints a password (common/instance_env.py):

  WC_INSTANCE_UUID     this instance's identity (WC_HQ, bundles, support)
  WCHQ_URL             the WC_HQ support link (https://webclerk.com)
  ALICE_WC_EMAIL       alice@<instance-uuid>.internal — .internal never receives mail
  ALICE_WC_PASSWORD    random; no person needs to know it
  ANDI_WC_EMAIL        andi@<instance-uuid>.internal
  ANDI_WC_PASSWORD     random
  ATHENA_WC_EMAIL      athena@<instance-uuid>.internal — security; mute toward WC_HQ unless
  ATHENA_WC_PASSWORD   there is an attack or an active wchq-conn-upstream Connection
  OLLAMA_BASE_URL      http://localhost:11434 when an LLM answers there; empty otherwise —
                       empty means Alice and Andi are passengers

An instance with its own domain may set real agent addresses instead
(e.g. ALICE_WC_EMAIL=alice@theirfarm.com) — mail then goes to their server.
Then run: manage.py sync_agent_logins

Usage:
    python manage.py init_instance_env
    python manage.py init_instance_env --dry-run
"""
import secrets
import urllib.request
import uuid

from django.core.management.base import BaseCommand

from common.instance_env import read_env, set_env


class Command(BaseCommand):
    help = 'Write missing instance identity and agent logins into .env'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **opts):
        env = read_env()
        instance = env.get('WC_INSTANCE_UUID') or str(uuid.uuid4())
        wanted = {
            'WC_INSTANCE_UUID': instance,
            'WCHQ_URL': 'https://webclerk.com',
            'ALICE_WC_EMAIL': f'alice@{instance}.internal',
            'ALICE_WC_PASSWORD': secrets.token_urlsafe(32),
            'ANDI_WC_EMAIL': f'andi@{instance}.internal',
            'ANDI_WC_PASSWORD': secrets.token_urlsafe(32),
            'ATHENA_WC_EMAIL': f'athena@{instance}.internal',
            'ATHENA_WC_PASSWORD': secrets.token_urlsafe(32),
        }
        missing = {k: v for k, v in wanted.items() if not env.get(k)}
        if 'OLLAMA_BASE_URL' not in env:        # present-but-empty is a choice: passenger
            missing['OLLAMA_BASE_URL'] = self._local_llm()
            wanted['OLLAMA_BASE_URL'] = missing['OLLAMA_BASE_URL']
        for key in wanted:
            state = 'write' if key in missing else 'keep'
            shown = '(hidden)' if key.endswith('PASSWORD') else (missing.get(key, env.get(key)) or '(empty — passenger)')
            self.stdout.write(f'  {state:5} {key} = {shown}')
        if opts['dry_run'] or not missing:
            self.stdout.write('Nothing written.' if not missing else 'Dry run — nothing written.')
            return
        set_env(missing)
        self.stdout.write(self.style.SUCCESS(f'Wrote {len(missing)} key(s) to .env. Restart the server, '
                                             'then run: manage.py sync_agent_logins'))

    @staticmethod
    def _local_llm() -> str:
        url = 'http://localhost:11434'
        try:
            with urllib.request.urlopen(f'{url}/api/tags', timeout=3) as resp:
                return url if resp.status == 200 else ''
        except Exception:
            return ''
