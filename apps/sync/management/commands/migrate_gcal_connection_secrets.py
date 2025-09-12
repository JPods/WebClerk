from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, Optional

from django.core.management.base import BaseCommand
from django.conf import settings

from apps.sync.models.connection import Connection


class Command(BaseCommand):
    help = (
        "Migrate Google Calendar Connection secrets off the database into local files/env pointers.\n"
        "- Moves tokens from conn.config['tokens'] to a local file under .local/ by default.\n"
        "- Optionally writes client_id/client_secret/redirect_uri into a local credentials JSON file and/or sets env_prefix.\n"
        "- By default DRY-RUN: use --apply to perform changes."
    )

    def add_arguments(self, parser):
        parser.add_argument('--ids', default='', help='Comma-separated Connection IDs to process (default: all type=google_calendar)')
        parser.add_argument('--apply', action='store_true', help='Apply changes (default: dry-run)')
        parser.add_argument('--env-prefix', default='', help='Set config.env_prefix (e.g., GCAL_PRIMARY); does not write secrets to DB')
        parser.add_argument('--credentials-file', default='', help='Write client credentials to a local JSON file (path can be relative to BASE_DIR)')
        parser.add_argument('--token-path', default='', help='Custom path for token file (default: .local/google_tokens_<id>.json)')
        parser.add_argument('--redact-db-secrets', action='store_true', help='Remove inline client_id/client_secret/redirect_uri and tokens from DB config after migration')

    def _resolve_path(self, path: str) -> Path:
        p = Path(path)
        if not p.is_absolute():
            p = Path(settings.BASE_DIR) / p
        return p

    def _target_connections(self, ids_csv: str) -> Iterable[Connection]:
        qs = Connection.objects.filter(type='google_calendar')
        if ids_csv.strip():
            ids = [int(x) for x in ids_csv.split(',') if x.strip()]
            qs = qs.filter(id__in=ids)
        return qs.order_by('id')

    def handle(self, *args, **opts):
        ids_csv: str = opts['ids']
        apply: bool = opts['apply']
        env_prefix: str = opts['env_prefix'].strip()
        cred_file: str = opts['credentials_file'].strip()
        token_path_opt: str = opts['token_path'].strip()
        redact: bool = opts['redact_db_secrets']

        conns = list(self._target_connections(ids_csv))
        if not conns:
            self.stdout.write('No google_calendar connections found.')
            return

        self.stdout.write(f"Processing {len(conns)} connection(s) {'(APPLY)' if apply else '(DRY-RUN)'}...")

        for conn in conns:
            cfg = (conn.config or {}).copy()
            tokens = cfg.get('tokens') or {}
            client_id = cfg.get('client_id')
            client_secret = cfg.get('client_secret')
            redirect_uri = cfg.get('redirect_uri')

            wrote_token_file = None
            wrote_creds_file = None

            # Decide token file path
            token_path = token_path_opt or cfg.get('token_path') or f".local/google_tokens_{conn.id}.json"
            token_path_resolved = self._resolve_path(token_path)

            # Migrate tokens to file
            if tokens:
                self.stdout.write(f"- Conn {conn.id}: tokens present -> file {token_path_resolved}")
                if apply:
                    token_path_resolved.parent.mkdir(parents=True, exist_ok=True)
                    with token_path_resolved.open('w') as f:
                        json.dump(tokens, f)
                    wrote_token_file = str(token_path_resolved)

            # Write credentials file if requested and we have inline creds
            if cred_file and (client_id or client_secret or redirect_uri):
                cred_path = self._resolve_path(cred_file)
                self.stdout.write(f"- Conn {conn.id}: writing credentials to {cred_path}")
                if apply:
                    cred_path.parent.mkdir(parents=True, exist_ok=True)
                    with cred_path.open('w') as f:
                        json.dump({
                            'client_id': client_id,
                            'client_secret': client_secret,
                            'redirect_uri': redirect_uri,
                        }, f)
                    wrote_creds_file = str(cred_path)

            # Build new config (pointers, not secrets)
            new_cfg = cfg.copy()
            # Set token storage to file if we moved/plan to move tokens
            if tokens:
                new_cfg['token_storage'] = 'file'
                new_cfg['token_path'] = token_path
            if env_prefix:
                new_cfg['env_prefix'] = env_prefix
            if cred_file:
                new_cfg['credentials_file'] = cred_file

            # Redact DB secrets if requested
            if redact:
                for key in ('tokens', 'client_id', 'client_secret', 'redirect_uri'):
                    if key in new_cfg:
                        new_cfg.pop(key, None)

            # Summarize changes
            self.stdout.write(f"  Conn {conn.id}: status={conn.status!r} -> new token_storage={new_cfg.get('token_storage','(unchanged)')}")
            if env_prefix:
                self.stdout.write(f"  Conn {conn.id}: set env_prefix={env_prefix}")
            if cred_file:
                self.stdout.write(f"  Conn {conn.id}: set credentials_file={cred_file}")
            if redact:
                self.stdout.write(f"  Conn {conn.id}: redacted DB secrets and tokens from config")

            # Apply changes
            if apply:
                conn.config = new_cfg
                # If we actually wrote tokens to file, update status
                if wrote_token_file:
                    conn.status = 'authorized'
                conn.save(update_fields=['config', 'status', 'dt_modified', 'version'])

        self.stdout.write(self.style.SUCCESS('Done.'))
