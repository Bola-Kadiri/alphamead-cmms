import shutil
import tempfile
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Vendor
from asset_inventory.models import AssetCategory, AssetSubCategory
from facility.models import Facility
from work.models import PaymentRequisition, WorkOrder

User = get_user_model()

TEMP_MEDIA = tempfile.mkdtemp()
WORK_ORDERS = '/work/api/work-orders/'
PAYMENT_REQUISITIONS = '/work/api/payment-requisitions/'


def make_user(email, roles):
    user = User.objects.create_user(email=email, password='testpass123', first_name='Test', last_name='User')
    user.roles = roles
    user.is_active = True
    user.save()
    return user


def bill_file(name='ekedc-bill.pdf'):
    return SimpleUploadedFile(name, b'%PDF-1.4 bill', content_type='application/pdf')


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class RaisePaymentWorkOrderTests(TestCase):
    """Raise Payment (known-cost bills): work order → review → approve → paid, with no WR, PO or WCC."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.client = APIClient()
        self.requester = make_user('requester@example.com', 'REQUESTER')
        self.reviewer = make_user('reviewer@example.com', 'REVIEWER')
        self.approver = make_user('approver@example.com', 'APPROVER')
        self.finance = make_user('finance@example.com', 'FINANCE')
        # Second approver for bills of ₦1,000,000 or more (RaisePaymentApprovalSettings default).
        self.second_approver = make_user('wole.olufore@alphamead.com', 'APPROVER')

        self.facility = Facility.objects.create(name='HQ Office')
        self.electricity = AssetCategory.objects.create(
            type='Expense', code='UTIL-ELEC', name='Utilities – Electricity', is_known_cost=True,
        )
        self.generators = AssetCategory.objects.create(type='Asset', code='GEN', name='Generators')
        self.ekedc_bill = AssetSubCategory.objects.create(
            code='EKEDC', name='EKEDC', type='Expense', asset_category=self.electricity,
        )
        self.generator_sub = AssetSubCategory.objects.create(
            code='GEN-SET', name='Generator', type='Asset', asset_category=self.generators,
        )
        self.ekedc = Vendor.objects.create(
            name='EKEDC', type='Company', phone='0800000000', account_name='EKEDC',
            bank='Test Bank', account_number='0011223344', currency='NGN', owner=self.requester,
        )

    # ── helpers ──────────────────────────────────────────────────────────────

    def payload(self, **overrides):
        data = {
            'type': WorkOrder.RAISE_PAYMENT,
            'invoice_no': 'EKEDC-0925-4471',
            'description': 'EKEDC bill, HQ Office, September 2026',
            'category': self.electricity.pk,
            'subcategory': self.ekedc_bill.pk,
            'facility': self.facility.pk,
            'payee': self.ekedc.pk,
            'cost': '1182365.62',
            'currency': 'NGN',
            'expected_payment_date': '2026-10-20',
            'withholding_tax': '5%',
            'reviewers': [self.reviewer.pk],
            'approver': self.approver.pk,
            'final_approver': self.second_approver.pk,  # ₦1,182,365.62 ≥ ₦1,000,000
            'resources': [bill_file()],
        }
        data.update(overrides)
        return {k: v for k, v in data.items() if v is not None}

    def create(self, **overrides):
        self.client.force_authenticate(user=self.requester)
        return self.client.post(WORK_ORDERS, self.payload(**overrides), format='multipart')

    def create_and_first_approve(self):
        """Raise the bill and give the Approver's (first) approval."""
        response = self.create()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        slug = response.data['slug']
        response = self.approve(slug)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return slug

    def finish_approval(self, slug):
        """Reviewer reviews; a bill of ₦1,000,000 or more then needs the second approver."""
        self.client.force_authenticate(user=self.reviewer)
        response = self.client.post(f'{WORK_ORDERS}{slug}/approve-by-reviewer/')
        if response.status_code == status.HTTP_200_OK and response.data['approval_status'] == 'Awaiting Final Approval':
            self.client.force_authenticate(user=self.second_approver)
            response = self.client.post(f'{WORK_ORDERS}{slug}/final-approve/')
        return response

    def approve(self, slug):
        self.client.force_authenticate(user=self.approver)
        return self.client.post(f'{WORK_ORDERS}{slug}/approve-by-approver/')

    # ── creation rules ───────────────────────────────────────────────────────

    def test_create_with_bill_succeeds(self):
        response = self.create()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        work_order = WorkOrder.objects.get(slug=response.data['slug'])
        self.assertTrue(work_order.uses_raise_payment_flow)
        self.assertEqual(work_order.payee, self.ekedc)
        self.assertEqual(work_order.resources.count(), 1)
        self.assertEqual(work_order.linked_payments.count(), 0)

    def test_bill_attachment_is_mandatory(self):
        response = self.create(resources=None)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('resources', response.data)

    def test_category_must_be_on_known_cost_list(self):
        response = self.create(category=self.generators.pk)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('category', response.data)

    def test_payee_facility_and_amount_are_required(self):
        response = self.create(payee=None, facility=None, cost=None)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        for field in ('payee', 'facility', 'cost'):
            self.assertIn(field, response.data)

    def test_payee_without_bank_details_is_refused(self):
        lawma = Vendor.objects.create(name='LAWMA', type='Company', currency='NGN')
        response = self.create(payee=lawma.pk)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('no bank details', str(response.data['payee']))

    def test_disbursement_refused_if_bank_details_removed(self):
        slug = self.create_and_first_approve()
        self.finish_approval(slug)
        requisition = WorkOrder.objects.get(slug=slug).linked_payments.get()
        Vendor.objects.filter(pk=self.ekedc.pk).update(account_number=None)

        self.client.force_authenticate(user=self.finance)
        response = self.client.post(f'{PAYMENT_REQUISITIONS}{requisition.pk}/disburse/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        requisition.refresh_from_db()
        self.assertFalse(requisition.is_disbursed)

    # ── approval → payment → closure ─────────────────────────────────────────

    def test_full_approval_creates_approved_payment_requisition(self):
        slug = self.create_and_first_approve()
        response = self.finish_approval(slug)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        work_order = WorkOrder.objects.get(slug=slug)
        self.assertEqual(work_order.approval_status, 'Approved')
        self.assertEqual(work_order.final_approver, self.second_approver)  # ₦1,182,365.62 ≥ ₦1,000,000
        requisition = work_order.linked_payments.get()
        self.assertEqual(requisition.approval_status, 'approve')
        self.assertEqual(requisition.pay_to, self.ekedc)
        self.assertEqual(requisition.expected_payment_amount, Decimal('1182365.62'))
        self.assertEqual(str(requisition.expected_payment_date), '2026-10-20')
        self.assertEqual(requisition.withholding_tax, '5%')
        self.assertEqual(requisition.attachment.count(), 1)

    def test_approval_limit_blocks_and_creates_nothing(self):
        self.approver.approval_limit = Decimal('1000.00')
        self.approver.save()
        slug = self.create().data['slug']
        response = self.approve(slug)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        work_order = WorkOrder.objects.get(slug=slug)
        self.assertNotEqual(work_order.approval_status, 'Approved')
        self.assertEqual(PaymentRequisition.objects.count(), 0)

    def test_disbursement_closes_work_order_and_requisition(self):
        slug = self.create_and_first_approve()
        self.finish_approval(slug)
        requisition = WorkOrder.objects.get(slug=slug).linked_payments.get()

        self.client.force_authenticate(user=self.finance)
        response = self.client.post(f'{PAYMENT_REQUISITIONS}{requisition.pk}/disburse/')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        requisition.refresh_from_db()
        work_order = WorkOrder.objects.get(slug=slug)
        self.assertTrue(requisition.is_disbursed)
        self.assertTrue(requisition.is_closed)
        self.assertEqual(work_order.work_status, 'closed')

    def test_no_wcc_for_known_cost(self):
        slug = self.create_and_first_approve()
        self.finish_approval(slug)
        work_order = WorkOrder.objects.get(slug=slug)

        self.client.force_authenticate(user=self.requester)
        response = self.client.post(
            '/work/api/work-order-completions/', {'work_order': work_order.pk}, format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('work_order', response.data)

    def test_approved_known_cost_is_locked(self):
        slug = self.create_and_first_approve()
        self.finish_approval(slug)
        self.client.force_authenticate(user=self.requester)
        response = self.client.patch(f'{WORK_ORDERS}{slug}/', {'cost': '1.00'}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ── other work orders unchanged ──────────────────────────────────────────

    def test_normal_work_order_approval_unchanged(self):
        self.client.force_authenticate(user=self.requester)
        response = self.client.post(WORK_ORDERS, {
            'type': 'Unplanned', 'description': 'Broken AC', 'facility': self.facility.pk,
            'reviewers': [self.reviewer.pk], 'approver': self.approver.pk,
        }, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        slug = response.data['slug']

        self.client.force_authenticate(user=self.reviewer)
        self.client.post(f'{WORK_ORDERS}{slug}/approve-by-reviewer/')
        response = self.approve(slug)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(WorkOrder.objects.get(slug=slug).approval_status, 'Approved')
        self.assertEqual(PaymentRequisition.objects.count(), 0)

    # ── duplicate-payment guard ──────────────────────────────────────────────

    def test_bill_number_is_required(self):
        response = self.create(invoice_no='')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('invoice_no', response.data)

    def test_same_bill_cannot_be_raised_twice(self):
        self.assertEqual(self.create().status_code, status.HTTP_201_CREATED)
        response = self.create(resources=[bill_file('again.pdf')])
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('invoice_no', response.data)

    def test_rejected_bill_can_be_raised_again(self):
        first = self.create()
        WorkOrder.objects.filter(slug=first.data['slug']).update(approval_status='Approver Rejected')
        response = self.create(resources=[bill_file('again.pdf')])
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    # ── Raise Payment work orders from before this flow keep old behaviour ──

    def test_existing_raise_payment_without_payee_is_unchanged(self):
        legacy = WorkOrder.objects.create(
            type=WorkOrder.RAISE_PAYMENT, requester=self.requester, owner=self.requester,
            description='Old-style raise payment', approver=self.approver, is_reviewed=True,
            approval_status='Reviewed',
        )
        self.assertFalse(legacy.uses_raise_payment_flow)

        response = self.approve(legacy.slug)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(PaymentRequisition.objects.count(), 0)  # no auto payment

        self.client.force_authenticate(user=self.requester)
        response = self.client.patch(f'{WORK_ORDERS}{legacy.slug}/', {'description': 'edited'}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    # ── category ↔ subcategory mapping ───────────────────────────────────────

    def test_subcategory_is_required(self):
        response = self.create(subcategory=None)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('subcategory', response.data)

    def test_subcategory_must_belong_to_category(self):
        response = self.create(subcategory=self.generator_sub.pk)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('subcategory', response.data)

    def test_inactive_subcategory_is_rejected(self):
        self.ekedc_bill.is_active = False
        self.ekedc_bill.save()
        response = self.create()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('subcategory', response.data)
