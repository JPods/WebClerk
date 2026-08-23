import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from apps.core.models import Contact
from .utils import assert_envelope

User = get_user_model()


class WcapiIfMatchTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='ifm@test.com',
            password='pass123',
            name_first='If',
            name_last='Match',
            username=''
        )
        self.client.login(email='ifm@test.com', password='pass123')
        self.contact = Contact.objects.create(
            email='ifmatch@example.com',
            name_first='Orig',
            name_last='Contact'
        )

    def post(self, payload, **headers):
        return self.client.post(
            '/wcapi/save/',
            data=json.dumps(payload),
            content_type='application/json',
            **headers
        )

    def test_if_match_success(self):
        v = self.contact.version
        resp = self.post({'model_name': 'contact', 'id': self.contact.id, 'name_first': 'Alpha'}, HTTP_IF_MATCH=str(v))  #chaned from t_n
        self.assertEqual(resp.status_code, 200)
        data = assert_envelope(resp.json(), expect_status='success')
        record = data.get('record') or data
        self.assertEqual(record.get('name_first'), 'Alpha')
        self.assertEqual(data.get('version'), v + 1)

    def test_if_match_conflict_412(self):
        v = self.contact.version
        ok = self.post({'model_name': 'contact', 'id': self.contact.id, 'name_last': 'One'}, HTTP_IF_MATCH=str(v))  #chaned from t_n
        self.assertEqual(ok.status_code, 200)
        assert_envelope(ok.json(), expect_status='success')
        stale = self.post({'model_name': 'contact', 'id': self.contact.id, 'name_last': 'Two'}, HTTP_IF_MATCH=str(v))  #chaned from t_n
        self.assertEqual(stale.status_code, 412)
        body = stale.json()
        assert_envelope(body)  # structural check (status likely 'error')
        self.assertIn('Version conflict', body['message'])

    def test_if_match_malformed_header_400(self):
        v = self.contact.version
        bad = self.post({'model_name': 'contact', 'id': self.contact.id, 'name_first': 'Bad'}, HTTP_IF_MATCH='"abc"')  #chaned from t_n
        self.assertEqual(bad.status_code, 400)
        body = bad.json()
        assert_envelope(body)
        self.assertIn('Malformed If-Match header', body['message'])
        self.contact.refresh_from_db()
        self.assertEqual(self.contact.name_first, 'Orig')

    def test_if_match_wildcard_skips_check(self):
        v = self.contact.version
        first = self.post({'model_name': 'contact', 'id': self.contact.id, 'name_first': 'One'}, HTTP_IF_MATCH='*')  #chaned from t_n
        self.assertEqual(first.status_code, 200)
        assert_envelope(first.json(), expect_status='success')
        second = self.post({'model_name': 'contact', 'id': self.contact.id, 'name_first': 'Two'}, HTTP_IF_MATCH='*')  #chaned from t_n
        self.assertEqual(second.status_code, 200)
        data2 = assert_envelope(second.json(), expect_status='success')
        record2 = data2.get('record') or data2
        self.assertEqual(record2.get('name_first'), 'Two')

    def test_if_match_wildcard_bypasses_stale(self):
        v = self.contact.version
        ok = self.post({'model_name': 'contact', 'id': self.contact.id, 'name_last': 'Stage1'}, HTTP_IF_MATCH=str(v))  #chaned from t_n
        self.assertEqual(ok.status_code, 200)
        assert_envelope(ok.json(), expect_status='success')
        conflict = self.post({'model_name': 'contact', 'id': self.contact.id, 'name_last': 'Stage2'}, HTTP_IF_MATCH=str(v))  #chaned from t_n
        self.assertEqual(conflict.status_code, 412)
        wildcard = self.post({'model_name': 'contact', 'id': self.contact.id, 'name_last': 'Stage3'}, HTTP_IF_MATCH='*')  #chaned from t_n
        self.assertEqual(wildcard.status_code, 200)
        data_wild = assert_envelope(wildcard.json(), expect_status='success')
        record_wild = data_wild.get('record') or data_wild
        self.assertEqual(record_wild.get('name_last'), 'Stage3')

    def test_legacy_expected_version_deprecation_message(self):
        v = self.contact.version
        resp = self.post({'model_name': 'contact', 'id': self.contact.id, 'expected_version': v, 'name_first': 'Legacy'})  #chaned from t_n
        self.assertEqual(resp.status_code, 200)
        data = assert_envelope(resp.json(), expect_status='success')
        self.assertIn('messages', data)
        self.assertTrue(any('deprecated' in m for m in data.get('messages', [])))
        record = data.get('record') or data
        self.assertEqual(record.get('name_first'), 'Legacy')
        self.assertEqual(data.get('version'), v + 1)
