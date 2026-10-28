"""The one Log (Bill, 2026-10-28): one writer, append-only, purposes enforced, audit writes it,
a failed audit write becomes a Pending, Alice's log notes are Log rows."""
import pytest

from apps.core.models import Log, Pending, Setting
from apps.core.services.door import Refused


@pytest.mark.django_db
class TestLogWrite:
    def test_write_keeps_purpose_action_record_and_content(self):
        entry = Log.write('audit', 'updated', model_name='order', record_id=7,
                          changes={'status': {'old': 'a', 'new': 'b'}})
        entry.refresh_from_db()
        assert (entry.purpose, entry.action, entry.model_name, entry.record_id) == ('audit', 'updated', 'order', 7)
        assert entry.config == {'changes': {'status': {'old': 'a', 'new': 'b'}}}
        assert entry.ida == str(entry.pk) and entry.uuid and entry.dt_created > 0

    def test_unknown_purpose_is_refused(self):
        with pytest.raises(ValueError, match='Unknown log purpose'):
            Log.write('whatever', 'x')

    def test_a_foreign_purpose_needs_its_pointer(self, monkeypatch):
        import apps.core.choices as choices
        monkeypatch.setattr(choices, 'LOG_PURPOSES', choices.LOG_PURPOSES | {'foreign_test'})
        with pytest.raises(ValueError, match='refs.foreign'):
            Log.write('foreign_test', 'committed')
        entry = Log.write('foreign_test', 'committed', refs={'foreign': {
            'database': 'other_db', 'model': 'app.Model', 'uuid': 'u-1'}})
        assert entry.refs['foreign']['database'] == 'other_db'

    def test_a_written_entry_is_never_changed(self):
        entry = Log.write('alice', 'system', name='a note')
        entry.action = 'edited'
        with pytest.raises(Refused):
            entry.save()


@pytest.mark.django_db
class TestAuditWritesTheLog:
    def test_an_update_to_an_audited_record_writes_a_log(self):
        from apps.core.models import Contact
        contact = Contact.objects.create(name_first='Log', name_last='Test')
        before = Log.objects.filter(purpose='audit').count()
        contact.name_last = 'Tested'
        contact.save()
        entry = Log.objects.filter(purpose='audit', model_name='contact', record_id=contact.pk).latest('id')
        assert Log.objects.filter(purpose='audit').count() == before + 1
        assert entry.config['changes']['name_last'] == {'old': 'Test', 'new': 'Tested'}

    def test_a_failed_audit_write_keeps_the_save_and_queues_a_pending(self, monkeypatch):
        from apps.core.models import Contact
        contact = Contact.objects.create(name_first='Log', name_last='Fail')

        def refuse(*a, **k):
            raise RuntimeError('log table unavailable')
        monkeypatch.setattr(Log, 'write', classmethod(lambda cls, *a, **k: refuse()))
        contact.name_last = 'Kept'
        contact.save()
        contact.refresh_from_db()
        assert contact.name_last == 'Kept'
        queued = Pending.objects.filter(purpose='log_write', record_id=str(contact.pk)).latest('id')
        assert queued.dt_processed == 0
        assert queued.changes['changes']['name_last']['new'] == 'Kept'

        monkeypatch.undo()
        assert queued.try_apply() is True
        assert Log.objects.filter(purpose='audit', model_name='contact', record_id=contact.pk,
                                  config__changes__name_last__new='Kept').exists()


@pytest.mark.django_db
class TestAliceNotes:
    def test_a_log_note_is_a_log_and_a_to_do_is_an_action(self):
        from apps.core.models import Action
        from apps.ai_assistant.services.notes import create_note, get_report, resolve_pending
        log_note = create_note('log', role='system', name='checked', details={'n': 1})
        todo = create_note('pending', role='action_required', name='look at this', parent_model='item',
                           details={'item_id': 5})
        assert isinstance(log_note, Log) and log_note.purpose == 'alice'
        assert log_note.config == {'name': 'checked', 'details': {'n': 1}}
        assert isinstance(todo, Action) and (todo.purpose, todo.status) == ('alice', 'open')
        assert todo.config['alice'] == {'role': 'action_required', 'model': 'item', 'details': {'item_id': 5}}
        assert not Setting.objects.filter(purpose__in=('alice_log', 'alice_pending')).exists()
        report = get_report(days=1)
        assert {i['category'] for i in report['items']} == {'log', 'pending'}
        assert resolve_pending(todo.pk).status == 'complete'
        assert get_report(category='pending', days=1)['total'] == 0


@pytest.mark.django_db
class TestResponsible:
    """Bill, 2026-10-28: future logs record who is responsible for triggering them."""

    def test_inside_the_door_the_acting_person_is_responsible(self, django_user_model):
        from apps.core.services.door import Actor, acts
        person = django_user_model.objects.create_user(email='responsible@example.com', password='x')

        @acts
        def verb(actor):
            return Log.write('alice', 'system', name='inside')
        entry = verb(Actor(user=person, kind='user', source='wcapi'))
        assert entry.user_id == person.pk
        assert entry.refs['actor'] == {'kind': 'user', 'source': 'wcapi'}

    def test_a_system_actor_is_named_by_kind_and_channel(self):
        from apps.core.services.door import Actor, acts

        @acts
        def task(actor):
            return Log.write('alice', 'system', name='nightly')
        entry = task(Actor.system('task'))
        assert entry.user_id is None
        assert entry.refs['actor'] == {'kind': 'system', 'source': 'task'}

    def test_an_audit_records_the_person_whose_save_it_was(self, django_user_model):
        from apps.core.models import Contact
        from apps.core.services.door import Actor, acts
        person = django_user_model.objects.create_user(email='saver@example.com', password='x')
        contact = Contact.objects.create(name_first='Who', name_last='Saved')

        @acts
        def save(actor):
            contact.name_last = 'Me'
            contact.save()
        save(Actor(user=person, kind='user', source='wcapi'))
        entry = Log.objects.filter(purpose='audit', record_id=contact.pk).latest('id')
        assert entry.user_id == person.pk

    def test_an_action_credits_its_creator_not_a_made_up_contact(self, django_user_model):
        from apps.core.models import Action
        from apps.core.services.door import Actor, acts
        person = django_user_model.objects.create_user(email='creator@example.com', password='x')

        @acts
        def make(actor):
            return Action.objects.create(action={'en': 'by a person'})
        made = make(Actor(user=person, kind='user', source='wcapi'))
        assert made.created_by[-1]['id'] == person.pk
        orphan = Action.objects.create(action={'en': 'by no one'})
        assert orphan.created_by[-1]['id'] is None


def _client():
    import secrets
    from django.contrib.auth import get_user_model
    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import RefreshToken
    user = get_user_model().objects.create_superuser(email='log-channel@example.com',
                                                     password=secrets.token_urlsafe(16))
    token = RefreshToken.for_user(user)
    token['role'] = 'admin'
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    return client, user


@pytest.mark.django_db
class TestLogThroughWcapi:
    """The browser writes a Log with one wcapi `new` (Bill: wcapi create on log)."""

    @pytest.fixture(autouse=True)
    def _log_model_setting(self):
        from django.core.management import call_command
        call_command('seed_model_definitions', model='log', verbosity=0)
        from apps.core.services import access
        access.clear_cache('log')

    def test_new_writes_a_complete_log_row_by_the_signed_in_user(self):
        client, user = _client()
        res = client.post('/wcapi/log/', {'purpose': 'alice', 'action': 'help_feedback',
                                          'config': {'name': 'help_feedback:x', 'details': {'vote': 'up'}}},
                          format='json')
        assert res.status_code in (200, 201), res.content
        entry = Log.objects.get(pk=res.json()['data']['id'])
        assert (entry.purpose, entry.action, entry.user_id) == ('alice', 'help_feedback', user.pk)
        assert entry.config == {'name': 'help_feedback:x', 'details': {'vote': 'up'}}

    def test_an_unknown_purpose_is_refused_with_coaching(self):
        client, _ = _client()
        res = client.post('/wcapi/log/', {'purpose': 'nonsense'}, format='json')
        assert res.status_code == 400 and 'Unknown log purpose' in res.json()['message']

    def test_a_log_row_cannot_be_changed_through_the_channel(self):
        client, _ = _client()
        entry = Log.write('alice', 'system', name='fixed')
        res = client.put(f'/wcapi/log/{entry.pk}/', {'action': 'edited'}, format='json')
        assert res.status_code == 409
        entry.refresh_from_db()
        assert entry.action == 'system'

    def test_list_reads_and_orders_logs(self):
        client, _ = _client()
        Log.write('alice', 'system', name='first')
        Log.write('alice', 'system', name='second')
        res = client.get('/wcapi/log/?purpose=alice&ordering=dt_created&limit=50')
        names = [r['config'].get('name') for r in res.json()['data']['results']]
        assert names.index('first') < names.index('second')


@pytest.mark.django_db
class TestInventoryLog:
    """A document line's change is a Log row, purpose inventory (it was InventoryEvent, with an
    LLM call per event)."""

    def test_a_line_save_writes_an_inventory_log_row(self, order_line_factory):
        before = Log.objects.filter(purpose='inventory').count()
        line = order_line_factory()
        entries = Log.objects.filter(purpose='inventory', action='order_line_add',
                                     config__details__line_id=line.pk)
        assert Log.objects.filter(purpose='inventory').count() > before
        entry = entries.latest('id')
        assert entry.model_name == 'item'
        assert entry.config['name'].startswith('order line add')
        assert entry.config['details']['document']['model'] == 'order'


@pytest.mark.django_db
class TestLesson:
    def test_question_frequency_is_one_lesson_about_no_one(self):
        from apps.core.models import Lesson
        from apps.ai_assistant.services.qa import _update_frequency
        _update_frequency('inventory', 'how do i count stock', 'How do I count stock?')
        _update_frequency('inventory', 'how do i count stock', 'How do I count stock?')
        [lesson] = Lesson.objects.filter(agent='alice', subject_key='qa_frequency')
        assert lesson.contact_id == 0
        assert lesson.config['details']['total_questions'] == 2
        assert lesson.config['details']['top_questions']['how do i count stock']['count'] == 2
        assert lesson.observation_count == 2
