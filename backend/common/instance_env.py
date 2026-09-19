"""The instance's .env — what the server needs before it can trust its own database.

Only these live here (Bill, 2026-09-18); every other key is on a Connection record:
  - WebClerk's own database password and SECRET_KEY (needed to start)
  - WC_INSTANCE_UUID and the WC_HQ support link (WCHQ_URL, WCHQ_API_KEY) — support
    must work when the database is damaged
  - the two agent logins every instance has, Alice and Andi (ALICE_WC_*, ANDI_WC_*)
  - OLLAMA_BASE_URL — empty means the agents are passengers (no LLM on this hardware)

Values are written by the installer (init_instance_env, db_init) and never printed.
"""
from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

from django.conf import settings

_LINE = re.compile(r'^\s*([A-Z0-9_]+)\s*=(.*)$')


def env_path() -> Path:
    return Path(settings.BASE_DIR) / '.env'


def read_env() -> dict:
    path = env_path()
    values = {}
    if path.exists():
        for line in path.read_text().splitlines():
            m = _LINE.match(line)
            if m:
                values[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return values


def set_env(updates: dict) -> list[str]:
    """Write keys into .env: replace a key's line, or append it. Returns the keys written.
    The file is rewritten atomically and kept readable by its owner only."""
    if not updates:
        return []
    path = env_path()
    lines = path.read_text().splitlines() if path.exists() else []
    pending = dict(updates)
    out = []
    for line in lines:
        m = _LINE.match(line)
        if m and m.group(1) in pending:
            out.append(f'{m.group(1)}={pending.pop(m.group(1))}')
        else:
            out.append(line)
    if pending:
        out.append('')
        out.append('# written by the installer (common/instance_env.py)')
        out.extend(f'{k}={v}' for k, v in pending.items())
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.env.')
    with os.fdopen(fd, 'w') as fh:
        fh.write('\n'.join(out) + '\n')
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)
    return list(updates)


def remove_env(keys) -> list[str]:
    """Remove keys' lines from .env. Returns the keys that were present."""
    path = env_path()
    if not path.exists():
        return []
    keys = set(keys)
    kept, removed = [], []
    for line in path.read_text().splitlines():
        m = _LINE.match(line)
        if m and m.group(1) in keys:
            removed.append(m.group(1))
        else:
            kept.append(line)
    if removed:
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.env.')
        with os.fdopen(fd, 'w') as fh:
            fh.write('\n'.join(kept) + '\n')
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    return removed
