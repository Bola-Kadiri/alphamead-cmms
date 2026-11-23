"""
Super Admin override: the Super Admin may edit and submit for Procurement & Store (Work Order
pricing) and for the Requester / Procurement & Store (Raise Payment), with a reason that goes in
the history, but may never review or approve. Admin does not get the Work Order override.
"""
from django.test import TestCase, override_settings
from rest_framework import status

from work.models import Notification, WorkOrder
from work.models.action_log import history
from work import test_stage2_work_order as stage2_tests
from work import test_raise_payment_route as route
from work.test_raise_payment_route import LARGE, TEMP_MEDIA

# Borrowed through the modules, so those test classes are not collected (and run) again here.
Stage2 = stage2_tests.Stage2WorkOrderTests
Route = route.RaisePaymentApprovalRouteTests
WORK_ORDERS = stage2_tests.WORK_ORDERS


@override_settings(MEDIA_ROOT=stage2_tests.TEMP_MEDIA)
class WorkOrderPricingOverrideTests(TestCase):
    setUp_stage2 = Stage2.setUp
    api = Stage2.api
    post = Stage2.post
    start = Stage2.start
    price = Stage2.price

    def setUp(self):
        self.setUp_stage2()
        self.boss = stage2_tests.make_user('boss@example.com', 'SUPER ADMIN', 'Boss')
        self.admin_user = stage2_tests.make_user('admin2@example.com', 'ADMIN', 'Ade')

    def flow(self, wo, user):
        return self.api(user).get(f'{WORK_ORDERS}{wo.slug}/flow/').data

    def test_super_admin_can_edit_and_submit_with_a_reason(self):
        wo = self.start()
        data = self.flow(wo, self.boss)
        self.assertTrue(data['acting_as_super_admin'])
        self.assertEqual(data['my_actions'], ['edit_pricing', 'submit'])

        # No reason: refused, nothing saved.
        response = self.price(wo, user=self.boss)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Give a reason', response.data['error'])
        self.assertFalse(WorkOrder.objects.get(pk=wo.pk).quote_lines.exists())

        # With a reason: saved, stamped "edited" on behalf of Procurement & Store, P&S told.
        path = f'{WORK_ORDERS}{wo.slug}/flow-pricing/'
        self.price(wo, user=self.bola)  # the rest of the pricing
        response = self.post(self.boss, path, {'quotation_reference': 'CA-Q-9', 'override_reason': 'Bola on leave'},
                             fmt='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        edit = history(wo).get(action='edited')
        self.assertEqual((edit.actor, edit.on_behalf_of_name), (self.boss, 'Procurement & Store'))
        self.assertIn('Bola on leave', edit.reason)
        self.assertTrue(Notification.objects.filter(recipient=self.bola, title='Super Admin acted on your work').exists())

        response = self.post(self.boss, f'{WORK_ORDERS}{wo.slug}/flow-submit/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.post(self.boss, f'{WORK_ORDERS}{wo.slug}/flow-submit/', {'override_reason': 'Urgent job'})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['status'], 'Awaiting Review')
        raised = history(wo).get(action='raised')
        self.assertEqual((raised.actor, raised.on_behalf_of_name), (self.boss, 'Procurement & Store'))

    def test_super_admin_cannot_review_or_approve(self):
        wo = self.start()
        self.price(wo)
        self.post(self.bola, f'{WORK_ORDERS}{wo.slug}/flow-submit/')
        self.assertEqual(self.flow(wo, self.boss)['my_actions'], [])
        self.assertFalse(self.flow(wo, self.boss)['acting_as_super_admin'])
        response = self.post(self.boss, f'{WORK_ORDERS}{wo.slug}/flow-review/', {'signature': 'Boss Test'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(WorkOrder.objects.get(pk=wo.pk).approval_status, 'Awaiting Review')

    def test_admin_does_not_get_the_override(self):
        wo = self.start()
        self.assertEqual(self.flow(wo, self.admin_user)['my_actions'], [])
        response = self.post(self.admin_user, f'{WORK_ORDERS}{wo.slug}/flow-pricing/',
                             {'quotation_reference': 'X', 'override_reason': 'try'}, fmt='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_procurement_unchanged_and_needs_no_reason(self):
        wo = self.start()
        self.assertFalse(self.flow(wo, self.bola)['acting_as_super_admin'])
        self.assertEqual(self.price(wo).status_code, status.HTTP_200_OK)
        response = self.post(self.bola, f'{WORK_ORDERS}{wo.slug}/flow-submit/')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertFalse(history(wo).filter(action='edited').exists())
        self.assertEqual(history(wo).get(action='raised').on_behalf_of_name, '')


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class RaisePaymentOverrideTests(TestCase):
    AUTO = Route.AUTO
    setUp = Route.setUp
    post_bill = Route.post_bill
    raise_bill = Route.raise_bill
    act = Route.act
    procure = Route.procure
    status_of = Route.status_of

    def act_now(self, *args, **kwargs):
        # Run the notifications that are sent once the change is saved.
        with self.captureOnCommitCallbacks(execute=True):
            return self.act(*args, **kwargs)

    def submit_po(self, slug, user, **extra):
        from django.core.files.uploadedfile import SimpleUploadedFile
        data = {'po_number': 'PO-1', 'quotation_amount': LARGE, 'client_price': '0', 'quotation_reference': 'Q-1',
                'po_document': SimpleUploadedFile('po.pdf', b'%PDF-1.4 po', content_type='application/pdf'), **extra}
        return self.act_now(user, slug, 'procurement-submit', data, 'multipart')

    def test_super_admin_po_step_needs_a_reason_and_is_stamped(self):
        slug = self.raise_bill(cost=LARGE)
        response = self.submit_po(slug, self.admin)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('override_reason', response.data)
        self.assertEqual(self.status_of(slug), 'Awaiting Procurement')

        response = self.submit_po(slug, self.admin, override_reason='P&S offline')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        wo = WorkOrder.objects.get(slug=slug)
        stamp = history(wo).get(action='procured')
        self.assertEqual((stamp.actor, stamp.on_behalf_of_name), (self.admin, 'Procurement & Store'))
        self.assertIn('P&S offline', stamp.reason)
        self.assertTrue(Notification.objects.filter(recipient=self.procurement,
                                                    title='Super Admin acted on your work').exists())

    def test_procurement_po_step_unchanged(self):
        slug = self.raise_bill(cost=LARGE)
        self.procure(slug)
        stamp = history(WorkOrder.objects.get(slug=slug)).get(action='procured')
        self.assertEqual((stamp.actor, stamp.on_behalf_of_name, stamp.reason), (self.procurement, '', ''))

    def test_super_admin_resubmit_needs_a_reason(self):
        slug = self.raise_bill(cost=LARGE)
        self.act(self.procurement, slug, 'procurement-return', {'procurement_reason': 'Wrong amount'})
        response = self.act(self.admin, slug, 'raise-payment-resubmit')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.status_of(slug), 'Procurement Returned')
        response = self.act_now(self.admin, slug, 'raise-payment-resubmit', {'override_reason': 'Requester away'})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        stamp = history(WorkOrder.objects.get(slug=slug)).get(action='resubmitted')
        self.assertEqual(stamp.on_behalf_of_name, 'Requester')
        self.assertTrue(Notification.objects.filter(recipient=self.requester,
                                                    title='Super Admin acted on your work').exists())

    def test_trail_shows_who_the_super_admin_acted_for(self):
        slug = self.raise_bill(cost=LARGE)
        self.submit_po(slug, self.admin, override_reason='P&S offline')
        self.client.force_authenticate(user=self.requester)
        trail = self.client.get(f'/work/api/work-orders/{slug}/').data['approval_trail']
        procured = [e for e in trail['events'] if e['action'] == 'procured'][0]
        self.assertEqual(procured['on_behalf_of']['name'], 'Procurement & Store')


del Stage2, Route
