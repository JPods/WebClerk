"""Tests that wcapi/get/ gracefully ignores unknown filter parameters.

The production WCAPIGetView silently ignores unrecognized query parameters
rather than rejecting them. Strict-mode rejection is not implemented.
"""
import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model

User = get_user_model()


class WcapiFilterIgnoresUnknownTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='strict@test.com', password='pass123', name_first='S', name_last='Mode', username=''
        )
        self.client.login(email='strict@test.com', password='pass123')

    def test_unknown_query_params_ignored(self):
        """Unknown query parameters are silently ignored (not rejected)."""
        resp = self.client.get('/wcapi/get/', {'model_name': 'contact', 'unknown_field': 'x'})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body.get('status'), 'success')

    def test_valid_model_name_returns_success(self):
        """A valid model_name returns a success envelope."""
        resp = self.client.get('/wcapi/get/', {'model_name': 'contact'})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body.get('status'), 'success')
