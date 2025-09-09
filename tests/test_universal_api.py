import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from apps.core.models import Contact
from .utils import assert_envelope

User = get_user_model()

class UniversalAPITestCase(TestCase):
    """Base test case providing convenience helpers for Universal API endpoints."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            name_first='Test',
            name_last='User',
            username=''
        )
        # A second contact (distinct from auth user)
        self.contact = Contact.objects.create(
            email='contact@example.com',
            name_first='Test',
            name_last='Contact',
            company='Test Company'
        )
        self.client.login(email='test@example.com', password='testpass123')

    # Helper methods
    def universal_query(self, model_key, **extra):
        payload = {'model_name': model_key.rstrip('s') if model_key.endswith('s') else model_key}
        payload.update(extra)
        return self.client.post(
            '/wcapi/query/',
            data=json.dumps(payload),
            content_type='application/json'
        )

    def universal_save(self, model_key, record):
        payload = {'model_name': model_key.rstrip('s') if model_key.endswith('s') else model_key}
        payload.update(record)
        return self.client.post(
            '/wcapi/save/',
            data=json.dumps(payload),
            content_type='application/json'
        )

    def universal_get(self, model_key, pk):
        return self.client.post(
            '/wcapi/get/',
            data=json.dumps({'model_name': model_key.rstrip('s') if model_key.endswith('s') else model_key, 'id': pk}),
            content_type='application/json'
        )


class ContactAPITests(UniversalAPITestCase):
    def test_query_contacts(self):
        resp = self.universal_query('contacts')
        data = assert_envelope(resp.json(), expect_status='success')
        self.assertEqual(data['model_name'], 'contact')
        self.assertIn('results', data)
        # ensure at least the two seeded contacts exist
        emails = {r.get('email') for r in data['results']}
        self.assertIn('contact@example.com', emails)

    def test_save_new_contact(self):
        resp = self.universal_save('contacts', {
            'email': 'john.doe@universal.com',
            'name_first': 'John',
            'name_last': 'Doe',
            'company': 'Universal Corp'
        })
        data = assert_envelope(resp.json(), expect_status='success')
        self.assertIn('id', data)
        self.assertIn('version', data)
        # Newer save responses may wrap the created row under 'record'
        record = data.get('record') or data
        self.assertEqual(record.get('email'), 'john.doe@universal.com')


class LocationAPITests(UniversalAPITestCase):
    pass


class PhoneAPITests(UniversalAPITestCase):
    pass


class EmailAPITests(UniversalAPITestCase):
    pass


class UniversalAPISecurityTests(UniversalAPITestCase):
    pass


class UniversalAPIPerformanceTests(UniversalAPITestCase):
    pass


class UniversalAPIRelationshipTests(UniversalAPITestCase):
    pass