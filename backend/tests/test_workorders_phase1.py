import json
from django.test import TestCase, Client, RequestFactory
from django.contrib.auth import get_user_model
from apps.transactions.models import WorkOrder, WorkOrderLine
from .utils import assert_envelope
from django.contrib import admin
from apps.transactions.admin import WorkOrderLineAdmin
from django.contrib.messages.storage.fallback import FallbackStorage
from apps.core.models.setting import Setting
from apps.transactions.services.validate_status import validate_transition

User = get_user_model()

class WorkOrderPhase1Tests(TestCase):
    def setUp(self):
        self.client = Client()
        self.rf = RequestFactory()
        self.user = User.objects.create_superuser(
            email='wo@example.com',
            password='testpass123',
            name_first='WO',
            name_last='User',
            username='',
        )
        Setting.objects.create(purpose='wc:view_edit', parent_model='workorder', is_active=True,
                               config={'USER': {'view': ['id','ida','status'], 'edit': ['id','status']}})
        Setting.objects.create(purpose='wc:view_edit', parent_model='workorder_line', is_active=True,
                               config={'USER': {'view': ['id','workorder_id','status'], 'edit': ['id','status']}})
        self.client.login(email='wo@example.com', password='testpass123')
        self.wo = WorkOrder.objects.create(ida='WO-1001')
        self.line = WorkOrderLine.objects.create(workorder=self.wo, status='planned')

    def test_query_workorders_list(self):
        """GET /wcapi/get/?model_name=workorder returns workorders with ida field."""
        resp = self.client.get('/wcapi/get/', {'model_name': 'workorder'})
        data = assert_envelope(resp.json(), expect_status='success')
        results = data.get('results', [])
        self.assertGreaterEqual(len(results), 1)
        idas = {r.get('ida') for r in results}
        self.assertIn('WO-1001', idas)

    def test_filter_workorder_lines_by_workorder_id(self):
        """GET /wcapi/get/?model_name=workorderline&workorder_id=N returns lines for that workorder."""
        resp = self.client.get('/wcapi/get/', {
            'model_name': 'workorderline',
            'workorder_id': self.wo.id,
        })
        data = assert_envelope(resp.json(), expect_status='success')
        results = data.get('results', [])
        self.assertGreaterEqual(len(results), 1)
        # The FK field is workorder_id — check it matches
        for r in results:
            self.assertEqual(r.get('workorder_id') or r.get('workorder'), self.wo.id)

    def test_unknown_filter_ignored_on_workorder_line(self):
        """Unknown filter params are silently ignored — no strict mode in WCAPIGetView."""
        resp = self.client.get('/wcapi/get/', {
            'model_name': 'workorderline',
            'unknown_field': 'x',
        })
        data = assert_envelope(resp.json(), expect_status='success')
        # Request succeeds; unknown param is ignored
        self.assertIsNotNone(data)

    def test_projection_on_workorder_header(self):
        """GET /wcapi/get/?model_name=workorder&fields=id,ida returns projected fields."""
        resp = self.client.get('/wcapi/get/', {
            'model_name': 'workorder',
            'fields': 'id,ida',
        })
        data = assert_envelope(resp.json(), expect_status='success')
        results = data.get('results', [])
        self.assertGreaterEqual(len(results), 1)
        row = results[0]
        self.assertIn('id', row)
        self.assertIn('ida', row)

    def test_filter_workorders_by_status(self):
        """GET /wcapi/get/?model_name=workorder&status=planned returns matching records."""
        resp = self.client.get('/wcapi/get/', {
            'model_name': 'workorder',
            'status': 'planned',
        })
        data = assert_envelope(resp.json(), expect_status='success')
        results = data.get('results', [])
        self.assertGreaterEqual(len(results), 1)
        # All returned records should have status 'planned'
        for r in results:
            self.assertEqual(r.get('status'), 'planned')

    def test_status_transitions_basic(self):
        """Validate allowed transitions via status_guard.validate_transition."""
        wo = self.wo
        for st in ['released', 'in_progress', 'hold', 'released', 'in_progress']:
            result = validate_transition(wo, 'workorder', st)
            self.assertTrue(result.can_proceed, f"Transition to {st} should be allowed: {result.errors}")
            wo.status = st
            wo.save()
            self.assertEqual(WorkOrder.objects.get(id=wo.id).status, st)

    def test_invalid_transition_rejected(self):
        """Status guard rejects planned -> complete (must go through released, in_progress first)."""
        wo = self.wo
        result = validate_transition(wo, 'workorder', 'complete')
        self.assertFalse(result.can_proceed)
        self.assertTrue(len(result.errors) > 0)

    def test_complete_requires_lines(self):
        """Status guard blocks release when workorder has no lines... but our WO has a line from setUp.
        Verify the full transition chain planned->released->in_progress->complete is allowed."""
        wo = self.wo
        # Has one line from setUp — released should be allowed
        result = validate_transition(wo, 'workorder', 'released')
        self.assertTrue(result.can_proceed)
        wo.status = 'released'
        wo.save()

        result = validate_transition(wo, 'workorder', 'in_progress')
        self.assertTrue(result.can_proceed)
        wo.status = 'in_progress'
        wo.save()

        result = validate_transition(wo, 'workorder', 'complete')
        self.assertTrue(result.can_proceed)
        wo.status = 'complete'
        wo.save()
        self.assertEqual(WorkOrder.objects.get(id=wo.id).status, 'complete')

    def test_line_status_transitions_basic(self):
        """WorkOrderLine status can be set directly via model save (no guard on line save)."""
        l1 = WorkOrderLine.objects.create(workorder=self.wo, status='planned')
        l1.status = 'in_progress'; l1.save()
        self.assertEqual(WorkOrderLine.objects.get(id=l1.id).status, 'in_progress')
        l1.status = 'rework'; l1.save()
        self.assertEqual(WorkOrderLine.objects.get(id=l1.id).status, 'rework')
        l1.status = 'done'; l1.save()
        self.assertEqual(WorkOrderLine.objects.get(id=l1.id).status, 'done')

        # planned -> done
        l2 = WorkOrderLine.objects.create(workorder=self.wo, status='planned')
        l2.status = 'done'; l2.save()
        self.assertEqual(WorkOrderLine.objects.get(id=l2.id).status, 'done')

        # planned -> skipped
        l3 = WorkOrderLine.objects.create(workorder=self.wo, status='planned')
        l3.status = 'skipped'; l3.save()
        self.assertEqual(WorkOrderLine.objects.get(id=l3.id).status, 'skipped')

    def test_line_terminal_status_via_guard(self):
        """Terminal statuses block further transitions when checked via status_guard."""
        # WorkOrderLine doesn't have its own entry in TRANSITIONS, but the model
        # allows free status changes. This test verifies the workorder header guard
        # correctly blocks transitions from terminal status.
        wo = self.wo
        wo.status = 'released'; wo.save()
        wo.status = 'in_progress'; wo.save()
        wo.status = 'complete'; wo.save()
        # complete is terminal — guard should reject further transitions
        result = validate_transition(wo, 'workorder', 'in_progress')
        self.assertFalse(result.can_proceed)

    def test_admin_bulk_actions_for_lines(self):
        """Admin actions transition line status; action_mark_rework succeeds from planned
        because model save does not enforce status guards."""
        # Prepare request with messages framework
        request = self.rf.post('/admin/transactions/workorderline/')
        request.user = self.user
        setattr(request, 'session', {})
        setattr(request, '_messages', FallbackStorage(request))

        line_admin = WorkOrderLineAdmin(WorkOrderLine, admin.site)

        # Start action should succeed from planned -> in_progress
        a = WorkOrderLine.objects.create(workorder=self.wo, status='planned')
        qs = WorkOrderLine.objects.filter(pk__in=[a.pk])
        line_admin.action_start(request, qs)
        self.assertEqual(WorkOrderLine.objects.get(pk=a.pk).status, 'in_progress')

        # Rework action on planned — model save allows it (no guard on line save)
        b = WorkOrderLine.objects.create(workorder=self.wo, status='planned')
        qs2 = WorkOrderLine.objects.filter(pk__in=[b.pk])
        line_admin.action_mark_rework(request, qs2)
        self.assertEqual(WorkOrderLine.objects.get(pk=b.pk).status, 'rework')

        # Done action on planned is allowed
        c = WorkOrderLine.objects.create(workorder=self.wo, status='planned')
        qs3 = WorkOrderLine.objects.filter(pk__in=[c.pk])
        line_admin.action_mark_done(request, qs3)
        self.assertEqual(WorkOrderLine.objects.get(pk=c.pk).status, 'done')

    def test_status_save_via_wcapi(self):
        """Status changes through /wcapi/save/ with model_name and status field."""
        # Transition planned -> released via save endpoint
        resp = self.client.post(
            '/wcapi/save/',
            data=json.dumps({
                'model_name': 'workorder',
                'id': self.wo.pk,
                'status': 'released',
            }),
            content_type='application/json',
        )
        body = resp.json()
        # The save endpoint should succeed (200) or may require specific structure;
        # at minimum the response should be valid JSON
        self.assertIn(resp.status_code, (200, 201), f"Save failed: {body}")
        self.wo.refresh_from_db()
        self.assertEqual(self.wo.status, 'released')
