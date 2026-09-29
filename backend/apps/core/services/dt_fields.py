"""Every dt_ field is a system stamp or a plan date (Bill, 2026-09-16; refusal ruled 2026-09-28).

A system dt_ records an event the system performed (created, modified, journaled, processed,
reconciled, last used, ...). Only that event writes it: a payload that tries to change one is
refused with coaching, for every role, admins included. A plan dt_ is a date a person enters
or reports (needed, due, deadline, start/end, effective, received, completed) and stays open to
whoever the role's edit list allows.

The prefix does not decide: dt_received and dt_completed are entered by people. So every dt_
field on every model is named in exactly one of these sets; tests/test_dt_fields.py fails on
any field that is in neither.
"""

SYSTEM_DT_FIELDS = frozenset({
    'dt_created', 'dt_modified',
    'dt_journaled', 'dt_processed', 'dt_reconciliation', 'dt_recorded',
    'dt_approved', 'dt_acknowledged', 'dt_joined', 'dt_event',
    'dt_started', 'dt_finished', 'dt_updated',
    'dt_last_used', 'dt_last_heartbeat', 'dt_last_interaction', 'dt_last_updated',
    'dt_last_recalc', 'dt_last_recalled',
    'dt_period_start', 'dt_period_end',
    'dt_locked',
})

PLAN_DT_FIELDS = frozenset({
    'dt_needed', 'dt_due', 'dt_discount_due', 'dt_deadline', 'dt_expected',
    'dt_start', 'dt_end', 'dt_start_original', 'dt_end_original',
    'dt_begin', 'dt_effective_start', 'dt_effective_end', 'dt_effective_from', 'dt_effective_to',
    'dt_received', 'dt_completed', 'dt_cash', 'dt_transaction', 'dt_next', 'dt_kanban',
    'dt_reviewed',
})


def system_dt_coaching(field: str) -> str:
    return (f'{field} is stamped by the system when its event happens; it is not written from a '
            f'request. Leave it out of the payload. To reverse a journal, use the unjournalize '
            f'command with a reason; to change what a record says, use an amending document.')
