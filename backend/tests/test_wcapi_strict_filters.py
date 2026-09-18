"""wcapi/get/ rejects unknown filter parameters with a coaching error.

Bill, 2026-09-17: bad input returns an error that coaches the user — a dropped filter
answers a different question than the one asked, and nothing says so.
"""
import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model

User = get_user_model()


class WcapiFilterRejectsUnknownTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='strict@test.com', password='pass123', name_first='S', name_last='Mode', username=''
        )
        self.client.login(email='strict@test.com', password='pass123')

    def test_unknown_query_params_rejected_with_coaching(self):
        """An unknown filter is a 400 that names it and suggests what to use."""
        resp = self.client.get('/wcapi/get/', {'model_name': 'contact', 'unknown_field': 'x'})
        self.assertEqual(resp.status_code, 400)
        body = resp.json()
        self.assertEqual(body.get('error', {}).get('code'), 'unknown_filter')
        self.assertIn('unknown_field', body.get('message', ''))

    def test_misspelled_field_suggests_the_real_one(self):
        """The message coaches instead of only refusing."""
        resp = self.client.get('/wcapi/get/', {'model_name': 'contact', 'emai': 'x@y.com'})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Did you mean 'email'", resp.json().get('message', ''))

    def test_valid_model_name_returns_success(self):
        """A valid model_name returns a success envelope."""
        resp = self.client.get('/wcapi/get/', {'model_name': 'contact'})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body.get('status'), 'success')
