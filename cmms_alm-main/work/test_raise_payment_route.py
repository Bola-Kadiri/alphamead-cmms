"""
Raise Payment approval order, decided by the bill amount:
  below ₦100,000:       Requester → Approver → Reviewer
  ₦100,000 or more (or another currency):
                        Requester → Procurement & Store (PO and quotation) → Approver → Reviewer
                        → second (final) approval by the configured user.
Only new Raise Payment bills follow it; everything else is unchanged.
"""
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
from work.models import Notification, PaymentRequisition, RaisePaymentApprovalSettings, WorkOrder

User = get_user_model()
TEMP_MEDIA = tempfile.mkdtemp()
WORK_ORDERS = '/work/api/work-orders/'
SMALL = '99999.99'
LARGE = '2500000.00'


def make_user(email, roles):
    user = User.objects.create_user(email=email, password='testpass123', first_name='Test', last_name='User')
    user.roles = roles
    user.is_active = True
    user.save()
    return user


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class RaisePaymentApprovalRouteTests(TestCase):

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.client = APIClient()
        self.requester = make_user('requester@example.com', 'REQUESTER')
        self.reviewer = make_user('reviewer@example.com', 'REVIEWER')
        self.approver = make_user('approver@example.com', 'APPROVER')
        self.admin = make_user('admin@example.com', 'SUPER ADMIN')
        self.wole = make_user('wole.olufore@alphamead.com', 'APPROVER')
        self.procurement = make_user('procurement@example.com', 'PROCUREMENT AND STORE')

        self.facility = Facility.objects.create(name='HQ Office')
        category = AssetCategory.objects.create(type='Expense', code='PHCN', name='PHCN/Power', is_known_cost=True)
        self.category = category
        self.subcategory = AssetSubCategory.objects.create(
            code='EKEDC', name='EKEDC', type='Expense', asset_category=category,
        )
        self.payee = Vendor.objects.create(
            name='EKEDC', type='Company', phone='0800000000', account_name='EKEDC',
            bank='Test Bank', account_number='0011223344', currency='NGN',
        )
        self.bill_no = 0

    # ── helpers ──────────────────────────────────────────────────────────────

    AUTO = object()

    def post_bill(self, cost=SMALL, currency='NGN', final_approver=AUTO):
        """Raise a bill; by default the Requester selects Wole when the amount needs it."""
        self.bill_no += 1
        if final_approver is self.AUTO:
            final_approver = self.wole.pk if (currency != 'NGN' or Decimal(cost) >= Decimal('100000')) else None
        data = {
            'type': WorkOrder.RAISE_PAYMENT, 'invoice_no': f'BILL-{self.bill_no}',
            'description': 'EKEDC bill', 'category': self.category.pk, 'subcategory': self.subcategory.pk,
            'facility': self.facility.pk, 'payee': self.payee.pk, 'cost': cost, 'currency': currency,
            'reviewers': [self.reviewer.pk], 'approver': self.approver.pk,
            'resources': [SimpleUploadedFile('bill.pdf', b'%PDF-1.4 bill', content_type='application/pdf')],
        }
        if final_approver is not None:
            data['final_approver'] = final_approver
        self.client.force_authenticate(user=self.requester)
        return self.client.post(WORK_ORDERS, data, format='multipart')

    def raise_bill(self, cost=SMALL, currency='NGN', final_approver=AUTO):
        response = self.post_bill(cost, currency, final_approver)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return response.data['slug']

    def act(self, user, slug, action, data=None, fmt='json'):
        self.client.force_authenticate(user=user)
        return self.client.post(f'{WORK_ORDERS}{slug}/{action}/', data or {}, format=fmt)

    def procure(self, slug, user=None):
        response = self.act(user or self.procurement, slug, 'procurement-submit', {
            'po_number': 'PO-2026-0101', 'quotation_reference': 'Q-77',
            'po_document': SimpleUploadedFile('po.pdf', b'%PDF-1.4 po', content_type='application/pdf'),
            'quotation_file': SimpleUploadedFile('quote.pdf', b'%PDF-1.4 quote', content_type='application/pdf'),
        }, 'multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return response

    def status_of(self, slug):
        return WorkOrder.objects.get(slug=slug).approval_status

    # ── the Requester selects the final approver ─────────────────────────────

    def test_final_approver_required_from_one_hundred_thousand(self):
        response = self.post_bill('100000.00', final_approver=None)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('final_approver', response.data)
        self.assertFalse(WorkOrder.objects.exists())

    def test_final_approver_must_be_the_configured_person(self):
        response = self.post_bill(LARGE, final_approver=self.approver.pk)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('final_approver', response.data)

    def test_no_final_approver_below_one_hundred_thousand(self):
        slug = self.raise_bill(SMALL, final_approver=self.wole.pk)
        self.assertIsNone(WorkOrder.objects.get(slug=slug).final_approver)

    def test_selected_final_approver_is_on_the_bill_from_the_start(self):
        response = self.post_bill(LARGE)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['final_approver'], self.wole.pk)
        self.assertTrue(response.data['needs_second_approval'])
        self.assertEqual(response.data['next_step'], 'procurement')

    def test_final_approvers_list_for_the_form(self):
        self.client.force_authenticate(user=self.requester)
        response = self.client.get(f'{WORK_ORDERS}final-approvers/')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['threshold'], '100000.00')
        self.assertEqual([a['email'] for a in response.data['approvers']], ['wole.olufore@alphamead.com'])

    # ── below ₦100,000: Approver → Reviewer → paid ───────────────────────────

    def test_small_bill_approver_then_reviewer(self):
        slug = self.raise_bill(SMALL)
        work_order = WorkOrder.objects.get(slug=slug)
        self.assertEqual(work_order.approval_route, WorkOrder.APPROVER_FIRST)
        self.assertFalse(work_order.needs_procurement)
        self.assertEqual(work_order.approval_status, 'Pending')

        response = self.act(self.approver, slug, 'approve-by-approver')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['approval_status'], 'Approver Approved')
        self.assertEqual(response.data['next_step'], 'reviewer')
        self.assertFalse(PaymentRequisition.objects.exists())  # not paid on the first approval

        response = self.act(self.reviewer, slug, 'approve-by-reviewer')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['approval_status'], 'Approved')
        work_order.refresh_from_db()
        self.assertIsNone(work_order.final_approver)
        self.assertEqual(work_order.linked_payments.get().approval_status, 'approve')

    def test_small_bill_skips_procurement(self):
        slug = self.raise_bill(SMALL)
        self.assertEqual(self.act(self.procurement, slug, 'procurement-submit', {'po_number': 'PO-1'}).status_code,
                         status.HTTP_400_BAD_REQUEST)

    def test_reviewer_cannot_act_before_approver(self):
        slug = self.raise_bill()
        self.assertEqual(self.act(self.reviewer, slug, 'approve-by-reviewer').status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.act(self.reviewer, slug, 'reject-by-reviewer', {'reviewer_reason': 'x'}).status_code,
                         status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.status_of(slug), 'Pending')

    def test_approver_cannot_act_twice(self):
        slug = self.raise_bill()
        self.act(self.approver, slug, 'approve-by-approver')
        self.assertEqual(self.act(self.approver, slug, 'approve-by-approver').status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.act(self.approver, slug, 'reject-by-approver', {'approver_reason': 'x'}).status_code,
                         status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.status_of(slug), 'Approver Approved')

    def test_approver_can_reject_first(self):
        slug = self.raise_bill()
        response = self.act(self.approver, slug, 'reject-by-approver', {'approver_reason': 'Wrong meter number'})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(self.status_of(slug), 'Approver Rejected')

    def test_approval_limit_applies_at_first_approval(self):
        self.approver.approval_limit = Decimal('1000.00')
        self.approver.save()
        slug = self.raise_bill()
        self.assertEqual(self.act(self.approver, slug, 'approve-by-approver').status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.status_of(slug), 'Pending')

    # ── ₦100,000 or more: Procurement & Store first ──────────────────────────

    def test_large_bill_waits_for_procurement(self):
        slug = self.raise_bill(LARGE)
        work_order = WorkOrder.objects.get(slug=slug)
        self.assertTrue(work_order.needs_procurement)
        self.assertEqual(work_order.approval_status, 'Awaiting Procurement')
        response = self.act(self.approver, slug, 'approve-by-approver')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.status_of(slug), 'Awaiting Procurement')

    def test_procurement_needs_the_po_and_the_quotation(self):
        slug = self.raise_bill(LARGE)
        response = self.act(self.procurement, slug, 'procurement-submit', {}, 'multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('po_number', response.data)
        self.assertIn('po_document', response.data)
        self.assertIn('quotation_file', response.data)

        response = self.procure(slug)
        self.assertEqual(response.data['approval_status'], 'Pending')
        self.assertEqual(response.data['next_step'], 'approver')
        work_order = WorkOrder.objects.get(slug=slug)
        self.assertEqual((work_order.po_number, work_order.procurement_by), ('PO-2026-0101', self.procurement))
        self.assertTrue(work_order.po_document)
        self.assertTrue(work_order.quotation_file)

    def test_only_procurement_adds_the_po(self):
        slug = self.raise_bill(LARGE)
        for user in (self.requester, self.approver, self.reviewer, self.wole):
            response = self.act(user, slug, 'procurement-submit', {'po_number': 'PO-1'})
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, user.email)
        self.assertEqual(self.status_of(slug), 'Awaiting Procurement')

    def test_procurement_returns_then_requester_resubmits(self):
        slug = self.raise_bill(LARGE)
        self.assertEqual(self.act(self.procurement, slug, 'procurement-return', {}).status_code, status.HTTP_400_BAD_REQUEST)
        response = self.act(self.procurement, slug, 'procurement-return', {'procurement_reason': 'Wrong bill attached'})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['next_step'], 'requester')

        # The Requester can fix the bill while it is returned, then resubmit.
        self.client.force_authenticate(user=self.requester)
        response = self.client.patch(f'{WORK_ORDERS}{slug}/', {'description': 'EKEDC bill, corrected'}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(self.act(self.approver, slug, 'raise-payment-resubmit').status_code, status.HTTP_403_FORBIDDEN)
        response = self.act(self.requester, slug, 'raise-payment-resubmit')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['approval_status'], 'Awaiting Procurement')

    def test_bill_corrected_below_the_threshold_goes_straight_to_the_approver(self):
        slug = self.raise_bill(LARGE)
        self.act(self.procurement, slug, 'procurement-return', {'procurement_reason': 'Amount is wrong'})
        self.client.force_authenticate(user=self.requester)
        response = self.client.patch(f'{WORK_ORDERS}{slug}/', {'cost': '50000.00'}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        response = self.act(self.requester, slug, 'raise-payment-resubmit')
        self.assertEqual(response.data['approval_status'], 'Pending')
        self.assertFalse(WorkOrder.objects.get(slug=slug).needs_procurement)

    def test_bill_edited_up_to_a_large_amount_needs_procurement(self):
        slug = self.raise_bill(SMALL)
        self.client.force_authenticate(user=self.requester)
        response = self.client.patch(f'{WORK_ORDERS}{slug}/', {'cost': LARGE, 'final_approver': self.wole.pk},
                                     format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(self.status_of(slug), 'Awaiting Procurement')

    def test_procurement_sees_the_bill_in_their_list(self):
        slug = self.raise_bill(LARGE)
        self.client.force_authenticate(user=self.procurement)
        rows = self.client.get(WORK_ORDERS).data
        rows = rows['results'] if isinstance(rows, dict) else rows
        self.assertIn(slug, [row['slug'] for row in rows])

    # ── then Approver → Reviewer → second approval ───────────────────────────

    def test_exactly_one_hundred_thousand_takes_the_full_route(self):
        slug = self.raise_bill('100000.00')
        self.procure(slug)
        self.act(self.approver, slug, 'approve-by-approver')
        response = self.act(self.reviewer, slug, 'approve-by-reviewer')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['approval_status'], 'Awaiting Final Approval')
        self.assertEqual(response.data['next_step'], 'final_approver')
        self.assertEqual(response.data['final_approver'], self.wole.pk)
        self.assertFalse(PaymentRequisition.objects.exists())

        response = self.act(self.wole, slug, 'final-approve')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        work_order = WorkOrder.objects.get(slug=slug)
        self.assertEqual(work_order.approval_status, 'Approved')
        self.assertIsNotNone(work_order.final_approved_at)
        self.assertEqual(work_order.linked_payments.get().approval_status, 'approve')

    def large_bill_reviewed(self):
        slug = self.raise_bill(LARGE)
        self.procure(slug)
        self.act(self.approver, slug, 'approve-by-approver')
        self.act(self.reviewer, slug, 'approve-by-reviewer')
        return slug

    def test_only_the_second_approver_can_give_final_approval(self):
        slug = self.large_bill_reviewed()
        for user in (self.approver, self.reviewer, self.requester, self.admin, self.procurement):
            self.assertEqual(self.act(user, slug, 'final-approve').status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.status_of(slug), 'Awaiting Final Approval')
        self.assertFalse(PaymentRequisition.objects.exists())

    def test_second_approver_can_reject_with_reason(self):
        slug = self.large_bill_reviewed()
        self.assertEqual(self.act(self.wole, slug, 'final-reject').status_code, status.HTTP_400_BAD_REQUEST)
        response = self.act(self.wole, slug, 'final-reject', {'final_approver_reason': 'Amount looks too high'})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(self.status_of(slug), 'Final Approver Rejected')
        self.assertFalse(PaymentRequisition.objects.exists())

    def test_final_rejected_bill_can_be_raised_again(self):
        slug = self.raise_bill(LARGE)
        WorkOrder.objects.filter(slug=slug).update(approval_status='Final Approver Rejected')
        self.bill_no -= 1  # same bill number again
        self.raise_bill(LARGE)

    def test_other_currencies_always_take_the_full_route(self):
        slug = self.raise_bill('100.00', currency='USD')
        self.assertEqual(self.status_of(slug), 'Awaiting Procurement')
        self.procure(slug)
        self.act(self.approver, slug, 'approve-by-approver')
        response = self.act(self.reviewer, slug, 'approve-by-reviewer')
        self.assertEqual(response.data['approval_status'], 'Awaiting Final Approval')

    def test_missing_second_approver_account_blocks_raising(self):
        self.wole.delete()
        response = self.post_bill(LARGE, final_approver=None)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('wole.olufore@alphamead.com', str(response.data['final_approver']))

    def test_threshold_and_approver_come_from_settings(self):
        settings = RaisePaymentApprovalSettings.current()
        settings.threshold = Decimal('3000000.00')
        settings.save()
        slug = self.raise_bill(LARGE)
        self.assertEqual(self.status_of(slug), 'Pending')  # below the raised threshold: no Procurement step
        self.act(self.approver, slug, 'approve-by-approver')
        self.assertEqual(self.act(self.reviewer, slug, 'approve-by-reviewer').data['approval_status'], 'Approved')

    def test_second_approver_sees_the_bill_in_their_list(self):
        slug = self.large_bill_reviewed()
        self.client.force_authenticate(user=self.wole)
        response = self.client.get(WORK_ORDERS)
        rows = response.data['results'] if isinstance(response.data, dict) else response.data
        self.assertIn(slug, [row['slug'] for row in rows])

    # ── locked while being approved ──────────────────────────────────────────

    def test_bill_cannot_be_edited_mid_approval(self):
        slug = self.raise_bill(LARGE)
        self.client.force_authenticate(user=self.requester)
        response = self.client.patch(f'{WORK_ORDERS}{slug}/', {'cost': '900000.00'}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)  # waiting for Procurement
        self.procure(slug)
        self.act(self.approver, slug, 'approve-by-approver')
        self.client.force_authenticate(user=self.requester)
        response = self.client.patch(f'{WORK_ORDERS}{slug}/', {'cost': '900000.00'}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(WorkOrder.objects.get(slug=slug).cost, Decimal(LARGE))

    # ── notifications ────────────────────────────────────────────────────────

    def test_each_person_is_notified_in_turn(self):
        with self.captureOnCommitCallbacks(execute=True):
            slug = self.raise_bill(LARGE)
        self.assertTrue(Notification.objects.filter(recipient=self.procurement, title__contains='PO and Quotation').exists())
        self.assertFalse(Notification.objects.filter(recipient=self.approver).exists())

        with self.captureOnCommitCallbacks(execute=True):
            self.procure(slug)
        self.assertTrue(Notification.objects.filter(recipient=self.approver).exists())
        self.assertFalse(Notification.objects.filter(recipient=self.reviewer).exists())

        with self.captureOnCommitCallbacks(execute=True):
            self.act(self.approver, slug, 'approve-by-approver')
        self.assertTrue(Notification.objects.filter(recipient=self.reviewer).exists())

        with self.captureOnCommitCallbacks(execute=True):
            self.act(self.reviewer, slug, 'approve-by-reviewer')
        self.assertTrue(Notification.objects.filter(recipient=self.wole, title__contains='Final Approval').exists())

    def test_requester_is_told_when_procurement_returns_it(self):
        slug = self.raise_bill(LARGE)
        with self.captureOnCommitCallbacks(execute=True):
            self.act(self.procurement, slug, 'procurement-return', {'procurement_reason': 'Wrong bill attached'})
        self.assertTrue(Notification.objects.filter(recipient=self.requester, title__contains='Returned by Procurement').exists())

    def test_small_bill_goes_straight_to_the_approver(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.raise_bill(SMALL)
        self.assertTrue(Notification.objects.filter(recipient=self.approver).exists())
        self.assertFalse(Notification.objects.filter(recipient=self.procurement).exists())

    # ── everything else unchanged ────────────────────────────────────────────

    def test_bill_already_in_progress_keeps_old_order(self):
        old = WorkOrder.objects.create(
            type=WorkOrder.RAISE_PAYMENT, requester=self.requester, owner=self.requester, facility=self.facility,
            category=self.category, subcategory=self.subcategory, payee=self.payee, cost=Decimal(LARGE),
            currency='NGN', approver=self.approver, invoice_no='OLD-1',
        )
        old.reviewers.set([self.reviewer])
        self.assertIsNone(old.approval_route)
        self.assertEqual(self.act(self.reviewer, old.slug, 'approve-by-reviewer').status_code, status.HTTP_200_OK)
        response = self.act(self.approver, old.slug, 'approve-by-approver')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(self.status_of(old.slug), 'Approved')
        self.assertTrue(PaymentRequisition.objects.exists())

    def test_large_bill_raised_before_the_procurement_step_keeps_going(self):
        old = WorkOrder.objects.create(
            type=WorkOrder.RAISE_PAYMENT, requester=self.requester, owner=self.requester, facility=self.facility,
            category=self.category, subcategory=self.subcategory, payee=self.payee, cost=Decimal('500000.00'),
            currency='NGN', approver=self.approver, invoice_no='OLD-2', approval_route=WorkOrder.APPROVER_FIRST,
        )
        old.reviewers.set([self.reviewer])
        response = self.act(self.approver, old.slug, 'approve-by-approver')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_normal_work_order_keeps_reviewer_then_approver(self):
        self.client.force_authenticate(user=self.requester)
        response = self.client.post(WORK_ORDERS, {
            'type': 'Unplanned', 'description': 'Broken AC', 'facility': self.facility.pk,
            'reviewers': [self.reviewer.pk], 'approver': self.approver.pk, 'cost': '5000000.00',
        }, format='multipart')
        slug = response.data['slug']
        self.assertIsNone(response.data['approval_route'])
        self.assertFalse(response.data['needs_procurement'])
        self.assertEqual(self.act(self.approver, slug, 'approve-by-approver').status_code, status.HTTP_400_BAD_REQUEST)
        self.act(self.reviewer, slug, 'approve-by-reviewer')
        self.assertEqual(self.act(self.approver, slug, 'approve-by-approver').status_code, status.HTTP_200_OK)
        self.assertEqual(self.status_of(slug), 'Approved')
        self.assertIsNone(WorkOrder.objects.get(slug=slug).final_approver)
