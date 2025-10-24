"""Compatibility shim: prefer apps.core.fixtures.seed.seed_all."""
from __future__ import annotations
from typing import Dict, Sequence
from apps.core.fixtures.seed import seed_all as seed_all  # re-export

def reseed_all(
    per_model: int = 5,
    superuser_emails: Sequence[str] | None = None,
    with_connections: bool = True,
    reset: bool = False,
    nuke: bool = False,
) -> Dict[str, object]:
    """
    Backward-compat wrapper. `reset`/`nuke` imply flush+migrate.
    """
    flush = bool(reset or nuke)
    migrate = bool(reset or nuke)
    return seed_all(
        per_model=per_model,
        superuser_emails=superuser_emails,
        with_connections=with_connections,
        flush=flush,
        migrate=migrate,
    )

__all__ = ["seed_all", "reseed_all"]