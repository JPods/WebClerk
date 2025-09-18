import json
from django.test import TestCase, Client, RequestFactory
from django.contrib.auth import get_user_model
from apps.transactions.models import Workorder, WorkorderLine
from .utils import assert_envelope
from django.contrib import admin
from apps.transactions.admin import WorkorderLineAdmin
from django.contrib.messages.storage.fallback import FallbackStorage
from apps.core.models.setting import Setting

User = get_user_model()

class WorkorderPhase1Tests(TestCase):
    def setUp(self):
        self.client = Client()
        self.rf = RequestFactory()
        self.user = User.objects.create_user(
            email='wo@example.com',
            password='testpass123',
            name_first='WO',
            name_last='User',
            username=''
        )
        # Ensure role and permissions for tx endpoints
        self.user.role = 'USER'; self.user.save(update_fields=['role'])
        Setting.objects.create(purpose='view_edit', model_name='work_order', is_active=True,
                               data={'USER': {'view': ['id','work_no','status'], 'edit': ['id','status']}})
        Setting.objects.create(purpose='view_edit', model_name='work_order_line', is_active=True,
                               data={'USER': {'view': ['id','parent_ref_id','status'], 'edit': ['id','status']}})
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

    def test_line_status_transitions_basic(self):
        # planned -> in_progress -> rework -> done
        l1 = WorkorderLine.objects.create(parent=self.wo, status='planned')
        l1.status = 'in_progress'; l1.save()
        self.assertEqual(WorkorderLine.objects.get(id=l1.id).status, 'in_progress')
        l1.status = 'rework'; l1.save()
        self.assertEqual(WorkorderLine.objects.get(id=l1.id).status, 'rework')
        l1.status = 'done'; l1.save()
        self.assertEqual(WorkorderLine.objects.get(id=l1.id).status, 'done')

        # planned -> done
        l2 = WorkorderLine.objects.create(parent=self.wo, status='planned')
        l2.status = 'done'; l2.save()
        self.assertEqual(WorkorderLine.objects.get(id=l2.id).status, 'done')

        # planned -> skipped
        l3 = WorkorderLine.objects.create(parent=self.wo, status='planned')
        l3.status = 'skipped'; l3.save()
        self.assertEqual(WorkorderLine.objects.get(id=l3.id).status, 'skipped')

    def test_line_invalid_transition_rejected(self):
        l = WorkorderLine.objects.create(parent=self.wo, status='planned')
        l.status = 'rework'  # planned -> rework not allowed
        with self.assertRaises(Exception):
            l.save()
        # done is terminal
        l2 = WorkorderLine.objects.create(parent=self.wo, status='planned')
        l2.status = 'done'; l2.save()
        l2.status = 'in_progress'
        with self.assertRaises(Exception):
            l2.save()

    def test_admin_bulk_actions_for_lines(self):
        # Prepare request with messages framework
        request = self.rf.post('/admin/transactions/workorderline/')
        request.user = self.user
        setattr(request, 'session', {})
        setattr(request, '_messages', FallbackStorage(request))

        line_admin = WorkorderLineAdmin(WorkorderLine, admin.site)

        # Start action should succeed from planned -> in_progress
        a = WorkorderLine.objects.create(parent=self.wo, status='planned')
        qs = WorkorderLine.objects.filter(pk__in=[a.pk])
        line_admin.action_start(request, qs)
        self.assertEqual(WorkorderLine.objects.get(pk=a.pk).status, 'in_progress')

        # Rework action on planned should fail and keep status unchanged
        b = WorkorderLine.objects.create(parent=self.wo, status='planned')
        qs2 = WorkorderLine.objects.filter(pk__in=[b.pk])
        line_admin.action_mark_rework(request, qs2)
        self.assertEqual(WorkorderLine.objects.get(pk=b.pk).status, 'planned')

        # Done action on planned is allowed
        c = WorkorderLine.objects.create(parent=self.wo, status='planned')
        qs3 = WorkorderLine.objects.filter(pk__in=[c.pk])
        line_admin.action_mark_done(request, qs3)
        self.assertEqual(WorkorderLine.objects.get(pk=c.pk).status, 'done')

    def test_transition_endpoints_header_and_line(self):
        # Header: planned -> released
        r1 = self.client.post(f'/tx/workorders/{self.wo.pk}/transition/', data=json.dumps({'to': 'released', 'reason': 'kickoff'}), content_type='application/json')
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(Workorder.objects.get(pk=self.wo.pk).status, 'released')

        # Line: planned -> in_progress -> done
        line = WorkorderLine.objects.create(parent=self.wo, status='planned')
        r2 = self.client.post(f'/tx/workorder-lines/{line.pk}/transition/', data=json.dumps({'to': 'in_progress', 'reason': 'start'}), content_type='application/json')
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(WorkorderLine.objects.get(pk=line.pk).status, 'in_progress')
        r3 = self.client.post(f'/tx/workorder-lines/{line.pk}/transition/', data=json.dumps({'to': 'done', 'reason': 'completed'}), content_type='application/json')
        self.assertEqual(r3.status_code, 200)
        ln = WorkorderLine.objects.get(pk=line.pk)
        self.assertEqual(ln.status, 'done')
        # Audit metadata should have action list with at least two entries
        meta = getattr(ln, 'metadata', {}) or {}
        acts = ((meta.get('history') or {}).get('action')) or []
        self.assertTrue(isinstance(acts, list) and len(acts) >= 2)

        # Invalid line transition should 400
        bad = self.client.post(f'/tx/workorder-lines/{line.pk}/transition/', data=json.dumps({'to': 'in_progress'}), content_type='application/json')
        self.assertEqual(bad.status_code, 400)
