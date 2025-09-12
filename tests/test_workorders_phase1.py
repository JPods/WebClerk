import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from apps.transactions.models.line_variants import Workorder, WorkorderLine
from .utils import assert_envelope

User = get_user_model()

class WorkorderPhase1Tests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='wo@example.com',
            password='testpass123',
            name_first='WO',
            name_last='User',
            username=''
        )
        self.client.login(email='wo@example.com', password='testpass123')
        self.wo = Workorder.objects.create(work_no='WO-1001')
        self.line = WorkorderLine.objects.create(parent=self.wo, status='planned')

    def post_json(self, url, payload):
        return self.client.post(url, data=json.dumps(payload), content_type='application/json')

    def test_query_workorders_list(self):
        resp = self.post_json('/wcapi/query/', {'model_name': 'work_order'})
        data = assert_envelope(resp.json(), expect_status='success')
        self.assertEqual(data.get('model_name'), 'work_order')
        nos = {r.get('work_no') for r in data.get('results', [])}
        self.assertIn('WO-1001', nos)

    def test_filter_workorder_lines_by_workorder_id(self):
        # Filter by friendly key workorder_id; mapped to parent_ref_id internally
        resp = self.post_json('/wcapi/query/', {
            'model_name': 'work_order_line',
            'workorder_id': self.wo.id,
            'fields': ['id', 'parent_ref_id', 'status']
        })
        data = assert_envelope(resp.json(), expect_status='success')
        self.assertEqual(data.get('model_name'), 'work_order_line')
        results = data.get('results', [])
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]['parent_ref_id'], self.wo.id)
        self.assertIn(results[0]['status'], {'planned', None, ''})

    def test_strict_mode_rejects_unknown_filter_on_workorder_line(self):
        resp = self.post_json('/wcapi/query/', {
            'model_name': 'work_order_line',
            'unknown_field': 'x',
            'strict': 1
        })
        body = resp.json()
        # Expect fail envelope and 400
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(body.get('status'), 'fail')
        self.assertIn('Invalid filter field', body.get('message', ''))

    def test_projection_on_workorder_header(self):
        resp = self.post_json('/wcapi/query/', {
            'model_name': 'work_order',
            'fields': ['id', 'work_no']
        })
        data = assert_envelope(resp.json(), expect_status='success')
        results = data.get('results', [])
        self.assertGreaterEqual(len(results), 1)
        row = results[0]
        self.assertIn('id', row)
        self.assertIn('work_no', row)

    def test_filter_workorders_by_status(self):
        # Default created Workorder has status 'planned'
        resp = self.post_json('/wcapi/query/', {
            'model_name': 'work_order',
            'status': 'planned',
            'fields': ['id', 'work_no', 'status']
        })
        data = assert_envelope(resp.json(), expect_status='success')
        self.assertEqual(data.get('model_name'), 'work_order')
        results = data.get('results', [])
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].get('status'), 'planned')

    def test_status_transitions_basic(self):
        # planned -> released -> in_progress -> hold -> released -> in_progress is allowed
        wo = self.wo
        for st in ['released', 'in_progress', 'hold', 'released', 'in_progress']:
            wo.status = st
            wo.save()
            self.assertEqual(Workorder.objects.get(id=wo.id).status, st)

    def test_invalid_transition_rejected(self):
        wo = self.wo
        wo.status = 'complete'  # planned -> complete not allowed
        with self.assertRaises(Exception):
            wo.save()

    def test_complete_requires_all_lines_done(self):
        # line is currently 'planned' from setUp
        wo = self.wo
        wo.status = 'released'
        wo.save()
        wo.status = 'in_progress'
        wo.save()
        wo.status = 'complete'
        with self.assertRaises(Exception):
            wo.save()
        # Now mark line done
        self.line.status = 'done'
        self.line.save()
        wo.status = 'complete'
        wo.save()
        self.assertEqual(Workorder.objects.get(id=wo.id).status, 'complete')
