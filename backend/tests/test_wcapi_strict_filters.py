import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from tests.utils import assert_envelope

User = get_user_model()


class WcapiStrictFilterTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='strict@test.com', password='pass123', name_first='S', name_last='Mode', username=''
        )
        self.client.login(email='strict@test.com', password='pass123')

    def post(self, payload, **headers):
        return self.client.post('/wcapi/query/', data=json.dumps(payload), content_type='application/json', **headers)

    def test_default_ignores_unknown(self):
        resp = self.post({'model_name': 'contact', 'unknown_field': 'x'})  #chaned from t_n
        self.assertEqual(resp.status_code, 200)
        assert_envelope(resp.json(), expect_status='success')

    def test_strict_param_rejects_unknown(self):
        resp = self.post({'model_name': 'contact', 'unknown_field': 'x', 'strict': 1})  #chaned from t_n
        self.assertEqual(resp.status_code, 400)
        body = resp.json(); assert_envelope(body, expect_status='fail')
        self.assertIn('Invalid filter field', body.get('message', ''))

    def test_strict_header_rejects_unknown(self):
        resp = self.post({'model_name': 'contact', 'unknown_field': 'x'}, HTTP_WCAPI_STRICT='1')  #chaned from t_n
        self.assertEqual(resp.status_code, 400)
        body = resp.json(); assert_envelope(body, expect_status='fail')
        self.assertIn('Invalid filter field', body.get('message', ''))