"""move_keys_to_connections — bring an existing instance to the keys rule (2026-09-18).

Idempotent; --dry-run shows what would change. Never prints a key.

1. Connection.config.credentials → encryption.credentials (config is returned by the
   API; encryption never leaves the server). Drops config.wchq_base_url and
   config.instance_uuid — WC_HQ url, key and identity are in .env.
2. The WC_HQ Athena token on the wchq-conn-* Connections → WCHQ_API_KEY in .env.
3. SMTP login in .env (EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD,
   EMAIL_USE_TLS) → an active Connection with channel 'smtp'; the lines leave .env.
4. The connection model's access set follows the schema: leaves that no longer exist
   are removed, new config leaves are added to 'all'.
"""
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from common.instance_env import read_env, remove_env, set_env

WCHQ_IDAS = ('wchq-conn-upstream', 'wchq-conn-downstream')
SMTP_ENV = ('EMAIL_HOST', 'EMAIL_PORT', 'EMAIL_HOST_USER', 'EMAIL_HOST_PASSWORD', 'EMAIL_USE_TLS')
WCHQ_ENC = ('athena_token', 'token_source', 'dt_registered', 'installation_id')


class Command(BaseCommand):
    help = 'Move keys out of Connection.config and .env SMTP into Connection.encryption; WC_HQ key into .env'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **opts):
        from apps.sync.models import Connection
        from apps.sync.services.connections import credentials, set_credentials
        dry = opts['dry_run']
        env = read_env()
        env_writes, env_removes = {}, []

        with transaction.atomic():
            # 1 + 2
            for conn in Connection.objects.all().order_by('pk'):
                cfg = dict(conn.config or {})
                enc = dict(conn.encryption or {}) if isinstance(conn.encryption, dict) else {}
                notes = []
                old = cfg.pop('credentials', None)
                if old is not None:
                    filled = {k: v for k, v in (old or {}).items() if str(v or '').strip()}
                    if filled:
                        merged = {**credentials(conn), **filled}
                        conn.encryption = enc
                        set_credentials(conn, merged)
                        enc = conn.encryption
                    notes.append(f'config.credentials → encryption ({len(filled)} filled)')
                for key in ('wchq_base_url', 'instance_uuid'):
                    if key in cfg:
                        cfg.pop(key); notes.append(f'config.{key} removed')
                if conn.ida in WCHQ_IDAS and enc.get('athena_token'):
                    if not env.get('WCHQ_API_KEY') and 'WCHQ_API_KEY' not in env_writes:
                        env_writes['WCHQ_API_KEY'] = enc['athena_token']
                        notes.append('athena token → .env WCHQ_API_KEY')
                    for key in WCHQ_ENC:
                        enc.pop(key, None)
                    notes.append('athena token removed from encryption')
                if notes:
                    self.stdout.write(f'  Connection {conn.pk} {conn.name}: ' + '; '.join(notes))
                    if not dry:
                        conn.config, conn.encryption = cfg, enc
                        conn.save(update_fields=['config', 'encryption'])

            # 3
            if env.get('EMAIL_HOST'):
                exists = Connection.objects.filter(config__channel='smtp').exists()
                if exists:
                    self.stdout.write('  smtp Connection exists — .env SMTP lines removed only')
                else:
                    self.stdout.write(f"  smtp Connection created for {env['EMAIL_HOST']}")
                    if not dry:
                        conn = Connection(name='Outbound mail (SMTP)', type='api', status='active', config={
                            'channel': 'smtp', 'direction': 'push', 'endpoint': env['EMAIL_HOST'],
                            'port': int(env.get('EMAIL_PORT') or 587),
                            'use_tls': (env.get('EMAIL_USE_TLS') or 'True').lower() in ('1', 'true', 'yes')})
                        set_credentials(conn, {'username': env.get('EMAIL_HOST_USER', ''),
                                               'password': env.get('EMAIL_HOST_PASSWORD', '')})
                        conn.save()
                env_removes = [k for k in SMTP_ENV if k in env]

            # 4
            self._conform_access(dry)

            if dry:
                transaction.set_rollback(True)

        if env_writes:
            self.stdout.write(f'  .env: write {", ".join(env_writes)}')
        if env_removes:
            self.stdout.write(f'  .env: remove {", ".join(env_removes)}')
        if not dry:
            set_env(env_writes)
            remove_env(env_removes)
        self.stdout.write('Dry run — nothing changed.' if dry else 'Done. Restart the server.')

    def _conform_access(self, dry):
        from apps.core.models import Setting
        from apps.core.services import field_leaves as fl
        from apps.core.services.access import clear_cache
        s = Setting.objects.filter(purpose='wc:model', parent_model='connection').first()
        acc = ((s.config or {}).get('access') or {}) if s else {}
        if not acc.get('sets'):
            return
        leaves = set(fl.model_leaves('connection')['leaves'])
        cfg = s.config
        for name, members in acc['sets'].items():
            stale = [m for m in members if m not in leaves]
            if stale:
                self.stdout.write(f'  access set {name}: remove {stale}')
            cfg['access']['sets'][name] = [m for m in members if m in leaves]
        new = sorted(l for l in leaves if l.startswith('config.') and l not in acc['sets'].get('all', []))
        if new and 'all' in acc['sets']:
            self.stdout.write(f'  access set all: add {new}')
            cfg['access']['sets']['all'] = sorted(cfg['access']['sets']['all'] + new)
        if not dry:
            s.config = cfg
            s._setting_update_authorized = True
            s.save()
            clear_cache('connection')
