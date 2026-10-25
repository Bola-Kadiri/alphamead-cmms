"""
New roles for the five-stage Work Request flow: CENTRAL OPERATION, AP OFFICER,
HEAD OF FINANCE & TREASURY and CONTRACTOR. HEAD OF FINANCE & TREASURY replaces the
removed FINANCE role; AP OFFICER sees payments but cannot pay out.
"""
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status

from accounts.api.serializers import UserSerializer
from accounts.models import Vendor
from cmms_instanta.permissions import SEE_ALL_INVOICE_ROLES, accessible_facilities
from facility.models import Facility
from work.models import WorkOrder
from work import tests as raise_payment_tests
from work.tests import PAYMENT_REQUISITIONS, WORK_ORDERS, make_user

User = get_user_model()

TEMP_MEDIA = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class FiveStageRoleTests(TestCase):
    # Borrow the Raise Payment fixtures and helpers without re-running that class's tests.
    setUp_raise_payment = raise_payment_tests.RaisePaymentWorkOrderTests.setUp
    payload = raise_payment_tests.RaisePaymentWorkOrderTests.payload
    create = raise_payment_tests.RaisePaymentWorkOrderTests.create
    create_and_first_approve = raise_payment_tests.RaisePaymentWorkOrderTests.create_and_first_approve
    finish_approval = raise_payment_tests.RaisePaymentWorkOrderTests.finish_approval
    approve = raise_payment_tests.RaisePaymentWorkOrderTests.approve

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.setUp_raise_payment()
        self.head = make_user('head.ft@example.com', 'HEAD OF FINANCE & TREASURY')
        self.ap_officer = make_user('ap@example.com', 'AP OFFICER')
        self.central_ops = make_user('central.ops@example.com', 'CENTRAL OPERATION')

    def approved_requisition(self):
        slug = self.create_and_first_approve()
        self.finish_approval(slug)
        return WorkOrder.objects.get(slug=slug).linked_payments.get()

    # ── the roles exist ──────────────────────────────────────────────────────

    def test_new_roles_can_be_assigned(self):
        roles = dict(User.ROLES_TYPE_CHOICES)
        for role in ('CENTRAL OPERATION', 'AP OFFICER', 'HEAD OF FINANCE & TREASURY', 'CONTRACTOR'):
            self.assertIn(role, roles)
        self.assertNotIn('FINANCE', roles)

    # ── paying out ───────────────────────────────────────────────────────────

    def test_head_of_finance_can_disburse(self):
        requisition = self.approved_requisition()
        self.client.force_authenticate(user=self.head)
        response = self.client.post(f'{PAYMENT_REQUISITIONS}{requisition.pk}/disburse/')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        requisition.refresh_from_db()
        self.assertTrue(requisition.is_disbursed)

    def test_ap_officer_cannot_disburse(self):
        requisition = self.approved_requisition()
        self.client.force_authenticate(user=self.ap_officer)
        response = self.client.post(f'{PAYMENT_REQUISITIONS}{requisition.pk}/disburse/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        requisition.refresh_from_db()
        self.assertFalse(requisition.is_disbursed)

    def test_leftover_finance_user_cannot_disburse(self):
        # Anyone still carrying the removed FINANCE value has no payment powers.
        requisition = self.approved_requisition()
        leftover = make_user('old.finance@example.com', 'REQUESTER')
        User.objects.filter(pk=leftover.pk).update(roles='FINANCE')
        leftover.refresh_from_db()
        self.client.force_authenticate(user=leftover)
        response = self.client.post(f'{PAYMENT_REQUISITIONS}{requisition.pk}/disburse/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ── what each role sees ──────────────────────────────────────────────────

    def test_company_wide_roles_see_every_work_order(self):
        self.create()
        for user in (self.head, self.ap_officer, self.central_ops):
            self.client.force_authenticate(user=user)
            response = self.client.get(WORK_ORDERS)
            self.assertEqual(response.status_code, status.HTTP_200_OK, user.roles)
            results = response.data['results'] if isinstance(response.data, dict) else response.data
            self.assertEqual(len(results), 1, user.roles)

    def test_other_requester_still_sees_only_their_own(self):
        self.create()
        other = make_user('other.requester@example.com', 'REQUESTER')
        self.client.force_authenticate(user=other)
        response = self.client.get(WORK_ORDERS)
        results = response.data['results'] if isinstance(response.data, dict) else response.data
        self.assertEqual(len(results), 0)

    def test_company_wide_roles_see_every_facility(self):
        Facility.objects.create(name='Lekki Estate')
        for user in (self.head, self.ap_officer, self.central_ops):
            self.assertEqual(accessible_facilities(user).count(), Facility.objects.count(), user.roles)

    def test_central_operation_does_not_see_all_invoices(self):
        self.assertNotIn('CENTRAL OPERATION', SEE_ALL_INVOICE_ROLES)
        self.assertIn('AP OFFICER', SEE_ALL_INVOICE_ROLES)
        self.assertIn('HEAD OF FINANCE & TREASURY', SEE_ALL_INVOICE_ROLES)

    # ── CONTRACTOR ───────────────────────────────────────────────────────────

    def test_contractor_must_be_linked_to_a_vendor(self):
        user = make_user('cool.air@example.com', 'REQUESTER')
        serializer = UserSerializer(user, data={'roles': 'CONTRACTOR'}, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn('vendor', serializer.errors)

        serializer = UserSerializer(user, data={'roles': 'CONTRACTOR', 'vendor': self.ekedc.pk}, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        user.refresh_from_db()
        self.assertEqual(user.vendor, self.ekedc)

    def test_vendor_link_is_cleared_for_other_roles(self):
        user = make_user('cool.air@example.com', 'CONTRACTOR')
        user.vendor = self.ekedc
        user.save()
        serializer = UserSerializer(user, data={'roles': 'REQUESTER'}, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        user.refresh_from_db()
        self.assertIsNone(user.vendor)

    def test_contractor_sees_no_staff_records_yet(self):
        self.create()
        vendor = Vendor.objects.create(name='Cool Air Ltd', type='Company', currency='NGN')
        contractor = make_user('cool.air@example.com', 'CONTRACTOR')
        contractor.vendor = vendor
        contractor.save()
        self.client.force_authenticate(user=contractor)
        response = self.client.get(WORK_ORDERS)
        results = response.data['results'] if isinstance(response.data, dict) else response.data
        self.assertEqual(len(results), 0)
