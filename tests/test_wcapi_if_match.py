import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from apps.core.models import Contact

User = get_user_model()


class WcapiIfMatchTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='ifm@test.com',
            password='pass123',
            username='ifm@test.com',
            name_first='If',
            name_last='Match'
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
        resp = self.post({'table_name': 'contacts', 'id': self.contact.id, 'name_first': 'Alpha'}, HTTP_IF_MATCH=str(v))
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body['record']['name_first'], 'Alpha')
        self.assertEqual(body['version'], v + 1)

    def test_if_match_conflict_412(self):
        v = self.contact.version
        ok = self.post({'table_name': 'contacts', 'id': self.contact.id, 'name_last': 'One'}, HTTP_IF_MATCH=str(v))
        self.assertEqual(ok.status_code, 200)
        stale = self.post({'table_name': 'contacts', 'id': self.contact.id, 'name_last': 'Two'}, HTTP_IF_MATCH=str(v))
        self.assertEqual(stale.status_code, 412)
        self.assertIn('Version conflict', stale.json()['message'])

    def test_if_match_malformed_header_400(self):
        v = self.contact.version
        bad = self.post({'table_name': 'contacts', 'id': self.contact.id, 'name_first': 'Bad'}, HTTP_IF_MATCH='"abc"')
        self.assertEqual(bad.status_code, 400)
        self.assertIn('Malformed If-Match header', bad.json()['message'])
        # Ensure no change applied
        self.contact.refresh_from_db()
        self.assertEqual(self.contact.name_first, 'Orig')

    def test_if_match_wildcard_skips_check(self):
        v = self.contact.version
        first = self.post({'table_name': 'contacts', 'id': self.contact.id, 'name_first': 'One'}, HTTP_IF_MATCH='*')
        self.assertEqual(first.status_code, 200)
        second = self.post({'table_name': 'contacts', 'id': self.contact.id, 'name_first': 'Two'}, HTTP_IF_MATCH='*')
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()['record']['name_first'], 'Two')

    def test_legacy_expected_version_deprecation_message(self):
        v = self.contact.version
        resp = self.post({'table_name': 'contacts', 'id': self.contact.id, 'expected_version': v, 'name_first': 'Legacy'})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn('messages', body)
        self.assertTrue(any('deprecated' in m for m in body['messages']))
        self.assertEqual(body['record']['name_first'], 'Legacy')
        self.assertEqual(body['version'], v + 1)
