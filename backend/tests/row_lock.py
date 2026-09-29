"""Hold a real database row lock from a second connection, for contention tests.

The layer soft lock (is_locked/dt_locked) is gone (Bill, 2026-09-28): a layer is guarded by the
row lock the applier and the consume paths take with select_for_update(nowait=True). A test of
contention holds that row lock from another connection, as a concurrent writer would. Rows must
be committed for the other connection to see them, so these tests use
``pytest.mark.django_db(transaction=True)``.
"""
import threading
from contextlib import contextmanager

from django.db import connections, transaction


@contextmanager
def row_locked(model, **lookup):
    """Lock the rows of ``model`` matching ``lookup`` in another connection until the block exits."""
    ready, release, failed = threading.Event(), threading.Event(), []

    def hold():
        try:
            with transaction.atomic():
                list(model.objects.select_for_update().filter(**lookup))
                ready.set()
                release.wait(timeout=30)
        except Exception as exc:  # the test fails on it below, never silently
            failed.append(exc)
            ready.set()
        finally:
            connections.close_all()

    holder = threading.Thread(target=hold, daemon=True)
    holder.start()
    ready.wait(timeout=30)
    if failed:
        raise failed[0]
    try:
        yield
    finally:
        release.set()
        holder.join(timeout=30)
