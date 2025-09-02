import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from apps.core.models import Contact

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

    def save(self, payload):
        return self.client.post('/wcapi/save/', data=json.dumps(payload), content_type='application/json')

    def test_update_with_matching_version_succeeds_and_bumps(self):
        v = self.contact.version
        resp = self.save({
            'table_name': 'contacts',
            'id': self.contact.id,
            'version': v,
            'name_first': 'Updated'
        })
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body['status'], 'success')
        self.assertEqual(body['data']['version'], v + 1)
        self.assertEqual(body['data']['record']['name_first'], 'Updated')

    def test_update_with_stale_version_conflicts(self):
        v = self.contact.version
        ok = self.save({
            'table_name': 'contacts',
            'id': self.contact.id,
            'version': v,
            'name_last': 'One'
        })
        self.assertEqual(ok.status_code, 200)
        new_v = ok.json()['data']['version']
        self.assertEqual(new_v, v + 1)
        conflict = self.save({
            'table_name': 'contacts',
            'id': self.contact.id,
            'version': v,
            'name_last': 'Two'
        })
        self.assertEqual(conflict.status_code, 412)
        body = conflict.json()
        self.assertEqual(body['status'], 'fail')  # 4xx -> fail
        self.assertIn('Version conflict', body['message'])
