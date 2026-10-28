"""wcapi/get/ rejects unknown filter parameters with a coaching error.

Bill, 2026-09-17: bad input returns an error that coaches the user — a dropped filter
answers a different question than the one asked, and nothing says so.
"""
import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from tests.utils import wcapi_get

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
        resp = wcapi_get(self.client, {'model_name': 'contact', 'unknown_field': 'x'})
        self.assertEqual(resp.status_code, 400)
        body = resp.json()
        self.assertEqual(body.get('error', {}).get('code'), 'unknown_filter')
        self.assertIn('unknown_field', body.get('message', ''))

    def test_misspelled_field_suggests_the_real_one(self):
        """The message coaches instead of only refusing."""
        resp = wcapi_get(self.client, {'model_name': 'contact', 'emai': 'x@y.com'})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Did you mean 'email'", resp.json().get('message', ''))

    def test_a_nested_filters_object_is_named_once_and_coached_to_flat(self):
        """axios serialized {filters: {...}, fields: [...]} as filters[x]=…&fields[]=… — four
        keys reported as '<invalid>' with one hint repeated four times (2026-10-25)."""
        resp = wcapi_get(self.client, {'model_name': 'action',
                                       'filters[metadata__quality_type]': 'sprint',
                                       'filters[status__in][0]': 'open',
                                       'filters[status__in][1]': 'in_progress',
                                       'fields[]': 'project_name'})
        self.assertEqual(resp.status_code, 400)
        message = resp.json().get('message', '')
        self.assertNotIn('<invalid>', message)
        self.assertIn("'filters[…]'", message)
        self.assertIn('?status__in=open,in_progress', message)
        self.assertEqual(message.count('Send filters flat'), 1)

    def test_a_list_read_with_id_is_refused_and_coached_to_the_record_path(self):
        """?id= once dropped the id and answered with the first record (2026-10-27: a line's
        Spec showed another item). One record is its own path; several are id__in."""
        resp = self.client.get('/wcapi/contact/', {'id': self.user.pk})
        self.assertEqual(resp.status_code, 400)
        body = resp.json()
        self.assertEqual(body['error']['code'], 'unknown_filter')
        self.assertIn(f'/wcapi/contact/{self.user.pk}/', body['message'])
        self.assertIn('id__in', body['message'])

        several = self.client.get('/wcapi/contact/', {'id__in': str(self.user.pk)})
        self.assertEqual(several.status_code, 200, several.content)
        self.assertEqual(len(several.json()['data']['results']), 1)

    def test_valid_model_name_returns_success(self):
        """A valid model_name returns a success envelope."""
        resp = wcapi_get(self.client, {'model_name': 'contact'})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body.get('status'), 'success')
