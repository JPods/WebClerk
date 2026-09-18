"""Report hooks — the engine, the registry gate, the superuser gate, and chaining.

Every test here answers one question: can a hook do something nobody declared?
The answer must be no, visibly.
"""
import pytest
from django.core.exceptions import ValidationError

from apps.core.models import Report, Setting
from apps.core.services import report_hooks as rh


POINTS = {
    'invoice.save_pre': {'may_set': ['terms_id'], 'may_block': True},
    'invoice.save_post': {'may_set': ['metadata.review.*'], 'may_create': ['note', 'action'],
                          'may_run': ['RPT-B']},
    'invoice.report_after': {'may_set': ['metadata.review.*'], 'may_run': ['*']},
}


@pytest.fixture
def upstream(db):
    """The WCHQ connection carries the shared Athena secret."""
    from apps.sync.models.connection import Connection
    return Connection.objects.create(
        ida=rh.WCHQ_CONNECTION_IDA, name='WCHQ upstream', purpose='sync', is_active=True,
        config={'wchq_base_url': 'https://wchq.example'},
        encryption={'athena_token': 'shared-secret'},
    )


@pytest.fixture
def registry(db, upstream):
    setting = Setting(name='Hook Points', purpose=rh.HOOK_POINTS_PURPOSE,
                      scope='system', config={'points': POINTS})
    setting._setting_create_authorized = True
    setting.save()
    return setting


def make_report(ida, hooks, cleared=True, **kwargs):
    """A report carrying hooks, cleared as WCHQ would clear it."""
    report = Report(ida=ida, name=ida, category='function', config={'hooks': hooks}, **kwargs)
    report._hooks_authorized = True
    report.save()
    if cleared:
        clear(report)
        report.refresh_from_db()
    return report


def clear(report):
    """Stand in for WCHQ: return the token it would have signed for this payload."""
    return rh.apply_clearance(report, rh.expected_token(rh.hook_hash(report.config['hooks'])))


# ── the superuser gate ───────────────────────────────────────────────────────

def test_hooks_need_authorization(db, registry):
    report = Report(ida='RPT-X', name='X', category='function',
                    config={'hooks': {'point': 'invoice.save_pre',
                                      'before': [{'require': 'terms_id'}]}})
    with pytest.raises(ValidationError):
        report.save()


def test_report_without_hooks_saves_freely(db):
    Report(ida='RPT-PLAIN', name='Plain', category='report', config={'rows': []}).save()
    assert Report.objects.filter(ida='RPT-PLAIN').exists()


def test_authorization_does_not_persist(db, registry):
    report = make_report('RPT-ONCE', {'point': 'invoice.save_pre', 'before': [{'require': 'terms_id'}]})
    report.config['hooks']['before'].append({'require': 'customer_id'})
    report.config = dict(report.config)
    with pytest.raises(ValidationError):
        report.save()


# ── the registry gate ────────────────────────────────────────────────────────

def test_undeclared_point_refused(db, registry):
    problems = rh.validate_hooks({'point': 'contact.save_pre', 'before': [{'require': 'email'}]})
    assert any('not declared' in p for p in problems)


def test_set_outside_may_set_refused(db, registry):
    problems = rh.validate_hooks({'point': 'invoice.save_pre',
                                  'before': [{'set': {'total': 0}}]})
    assert any("set 'total' is not allowed" in p for p in problems)


def test_block_needs_may_block(db, registry):
    problems = rh.validate_hooks({'point': 'invoice.save_post', 'after': [{'block': 'no'}]})
    assert any('may not block' in p for p in problems)


def test_unknown_verb_refused(db, registry):
    problems = rh.validate_hooks({'point': 'invoice.save_pre', 'before': [{'delete_all': True}]})
    assert any('unknown key' in p for p in problems)


def test_wildcard_path_allows_children(db, registry):
    assert rh.validate_hooks({'point': 'invoice.save_post',
                              'after': [{'set': {'metadata.review.flag': True}}]}) == []


# ── Athena clearance ─────────────────────────────────────────────────────────

def test_uncleared_hooks_do_not_run(db, registry, invoice):
    report = make_report('RPT-UNCLEARED',
                         {'point': 'invoice.save_post', 'after': [{'set': {'metadata.review.flag': True}}]},
                         cleared=False)
    result = rh.run_phase(report, 'after', record=invoice)
    assert not result.ran
    assert any('not cleared' in e for e in result.errors)


def test_editing_hooks_drops_clearance(db, registry):
    report = make_report('RPT-EDIT', {'point': 'invoice.save_post',
                                      'after': [{'set': {'metadata.review.flag': True}}]})
    assert rh.is_cleared(report)

    hooks = report.config['hooks']
    hooks['after'] = [{'set': {'metadata.review.flag': False}}]
    report.config = {**report.config, 'hooks': hooks}
    report._hooks_authorized = True
    report.save()

    assert not rh.is_cleared(report)
    assert report.config['hooks']['athena']['cleared'] is False


# ── the verbs ────────────────────────────────────────────────────────────────

def test_set_writes_json_path(db, registry, invoice):
    report = make_report('RPT-SET', {'point': 'invoice.save_post',
                                     'after': [{'set': {'metadata.review.flag': True}}]})
    result = rh.run_phase(report, 'after', record=invoice)
    assert result.ok
    assert invoice.metadata['review']['flag'] is True


def test_when_condition_skips(db, registry, invoice):
    invoice.status = 'draft'
    report = make_report('RPT-WHEN', {'point': 'invoice.save_post',
                                      'after': [{'when': {'status': 'released'},
                                                 'set': {'metadata.review.flag': True}}]})
    rh.run_phase(report, 'after', record=invoice)
    assert not (invoice.metadata or {}).get('review')


def test_require_blocks_when_point_may_block(db, registry, invoice):
    invoice.terms_id = None
    report = make_report('RPT-REQ', {'point': 'invoice.save_pre',
                                     'before': [{'require': 'terms_id',
                                                 'message': 'Released invoices need terms'}]})
    with pytest.raises(rh.HookBlocked) as caught:
        rh.run_phase(report, 'before', record=invoice)
    assert 'need terms' in caught.value.message


def test_failed_validate_without_may_block_is_recorded(db, registry, invoice):
    report = make_report('RPT-REC', {'point': 'invoice.save_post',
                                     'after': [{'require': 'nonexistent_field'}]})
    result = rh.run_phase(report, 'after', record=invoice)
    assert not result.ok and result.errors


def test_token_rendering(db, registry, invoice):
    report = make_report('RPT-TOK', {'point': 'invoice.save_post',
                                     'after': [{'set': {'metadata.review.by': '{{report.ida}}'}}]})
    rh.run_phase(report, 'after', record=invoice)
    assert invoice.metadata['review']['by'] == 'RPT-TOK'


def test_note_needs_may_create(db, registry, invoice):
    """A point without may_create=['note'] refuses the hook at save time, so the
    rule never reaches the engine."""
    with pytest.raises(ValidationError):
        make_report('RPT-NOTE', {'point': 'invoice.report_after',
                                 'after': [{'add_note': 'flagged'}]})


def test_note_written_when_allowed(db, registry, invoice):
    report = make_report('RPT-NOTE-OK', {'point': 'invoice.save_post',
                                         'after': [{'add_note': 'flagged by {{report.ida}}'}]})
    result = rh.run_phase(report, 'after', record=invoice)
    assert result.ok
    assert invoice.comments['notes'][-1]['text'] == 'flagged by RPT-NOTE-OK'


# ── chaining ─────────────────────────────────────────────────────────────────

def test_report_calls_report(db, registry, invoice):
    make_report('RPT-B', {'point': 'invoice.report_after',
                          'after': [{'set': {'metadata.review.second': True}}]})
    caller = make_report('RPT-A', {'point': 'invoice.save_post',
                                   'after': [{'run_report': 'RPT-B'}]})
    result = rh.run_phase(caller, 'after', record=invoice)
    assert 'RPT-B' in result.called
    assert invoice.metadata['review']['second'] is True


def test_undeclared_target_refused_at_save(db, registry, invoice):
    """may_run lists which reports a point may call. An unlisted target is
    refused when the hook is saved."""
    make_report('RPT-C', {'point': 'invoice.report_after', 'after': [{'set': {'metadata.review.x': 1}}]})
    with pytest.raises(ValidationError):
        make_report('RPT-A2', {'point': 'invoice.save_post', 'after': [{'run_report': 'RPT-C'}]})


def test_undeclared_target_refused_at_run(db, registry, invoice):
    """Registry edits do not retroactively bless a stored hook: the engine checks
    may_run again before it calls anything."""
    caller = make_report('RPT-A3', {'point': 'invoice.save_post', 'after': [{'run_report': 'RPT-B'}]})
    registry.config = {'points': {**POINTS, 'invoice.save_post': {
        **POINTS['invoice.save_post'], 'may_run': []}}}
    registry._setting_update_authorized = True
    registry.save()

    result = rh.run_phase(caller, 'after', record=invoice)
    assert any('may not call' in e for e in result.errors)


def test_cycle_refused(db, registry, invoice):
    make_report('RPT-LOOP2', {'point': 'invoice.report_after', 'after': [{'run_report': 'RPT-LOOP1'}]})
    first = make_report('RPT-LOOP1', {'point': 'invoice.report_after', 'after': [{'run_report': 'RPT-LOOP2'}]})
    result = rh.run_phase(first, 'after', record=invoice)
    assert any('cycle refused' in e for e in result.errors)


def test_self_call_refused(db, registry, invoice):
    report = make_report('RPT-SELF', {'point': 'invoice.report_after',
                                      'after': [{'run_report': 'RPT-SELF'}]})
    result = rh.run_phase(report, 'after', record=invoice)
    assert any('cycle refused' in e for e in result.errors)


# ── health ───────────────────────────────────────────────────────────────────

def test_suspended_hook_is_skipped(db, registry, invoice):
    report = make_report('RPT-SUS', {'point': 'invoice.save_post',
                                     'after': [{'set': {'metadata.review.flag': True}}]})
    report.metadata = {**(report.metadata or {}), 'hook_health': {'suspended': True, 'strikes': 3}}
    report._hooks_authorized = True
    report.save()
    assert report not in rh.hooks_for_point('invoice.save_post')


# ── WCHQ token binding ───────────────────────────────────────────────────────

def test_forged_token_refused(db, registry):
    report = make_report('RPT-FORGE', {'point': 'invoice.save_post',
                                       'after': [{'set': {'metadata.review.flag': True}}]},
                         cleared=False)
    answer = rh.apply_clearance(report, 'not-the-real-token')
    assert answer['status'] == 'error'
    assert not rh.is_cleared(report)


def test_token_from_another_payload_refused(db, registry):
    other = rh.expected_token(rh.hook_hash({'point': 'invoice.save_post', 'after': []}))
    report = make_report('RPT-SWAP', {'point': 'invoice.save_post',
                                      'after': [{'set': {'metadata.review.flag': True}}]},
                         cleared=False)
    assert rh.apply_clearance(report, other)['status'] == 'error'
    assert not rh.is_cleared(report)


def test_valid_token_clears(db, registry):
    report = make_report('RPT-OK', {'point': 'invoice.save_post',
                                    'after': [{'set': {'metadata.review.flag': True}}]},
                         cleared=False)
    assert rh.apply_clearance(report, rh.expected_token(rh.hook_hash(report.config['hooks'])))['status'] == 'cleared'
    report.refresh_from_db()
    assert rh.is_cleared(report)


# ── Alice's send/receive protocol with WCHQ ──────────────────────────────────

from apps.ai_assistant.services import hook_review as hr


def test_send_queues_a_bundle(db, registry):
    report = make_report('RPT-SEND', {'point': 'invoice.save_post',
                                      'after': [{'set': {'metadata.review.flag': True}}]},
                         cleared=False)
    answer = hr.send_review_request(report, note='first submission')
    report.refresh_from_db()

    assert answer['ok'] and answer['status'] == hr.STATE_SUBMITTED
    assert hr.review_state(report) == hr.STATE_SUBMITTED

    from apps.core.models.pending import Pending
    pending = Pending.objects.get(uuid=answer['pending_uuid'])
    assert pending.purpose == 'sync.bundle_out'
    assert pending.config['payload']['kind'] == hr.KIND_REQUEST
    assert 'athena' not in pending.config['payload']['hooks']


def test_send_without_connection_is_a_fault(db, registry, upstream):
    upstream.delete()
    report = make_report('RPT-NOCONN', {'point': 'invoice.save_post',
                                        'after': [{'set': {'metadata.review.flag': True}}]},
                         cleared=False)
    answer = hr.send_review_request(report)
    assert answer['error'] == 'no_wchq_connection'
    assert hr.review_state(report) == hr.STATE_DRAFT


def test_manual_transport_writes_a_bundle(db, registry, upstream):
    upstream.config = {**upstream.config, 'transport': 'manual'}
    upstream.save()
    report = make_report('RPT-CARRY', {'point': 'invoice.save_post',
                                       'after': [{'set': {'metadata.review.flag': True}}]},
                         cleared=False)
    answer = hr.send_review_request(report)
    assert answer['ok'] and answer['bundle_id']


def test_ack_then_answer_clears(db, registry):
    report = make_report('RPT-FLOW', {'point': 'invoice.save_post',
                                      'after': [{'set': {'metadata.review.flag': True}}]},
                         cleared=False)
    payload_hash = rh.hook_hash(report.config['hooks'])
    hr.send_review_request(report)

    hr.receive({'kind': hr.KIND_ACK, 'report_ida': 'RPT-FLOW', 'hook_hash': payload_hash})
    report.refresh_from_db()
    assert hr.review_state(report) == hr.STATE_UNDER_REVIEW
    assert report in hr.outstanding_reviews()

    hr.receive({'kind': hr.KIND_ANSWER, 'report_ida': 'RPT-FLOW', 'hook_hash': payload_hash,
                'token': rh.expected_token(payload_hash), 'reviewer': 'wchq-alice'})
    report.refresh_from_db()
    assert hr.review_state(report) == hr.STATE_CLEARED
    assert rh.is_cleared(report)


def test_denial_leaves_hook_dark(db, registry):
    report = make_report('RPT-DENY', {'point': 'invoice.save_post',
                                      'after': [{'set': {'metadata.review.flag': True}}]},
                         cleared=False)
    hr.receive({'kind': hr.KIND_ANSWER, 'report_ida': 'RPT-DENY', 'reason': 'sets a field it should not'})
    report.refresh_from_db()
    assert hr.review_state(report) == hr.STATE_DENIED
    assert not rh.is_cleared(report)


def test_revoke_stops_a_live_hook(db, registry, invoice):
    report = make_report('RPT-REVOKE', {'point': 'invoice.save_post',
                                        'after': [{'set': {'metadata.review.flag': True}}]})
    assert rh.is_cleared(report)

    hr.receive({'kind': hr.KIND_REVOKE, 'report_ida': 'RPT-REVOKE', 'reason': 'bad rule found at WCHQ'})
    report.refresh_from_db()
    assert hr.review_state(report) == hr.STATE_REVOKED
    assert not rh.is_cleared(report)
    result = rh.run_phase(report, 'after', record=invoice)
    assert any('not cleared' in e for e in result.errors)


def test_answer_for_another_payload_ignored(db, registry):
    report = make_report('RPT-STALE', {'point': 'invoice.save_post',
                                       'after': [{'set': {'metadata.review.flag': True}}]},
                         cleared=False)
    answer = hr.receive({'kind': hr.KIND_ANSWER, 'report_ida': 'RPT-STALE',
                         'hook_hash': 'a' * 64, 'token': 'whatever'})
    assert answer['error'] == 'hash_mismatch'
    assert not rh.is_cleared(report)


# ── append_log + dry run ─────────────────────────────────────────────────────

LOG_POINTS = {**POINTS, 'invoice.save_post': {**POINTS['invoice.save_post'],
                                              'may_log': ['record_saves']}}


@pytest.fixture
def log_registry(registry):
    registry.config = {'points': LOG_POINTS}
    registry._setting_update_authorized = True
    registry.save()
    return registry


def test_append_log_writes_a_line(db, log_registry, invoice, tmp_path, settings):
    settings.BASE_DIR = str(tmp_path)
    report = make_report('RPT-LOG', {'point': 'invoice.save_post',
                                     'after': [{'append_log': {'log': 'record_saves',
                                                               'ida': '{{report.ida}}'}}]})
    result = rh.run_phase(report, 'after', record=invoice)
    assert result.ok and result.logged == ['record_saves']

    import json as _json
    lines = (tmp_path / 'logs' / 'hooks' / 'record_saves.jsonl').read_text().strip().splitlines()
    entry = _json.loads(lines[-1])
    assert entry['ida'] == 'RPT-LOG' and entry['dt_utc']


def test_undeclared_log_refused(db, log_registry):
    problems = rh.validate_hooks({'point': 'invoice.save_post',
                                  'after': [{'append_log': {'log': 'somewhere_else'}}]})
    assert any("may not write log" in p for p in problems)


def test_log_name_cannot_be_a_path(db, log_registry):
    problems = rh.validate_hooks({'point': 'invoice.save_post',
                                  'after': [{'append_log': {'log': '../../etc/passwd'}}]})
    assert any('log name of letters' in p for p in problems)


def test_dry_run_writes_nothing(db, log_registry, tmp_path, settings):
    settings.BASE_DIR = str(tmp_path)
    outcome = rh.dry_run({'point': 'invoice.save_post',
                          'after': [{'set': {'metadata.review.flag': True}},
                                    {'append_log': {'log': 'record_saves'}},
                                    {'add_note': 'x'}]}, model_key='invoice')
    assert outcome['ok']
    assert outcome['would_set'] == ['metadata.review.flag']
    assert outcome['would_log'] == ['record_saves']
    assert 'note' in outcome['would_create']
    assert not (tmp_path / 'logs').exists()


def test_dry_run_reports_a_block(db, registry):
    outcome = rh.dry_run({'point': 'invoice.save_pre',
                          'before': [{'require': 'terms_id', 'message': 'needs terms'}]},
                         model_key='invoice', phase='before')
    assert outcome['blocked'] == 'needs terms'


# ── WCHQ side ────────────────────────────────────────────────────────────────

from apps.ai_assistant.services import hook_review_hq as hq


@pytest.fixture
def no_advisers(monkeypatch):
    """Allie and Claude unreachable — their absence must be recorded, not assumed."""
    monkeypatch.setattr(hq, '_consult', lambda who, question: '')
    return True


@pytest.fixture
def quiet_advisers(monkeypatch):
    monkeypatch.setattr(hq, '_consult', lambda who, question: 'CLEAR — does what it says.')
    return True


def test_straightforward_hook_clears_immediately(db, log_registry, quiet_advisers):
    payload = {'kind': hr.KIND_REQUEST, 'instance_uuid': 'inst-1', 'report_ida': 'RPT-HQ1',
               'hook_hash': 'abc123', 'hooks': {'point': 'invoice.save_post',
                                                'after': [{'append_log': {'log': 'record_saves'}}]}}
    answer = hq.review_request(payload)
    assert answer['status'] == 'cleared'
    assert answer['token']
    assert answer['simulation']['runs']['after']['would_log'] == ['record_saves']


def test_blocking_hook_is_held_for_a_person(db, log_registry, quiet_advisers):
    payload = {'kind': hr.KIND_REQUEST, 'instance_uuid': 'inst-1', 'report_ida': 'RPT-HQ2',
               'hook_hash': 'def456',
               'hooks': {'point': 'invoice.save_pre',
                         'before': [{'require': 'terms_id', 'message': 'needs terms'}]}}
    answer = hq.review_request(payload)
    assert answer['status'] == 'held'
    assert any(q['kind'] == 'blocks_saves' for q in answer['questions'])
    assert 'token' not in answer


def test_unreachable_adviser_holds_the_review(db, log_registry, no_advisers):
    payload = {'kind': hr.KIND_REQUEST, 'instance_uuid': 'inst-1', 'report_ida': 'RPT-HQ3',
               'hook_hash': 'ghi789', 'hooks': {'point': 'invoice.save_post',
                                                'after': [{'append_log': {'log': 'record_saves'}}]}}
    answer = hq.review_request(payload)
    assert answer['status'] == 'held'
    assert any(q['kind'] == 'adviser_unreachable' for q in answer['questions'])


def test_sign_off_sends_the_answer(db, log_registry, no_advisers):
    payload = {'kind': hr.KIND_REQUEST, 'instance_uuid': 'inst-1', 'report_ida': 'RPT-HQ4',
               'hook_hash': 'jkl012', 'hooks': {'point': 'invoice.save_post',
                                                'after': [{'append_log': {'log': 'record_saves'}}]}}
    held = hq.review_request(payload)
    assert hq.awaiting_signoff().count() == 1

    answer = hq.sign_off(held['review_id'], approved=True, by='bill')
    assert answer['status'] == 'cleared'
    assert answer['reviewer'] == 'bill'
    # Signed for that instance and that payload — not this one.
    assert answer['token'] == hq.sign_answer('inst-1', 'jkl012', 'RPT-HQ4')['token']
    assert answer['token'] != rh.expected_token('jkl012')
    assert hq.awaiting_signoff().count() == 0


def test_denied_sign_off_sends_a_reason(db, log_registry, no_advisers):
    payload = {'kind': hr.KIND_REQUEST, 'instance_uuid': 'inst-1', 'report_ida': 'RPT-HQ5',
               'hook_hash': 'mno345', 'hooks': {'point': 'invoice.save_post',
                                                'after': [{'append_log': {'log': 'record_saves'}}]}}
    held = hq.review_request(payload)
    answer = hq.sign_off(held['review_id'], approved=False, by='bill', reason='not needed')
    assert answer['status'] == 'denied' and answer['reason'] == 'not needed'
    assert 'token' not in answer


def test_unknown_verb_is_caught_at_hq(db, log_registry, quiet_advisers):
    payload = {'kind': hr.KIND_REQUEST, 'instance_uuid': 'inst-1', 'report_ida': 'RPT-HQ6',
               'hook_hash': 'pqr678',
               'hooks': {'point': 'invoice.save_post', 'after': [{'delete_everything': True}]}}
    answer = hq.review_request(payload)
    assert answer['status'] == 'held'
    assert any(q['kind'] == 'unknown_verb' for q in answer['questions'])


# ── Athena's local clearance ─────────────────────────────────────────────────

from apps.core.services import athena_hooks as ah


class FakeSuper:
    is_superuser = True
    email = 'bill@jpods.com'
    pk = 1


class FakeStaff:
    is_superuser = False
    email = 'staff@example.com'
    pk = 2


def test_athena_offers_a_token(db, log_registry):
    report = make_report('RPT-ATH1', {'point': 'invoice.save_post',
                                      'after': [{'append_log': {'log': 'record_saves'}}]},
                         cleared=False)
    offered = ah.offer(report)
    assert offered['ok'] and offered['token_available']
    assert offered['concerns'] == []
    assert offered['simulation']['after']['would_log'] == ['record_saves']


def test_athena_clearance_runs_the_hook(db, log_registry, invoice, tmp_path, settings):
    settings.BASE_DIR = str(tmp_path)
    report = make_report('RPT-ATH2', {'point': 'invoice.save_post',
                                      'after': [{'set': {'metadata.review.flag': True}}]},
                         cleared=False)
    assert not rh.is_cleared(report)

    assert ah.accept(report, by=FakeSuper())['ok']
    report.refresh_from_db()
    assert rh.is_cleared(report)

    result = rh.run_phase(report, 'after', record=invoice)
    assert result.ok and invoice.metadata['review']['flag'] is True


def test_only_a_superuser_may_clear_locally(db, log_registry):
    report = make_report('RPT-ATH3', {'point': 'invoice.save_post',
                                      'after': [{'set': {'metadata.review.flag': True}}]},
                         cleared=False)
    answer = ah.accept(report, by=FakeStaff())
    assert not answer['ok']
    assert not rh.is_cleared(report)


def test_concerns_are_named_and_recorded(db, registry):
    report = make_report('RPT-ATH4', {'point': 'invoice.save_pre',
                                      'before': [{'require': 'terms_id', 'message': 'needs terms'}]},
                         cleared=False)
    offered = ah.offer(report)
    assert any(c['kind'] == 'blocks_saves' for c in offered['concerns'])

    assert ah.accept(report, by=FakeSuper(), reason='we want this guard')['ok']
    report.refresh_from_db()
    athena = report.config['hooks']['athena']
    assert athena['issuer'] == 'athena'
    assert athena['accepted_by'] == 'bill@jpods.com'
    assert athena['accepted_concerns'][0]['kind'] == 'blocks_saves'


def test_local_token_does_not_pass_as_wchq(db, log_registry):
    report = make_report('RPT-ATH5', {'point': 'invoice.save_post',
                                      'after': [{'append_log': {'log': 'record_saves'}}]},
                         cleared=False)
    local = rh.expected_token(rh.hook_hash(report.config['hooks']), rh.ISSUER_ATHENA)
    assert rh.apply_clearance(report, local, issuer=rh.ISSUER_WCHQ)['status'] == 'error'
    assert not rh.is_cleared(report)


def test_editing_drops_local_clearance_too(db, log_registry):
    report = make_report('RPT-ATH6', {'point': 'invoice.save_post',
                                      'after': [{'append_log': {'log': 'record_saves'}}]},
                         cleared=False)
    ah.accept(report, by=FakeSuper())
    report.refresh_from_db()
    assert rh.is_cleared(report)

    hooks = report.config['hooks']
    hooks['after'] = [{'append_log': {'log': 'record_saves', 'extra': 'x'}}]
    report.config = {**report.config, 'hooks': hooks}
    report._hooks_authorized = True
    report.save()
    assert not rh.is_cleared(report)


def test_withdraw_stops_a_local_hook(db, log_registry, invoice):
    report = make_report('RPT-ATH7', {'point': 'invoice.save_post',
                                      'after': [{'set': {'metadata.review.flag': True}}]},
                         cleared=False)
    ah.accept(report, by=FakeSuper())
    report.refresh_from_db()
    assert ah.withdraw(report, by=FakeSuper(), reason='changed my mind')['ok']
    report.refresh_from_db()
    assert not rh.is_cleared(report)
