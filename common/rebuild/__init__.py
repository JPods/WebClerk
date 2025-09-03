"""Utilities for destructive local rebuild/reset workflows.

Exports :func:`full_reset_and_seed` consolidating earlier ad-hoc reset shell
scripts into a single Python implementation.

Programmatic usage::

    from common.rebuild import full_reset_and_seed
    full_reset_and_seed(create_superusers=3)

CLI via Django shell::

    python manage.py shell -c "from common.rebuild import full_reset_and_seed; full_reset_and_seed()"

DEV ONLY: refuses to run when DEBUG is False unless FORCE_FULL_RESET=1.
"""

from .full_reset import full_reset_and_seed, ResetResult  # re-export

__all__ = ["full_reset_and_seed", "ResetResult"]
