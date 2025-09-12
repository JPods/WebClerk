from __future__ import annotations

from typing import Any, Dict, Optional
from datetime import datetime, timezone
import os
import json
from pathlib import Path

from django.utils.crypto import get_random_string
from django.conf import settings

try:
    from google_auth_oauthlib.flow import Flow
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
except Exception:  # pragma: no cover - optional at import time
    Flow = None  # type: ignore
    Credentials = None  # type: ignore
    build = None  # type: ignore

from apps.sync.models.connection import Connection


SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events',
]


def _ensure_google_libs():
    if Flow is None or Credentials is None or build is None:
        raise RuntimeError('Google API libraries not installed. Please pip install google-auth, google-auth-oauthlib, google-api-python-client.')


def _load_json_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Credentials file not found: {path}")
    with path.open('r') as f:
        return json.load(f)


def _resolve_client_config(conn: Connection) -> Dict[str, Any]:
    """
    Resolve client credentials with precedence:
    1) Environment variables via config.env_prefix (e.g., GCAL_PRIMARY_CLIENT_ID)
    2) Local credentials file via config.credentials_file (relative to BASE_DIR or absolute)
    3) Inline values from conn.config
    Never persists secrets back into the DB.
    """
    base_cfg = (conn.config or {}).copy()
    cfg: Dict[str, Any] = {}

    # 1) Environment prefix (e.g., GCAL_PRIMARY)
    env_prefix = base_cfg.get('env_prefix')
    if env_prefix:
        env_id = os.environ.get(f'{env_prefix}_CLIENT_ID')
        env_secret = os.environ.get(f'{env_prefix}_CLIENT_SECRET')
        env_redirect = os.environ.get(f'{env_prefix}_REDIRECT_URI')
        if env_id:
            cfg['client_id'] = env_id
        if env_secret:
            cfg['client_secret'] = env_secret
        if env_redirect:
            cfg['redirect_uri'] = env_redirect

    # 2) Local JSON credentials file
    cred_file = base_cfg.get('credentials_file')
    if cred_file and not all(k in cfg for k in ('client_id', 'client_secret', 'redirect_uri')):
        p = Path(cred_file)
        if not p.is_absolute():
            p = Path(settings.BASE_DIR) / p
        try:
            j = _load_json_file(p)
            cfg.setdefault('client_id', j.get('client_id'))
            cfg.setdefault('client_secret', j.get('client_secret'))
            cfg.setdefault('redirect_uri', j.get('redirect_uri'))
        except FileNotFoundError:
            # Let missing file surface later if nothing else provided
            pass

    # 3) Inline fallback
    for key in ('client_id', 'client_secret', 'redirect_uri', 'scopes'):
        if key not in cfg and key in base_cfg:
            cfg[key] = base_cfg[key]

    # Defaults
    cfg.setdefault('scopes', SCOPES)

    missing = [k for k in ('client_id', 'client_secret', 'redirect_uri') if not cfg.get(k)]
    if missing:
        raise ValueError(f"Connection {conn.id} missing OAuth config values: {', '.join(missing)}")

    return cfg


def _get_oauth_config(conn: Connection) -> Dict[str, Any]:
    return _resolve_client_config(conn)


def _token_file_path(conn: Connection, cfg: Dict[str, Any]) -> Path:
    # default token file name if using file storage
    token_path = (conn.config or {}).get('token_path') or f".local/google_tokens_{conn.id}.json"
    p = Path(token_path)
    if not p.is_absolute():
        p = Path(settings.BASE_DIR) / p
    return p


def _store_tokens(conn: Connection, cfg: Dict[str, Any], token_data: Dict[str, Any]) -> None:
    storage = (conn.config or {}).get('token_storage', 'db')
    if storage == 'file':
        path = _token_file_path(conn, cfg)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('w') as f:
            json.dump(token_data, f)
        # Do not store tokens in DB when using file storage
        conn.status = 'authorized'
        conn.save(update_fields=['status', 'dt_modified', 'version'])
    else:
        # Store in DB config under tokens
        db_cfg = (conn.config or {}).copy()
        db_cfg['tokens'] = token_data
        conn.config = db_cfg
        conn.status = 'authorized'
        conn.save(update_fields=['config', 'status', 'dt_modified', 'version'])


def _load_tokens(conn: Connection, cfg: Dict[str, Any]) -> Dict[str, Any]:
    storage = (conn.config or {}).get('token_storage', 'db')
    if storage == 'file':
        path = _token_file_path(conn, cfg)
        if not path.exists():
            raise FileNotFoundError(f"Token file not found: {path}; complete OAuth first.")
        with path.open('r') as f:
            return json.load(f)
    return (conn.config or {}).get('tokens') or {}


def get_authorization_url(conn: Connection, state: Optional[str] = None) -> str:
    _ensure_google_libs()
    cfg = _get_oauth_config(conn)
    flow = Flow.from_client_config(
        {
            'web': {
                'client_id': cfg['client_id'],
                'client_secret': cfg['client_secret'],
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token',
                'redirect_uris': [cfg['redirect_uri']],
            }
        },
        scopes=cfg.get('scopes', SCOPES),
    )
    flow.redirect_uri = cfg['redirect_uri']
    use_state = state or get_random_string(24)
    authorization_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        state=use_state,
        prompt='consent',  # ensure refresh_token returned first time
    )
    # Stash transient state if desired
    meta = conn.metadata or {}
    meta.setdefault('oauth', {})['state'] = use_state
    conn.metadata = meta
    conn.save(update_fields=['metadata', 'dt_modified', 'version'])
    return authorization_url


def exchange_code_for_tokens(conn: Connection, code: str) -> Dict[str, Any]:
    _ensure_google_libs()
    cfg = _get_oauth_config(conn)
    flow = Flow.from_client_config(
        {
            'web': {
                'client_id': cfg['client_id'],
                'client_secret': cfg['client_secret'],
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token',
                'redirect_uris': [cfg['redirect_uri']],
            }
        },
        scopes=cfg.get('scopes', SCOPES),
    )
    flow.redirect_uri = cfg['redirect_uri']
    flow.fetch_token(code=code)
    creds = flow.credentials
    token_data = {
        'token': creds.token,
        'refresh_token': getattr(creds, 'refresh_token', None),
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': list(creds.scopes or []),
        'expiry': creds.expiry.isoformat() if getattr(creds, 'expiry', None) else None,
    }
    # Persist tokens based on configured storage strategy
    _store_tokens(conn, cfg, token_data)
    return token_data


def _build_creds_from_connection(conn: Connection):
    _ensure_google_libs()
    cfg = _get_oauth_config(conn)
    tok = _load_tokens(conn, cfg)
    if not tok.get('token'):
        raise ValueError('Connection has no tokens; complete OAuth first.')
    creds = Credentials(
        token=tok.get('token'),
        refresh_token=tok.get('refresh_token'),
        token_uri=tok.get('token_uri'),
        client_id=cfg['client_id'],
        client_secret=cfg['client_secret'],
        scopes=cfg.get('scopes', SCOPES),
    )
    return creds


def list_events(conn: Connection, calendar_id: str = 'primary', max_results: int = 10, time_min: Optional[str] = None) -> Dict[str, Any]:
    creds = _build_creds_from_connection(conn)
    service = build('calendar', 'v3', credentials=creds)
    if not time_min:
        time_min = datetime.now(timezone.utc).isoformat()
    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=time_min,
        maxResults=max_results,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    return {
        'calendar_id': calendar_id,
        'items': events_result.get('items', []),
        'summary': events_result.get('summary')
    }
