"""
CLIENT role: view-only access to their own client's facilities, with Alpha
Mead's internal costs and vendor details masked.

Uses real JWTs (not force_authenticate) so the ClientAccessMiddleware is
exercised exactly as it is for the React app.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import Client, Vendor
from facility.models import Facility
from work.models import (PaymentRequisition, WorkOrder, WorkOrderCompletion, WorkRequest,
                         WorkRequestQuotationItem)

User = get_user_model()


def make_user(email, roles, **extra):
    user = User.objects.create_user(email=email, password='x', first_name='T', last_name='U')
    user.roles = roles
    user.is_active = True
    for key, value in extra.items():
        setattr(user, key, value)
    user.save()
    return user


def api_for(user):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(user).access_token}')
    return client


class ClientRoleTests(TestCase):

    def setUp(self):
        self.nestle = Client.objects.create(name='NESTLE (H.O) NIG', type='Company', code='CLI-T1')
        self.other = Client.objects.create(name='Other Co', type='Company', code='CLI-T2')
        self.agbara = Facility.objects.create(name='Nestle Agbara', code='NA-01', client=self.nestle)
        self.elsewhere = Facility.objects.create(name='Other Site', code='OS-01', client=self.other)

        self.staff = make_user('staff@example.com', 'REQUESTER')
        self.admin = make_user('admin@example.com', 'SUPER ADMIN')
        self.client_user = make_user('manager@nestle.example', 'CLIENT')
        self.client_user.clients.add(self.nestle)
        self.vendor = Vendor.objects.create(
            name='Cool Air Ltd', type='Company', phone='0800', account_name='Cool Air',
            bank='Zenith Bank', account_number='2223334445', currency='NGN',
        )

        # Repair at the client's site, priced: vendor 100,000 / client 150,000.
        self.wr = WorkRequest.objects.create(type='Work', requester=self.staff, owner=self.staff,
                                             facility=self.agbara, description='AC not cooling',
                                             po_amount=Decimal('100000'), vendor=self.vendor)
        WorkRequestQuotationItem.objects.create(work_request=self.wr, description='Regas', quantity=1,
                                                unit_cost_vendor=Decimal('100000'),
                                                unit_cost_client=Decimal('150000'))
        self.wo = WorkOrder.objects.create(type='FROM-WORK-REQUEST', source_work_request=self.wr,
                                           requester=self.staff, owner=self.staff, facility=self.agbara,
                                           cost=Decimal('100000'), vendor=self.vendor,
                                           approval_status='Approved')
        self.wcc = WorkOrderCompletion.objects.create(work_order=self.wo, owner=self.staff,
                                                      approval_status='Approved')
        self.bill = WorkOrder.objects.create(type=WorkOrder.RAISE_PAYMENT, requester=self.staff,
                                             owner=self.staff, facility=self.agbara,
                                             cost=Decimal('80000'), payee=self.vendor)
        # Another client's site.
        self.other_wr = WorkRequest.objects.create(type='Work', requester=self.staff, owner=self.staff,
                                                   facility=self.elsewhere, description='Leak')
        self.other_wo = WorkOrder.objects.create(type='Unplanned', requester=self.staff, owner=self.staff,
                                                 facility=self.elsewhere)
        self.api = api_for(self.client_user)

    @staticmethod
    def ids(response):
        data = response.data
        rows = data['results'] if isinstance(data, dict) and 'results' in data else data
        return {row['id'] for row in rows}

    # ── sees only their own facilities ───────────────────────────────────────

    def test_sees_only_own_facilities_work(self):
        r = self.api.get('/work/api/work-requests/')
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
        self.assertEqual(self.ids(r), {self.wr.id})

        r = self.api.get('/work/api/work-orders/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(self.ids(r), {self.wo.id})  # bill hidden: utility bills off by default

        r = self.api.get('/work/api/work-order-completions/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(self.ids(r), {self.wcc.id})

        r = self.api.get('/facility/api/api/facilities/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(self.ids(r), {self.agbara.id})

    def test_cannot_open_another_clients_record(self):
        r = self.api.get(f'/work/api/work-orders/{self.other_wo.slug}/')
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)
        r = self.api.get(f'/work/api/work-requests/{self.other_wr.slug}/')
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_utility_bills_follow_the_client_setting(self):
        self.nestle.show_utility_bills = True
        self.nestle.save()
        r = self.api.get('/work/api/work-orders/')
        self.assertEqual(self.ids(r), {self.wo.id, self.bill.id})

    def test_no_facilities_linked_means_nothing_visible(self):
        lonely = make_user('lonely@client.example', 'CLIENT')
        r = api_for(lonely).get('/work/api/work-orders/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(self.ids(r), set())

    # ── costs and vendor details masked ──────────────────────────────────────

    def test_work_order_shows_client_price_only(self):
        r = self.api.get(f'/work/api/work-orders/{self.wo.slug}/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        data = r.data
        self.assertEqual(Decimal(data['cost']), Decimal('150000'))  # client price, not vendor 100,000
        for hidden in ('vendor', 'vendor_detail', 'payee_detail', 'linked_payment_requisition',
                       'approver_detail', 'reviewers_detail'):
            self.assertNotIn(hidden, data)
        self.assertEqual(set(data['source_work_request_detail']),
                         {'id', 'work_request_number', 'total_cost_client'})
        self.assertNotIn('100000', str(data))

    def test_work_request_hides_vendor_cost_margin_and_lines(self):
        data = self.api.get(f'/work/api/work-requests/{self.wr.slug}/').data
        for hidden in ('total_cost_vendor', 'margin', 'quotation_items', 'vendor_detail',
                       'po_amount', 'po_document', 'vendor_invoice'):
            self.assertNotIn(hidden, data)
        self.assertEqual(Decimal(str(data['total_cost_client'])), Decimal('150000'))

    def test_nested_work_order_in_wcc_is_masked(self):
        data = self.api.get(f'/work/api/work-order-completions/{self.wcc.id}/').data
        self.assertNotIn('vendor_detail', data['work_order_detail'])
        self.assertEqual(Decimal(data['work_order_detail']['cost']), Decimal('150000'))

    # ── view only ────────────────────────────────────────────────────────────

    def test_cannot_change_anything(self):
        attempts = [
            ('post', '/work/api/work-requests/', {'type': 'Work', 'facility': self.agbara.id}),
            ('patch', f'/work/api/work-orders/{self.wo.slug}/', {'description': 'x'}),
            ('delete', f'/work/api/work-orders/{self.wo.slug}/', None),
            ('post', f'/work/api/work-orders/{self.wo.slug}/approve-by-approver/', None),
            ('post', f'/work/api/work-requests/{self.wr.slug}/final-approve/', None),
            ('post', '/work/api/work-order-completions/', {'work_order': self.wo.id}),
        ]
        for method, url, body in attempts:
            r = getattr(self.api, method)(url, body, format='json')
            self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN, (method, url))
        self.wo.refresh_from_db()
        self.assertEqual(self.wo.approval_status, 'Approved')

    def test_internal_screens_are_blocked(self):
        for url in ('/work/api/payment-requisitions/', '/accounts/api/users/', '/accounts/api/vendors/',
                    '/work/api/work-orders/approvers/', '/work/api/work-requests/approved-work-requests/',
                    '/dashboard/api/dashboard/', '/work/api/ppm/'):
            self.assertEqual(self.api.get(url).status_code, status.HTTP_403_FORBIDDEN, url)

    def test_payment_requisitions_never_reachable(self):
        PaymentRequisition.objects.create(requisition_date='2026-10-01', owner=self.staff, pay_to=self.vendor)
        self.assertEqual(self.api.get('/work/api/payment-requisitions/').status_code, status.HTTP_403_FORBIDDEN)

    # ── other roles unaffected ───────────────────────────────────────────────

    def test_super_admin_still_sees_everything(self):
        admin = api_for(self.admin)
        self.assertEqual(self.ids(admin.get('/work/api/work-orders/')),
                         {self.wo.id, self.bill.id, self.other_wo.id})
        data = admin.get(f'/work/api/work-orders/{self.wo.slug}/').data
        self.assertIn('vendor_detail', data)
        self.assertEqual(Decimal(data['cost']), Decimal('100000'))
