import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from apps.core.models import Contact
from tests.utils import assert_envelope

User = get_user_model()


class WcapiConcurrencyTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='cc@test.com',
            password='pass123',
            name_first='CC',
            name_last='User',
            username=''
        )
        self.client.login(email='cc@test.com', password='pass123')
        self.contact = Contact.objects.create(
            email='target@example.com',
            name_first='Target',
            name_last='Contact'
        )

    def save(self, payload, *, headers=None):
        """POST helper for /wcapi/save/ with JSON body."""
        headers = headers or {}
        return self.client.post(
            '/wcapi/save/',
            data=json.dumps(payload),
            content_type='application/json',
            **headers,
        )

    def test_update_with_matching_version_succeeds_and_bumps(self):
        v = self.contact.version
        resp = self.save({
            'model_name': 'contact',  #chaned from t_n
            'id': self.contact.id,
            'version': v,
            'name_first': 'Updated'
        })
        self.assertEqual(resp.status_code, 200)
        data = assert_envelope(resp.json(), expect_status='success')
        self.assertEqual(data['version'], v + 1)
        self.assertEqual(data['record']['name_first'], 'Updated')

    def test_update_with_stale_version_conflicts(self):
        v = self.contact.version
        ok = self.save({
            'model_name': 'contact',  #chaned from t_n
            'id': self.contact.id,
            'version': v,
            'name_last': 'One'
        })
        self.assertEqual(ok.status_code, 200)
        new_v = assert_envelope(ok.json(), expect_status='success')['version']
        self.assertEqual(new_v, v + 1)
        conflict = self.save({
            'model_name': 'contact',  #chaned from t_n
            'id': self.contact.id,
            'version': v,
            'name_last': 'Two'
        })
        self.assertEqual(conflict.status_code, 412)
        assert_envelope(conflict.json(), expect_status='fail')

    def test_if_match_header_precedence(self):
        v = self.contact.version
        first = self.save({
            'model_name': 'contact',  #chaned from t_n
            'id': self.contact.id,
            'version': v,
            'name_first': 'One'
        })
        self.assertEqual(first.status_code, 200)
        bumped = assert_envelope(first.json(), expect_status='success')['version']
        self.assertEqual(bumped, v + 1)
        # Stale body version but correct If-Match header should allow update
        second = self.save({
            'model_name': 'contact',  #chaned from t_n
            'id': self.contact.id,
            'version': v,  # stale body version; header takes precedence
            'name_first': 'Two'
        }, headers={'HTTP_IF_MATCH': str(bumped)})
        self.assertEqual(second.status_code, 200)
        data2 = assert_envelope(second.json(), expect_status='success')
        self.assertEqual(data2['version'], bumped + 1)
        self.assertEqual(data2['record']['name_first'], 'Two')

    def test_if_match_header_conflict(self):
        v = self.contact.version
        first = self.save({
            'model_name': 'contact',  #chaned from t_n
            'id': self.contact.id,
            'version': v,
            'name_last': 'Alpha'
        })
        self.assertEqual(first.status_code, 200)
        bumped = assert_envelope(first.json(), expect_status='success')['version']
        self.assertEqual(bumped, v + 1)
        conflict = self.save({
            'model_name': 'contact',  #chaned from t_n
            'id': self.contact.id,
            'name_last': 'Beta'
        }, headers={'HTTP_IF_MATCH': str(v)})
        self.assertEqual(conflict.status_code, 412)
        assert_envelope(conflict.json(), expect_status='fail')

    def test_if_match_wildcard_skips_check(self):
        v = self.contact.version
        resp = self.save({
            'model_name': 'contact',  #chaned from t_n
            'id': self.contact.id,
            'name_first': 'Wildcard'
        }, headers={'HTTP_IF_MATCH': '*'})
        self.assertEqual(resp.status_code, 200)
        data = assert_envelope(resp.json(), expect_status='success')
        # version should advance (but at least be >= initial)
        self.assertGreaterEqual(data['version'], v + 1)
        self.assertEqual(data['record']['name_first'], 'Wildcard')
