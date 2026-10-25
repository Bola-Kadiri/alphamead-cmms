"""
Stage 2 · Work Order in the five-stage flow: Procurement & Store (team) prices a
client-approved Work Request → Category Manager reviews or sends back → Client
approves the price (spend committed) or rejects (job ends) → contractor accepts.
"""
import json
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Client, Vendor
from asset_inventory.models import AssetCategory, AssetSubCategory
from facility.models import Facility
from work.models import ApprovalMatrix, CompanyApprovers, Notification, WorkOrder, WorkRequest
from work.models import work_request_flow as stage1
from work.models.action_log import history

User = get_user_model()
WORK_ORDERS = '/work/api/work-orders/'
MY_TASKS = '/work/api/my-tasks/'
TEMP_MEDIA = tempfile.mkdtemp()


def make_user(email, roles, first, facilities=(), clients=(), vendor=None):
    user = User.objects.create_user(email=email, password='x', first_name=first, last_name='Test')
    user.roles = roles
    user.is_active = True
    user.vendor = vendor
    user.save()
    user.facility.set(facilities)
    user.clients.set(clients)
    return user


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class Stage2WorkOrderTests(TestCase):

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.nestle = Client.objects.create(name='NESTLE (H.O) NIG', type='Company', code='CLI-W2')
        self.agbara = Facility.objects.create(name='Nestle Agbara', code='NA-01', client=self.nestle)
        self.hvac = AssetCategory.objects.create(type='Asset', code='HVAC', name='HVAC')
        self.split = AssetSubCategory.objects.create(code='SPLIT', name='Split unit', type='Asset', asset_category=self.hvac)
        self.cool_air = Vendor.objects.create(name='Cool Air Ltd', type='Company', phone='0800', account_name='Cool Air',
                                              bank='Zenith Bank', account_number='2223334445', currency='NGN')
        self.no_bank = Vendor.objects.create(name='Cash Only Ltd', type='Company', currency='NGN')

        self.tunde = make_user('tunde@example.com', 'REQUESTER', 'Tunde', [self.agbara])
        self.femi = make_user('femi@example.com', 'APPROVER', 'Femi', [self.agbara])
        self.ngozi = make_user('ngozi@example.com', 'CLIENT', 'Ngozi', clients=[self.nestle])
        self.bola = make_user('bola@example.com', 'PROCUREMENT AND STORE', 'Bola')
        self.chidi = make_user('chidi@example.com', 'PROCUREMENT AND STORE', 'Chidi')
        self.emeka = make_user('emeka@coolair.example', 'CONTRACTOR', 'Emeka', vendor=self.cool_air)
        make_user('kemi@example.com', 'CENTRAL OPERATION', 'Kemi')
        make_user('seun@example.com', 'AP OFFICER', 'Seun')
        make_user('ibrahim@example.com', 'REVIEWER', 'Ibrahim')
        adaeze = make_user('adaeze@example.com', 'HEAD OF FINANCE & TREASURY', 'Adaeze')
        company = CompanyApprovers.current()
        company.head_of_finance = adaeze
        company.save()
        ApprovalMatrix.objects.create(facility=self.agbara, approver=self.femi, client_rep=self.ngozi).go_live(adaeze)

        # A client-approved Work Request (Stage 1 done).
        self.wr = WorkRequest.objects.create(type='Work', requester=self.tunde, owner=self.tunde, facility=self.agbara,
                                             category=self.hvac, subcategory=self.split, priority='High',
                                             description='Reception AC not cooling', flow=WorkRequest.FIVE_STAGE)
        stage1.raise_request(self.wr, self.tunde)
        stage1.review(self.wr, self.femi, 'Femi Test')
        stage1.client_approve(self.wr, self.ngozi, 'Ngozi Test')

    # ── helpers ──────────────────────────────────────────────────────────────

    def api(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def post(self, user, path, data=None, fmt='json'):
        with self.captureOnCommitCallbacks(execute=True):
            return self.api(user).post(path, data or {}, format=fmt)

    def start(self, user=None):
        response = self.post(user or self.bola, f'{WORK_ORDERS}flow-start/', {'work_request': self.wr.slug})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return WorkOrder.objects.get(slug=response.data['slug'])

    def price(self, wo, user=None, vendor=None, client_unit='150000', with_file=True):
        data = {
            'lines': json.dumps([{'description': 'Compressor replacement', 'quantity': 1,
                                  'unit_cost_vendor': '120000', 'unit_cost_client': client_unit}]),
            'vendor': (vendor or self.cool_air).pk, 'quotation_reference': 'CA-Q-2210',
            'po_number': 'PO-2026-0341', 'expected_start_date': '2026-10-28',
        }
        if with_file:
            data['resources'] = SimpleUploadedFile('quote.pdf', b'%PDF-1.4 quote', content_type='application/pdf')
        return self.post(user or self.bola, f'{WORK_ORDERS}{wo.slug}/flow-pricing/', data, fmt='multipart')

    def priced_and_submitted(self):
        wo = self.start()
        self.price(wo)
        response = self.post(self.bola, f'{WORK_ORDERS}{wo.slug}/flow-submit/')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return wo

    def approved(self):
        wo = self.priced_and_submitted()
        self.post(self.femi, f'{WORK_ORDERS}{wo.slug}/flow-review/', {'signature': 'Femi Test'})
        response = self.post(self.ngozi, f'{WORK_ORDERS}{wo.slug}/flow-approve/', {'signature': 'Ngozi Test', 'confirmed': True})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return wo

    # ── queue and starting ───────────────────────────────────────────────────

    def test_approved_request_waits_in_the_procurement_queue(self):
        queue = self.api(self.chidi).get(f'{WORK_ORDERS}procurement-queue/').data
        self.assertEqual([row['number'] for row in queue], [self.wr.work_request_number])
        self.assertEqual([t['kind'] for t in self.api(self.bola).get(MY_TASKS).data], ['work_order_to_raise'])
        self.start()
        self.assertEqual(self.api(self.chidi).get(f'{WORK_ORDERS}procurement-queue/').data, [])

    def test_only_procurement_starts_a_work_order(self):
        response = self.post(self.tunde, f'{WORK_ORDERS}flow-start/', {'work_request': self.wr.slug})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_one_work_order_per_request(self):
        self.start()
        response = self.post(self.chidi, f'{WORK_ORDERS}flow-start/', {'work_request': self.wr.slug})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ── pricing and submitting ───────────────────────────────────────────────

    def test_pricing_totals_and_margin(self):
        wo = self.start()
        response = self.price(wo)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['pricing'], {'client_price': '150000.00', 'vendor_cost': '120000.00',
                                                    'margin': '30000.00', 'margin_percent': 20.0})

    def test_submit_checks_everything(self):
        wo = self.start()
        response = self.post(self.bola, f'{WORK_ORDERS}{wo.slug}/flow-submit/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        for text in ('Choose the vendor', 'quote line', 'quotation reference', 'PO number', 'start date', 'quotation.'):
            self.assertIn(text, response.data['error'])

    def test_vendor_must_be_payable(self):
        wo = self.start()
        self.price(wo, vendor=self.no_bank)
        response = self.post(self.bola, f'{WORK_ORDERS}{wo.slug}/flow-submit/')
        self.assertIn('no bank details', response.data['error'])

    def test_client_price_not_below_vendor_cost(self):
        wo = self.start()
        self.price(wo, client_unit='100000')
        response = self.post(self.bola, f'{WORK_ORDERS}{wo.slug}/flow-submit/')
        self.assertIn('cannot be lower than the vendor cost', response.data['error'])

    def test_any_procurement_member_can_submit(self):
        wo = self.start(self.bola)
        self.price(wo, user=self.chidi)
        response = self.post(self.chidi, f'{WORK_ORDERS}{wo.slug}/flow-submit/')
        self.assertEqual(response.data['status'], 'Awaiting Review')
        self.assertTrue(Notification.objects.filter(recipient=self.femi).exists())

    # ── review and client decision ───────────────────────────────────────────

    def test_review_shows_price_check_and_goes_to_client(self):
        wo = self.priced_and_submitted()
        data = self.api(self.femi).get(f'{WORK_ORDERS}{wo.slug}/flow/').data
        self.assertEqual(data['my_actions'], ['review', 'send_back'])
        self.assertIn('margin', data['pricing'])
        response = self.post(self.femi, f'{WORK_ORDERS}{wo.slug}/flow-review/', {'signature': 'Femi Test'})
        self.assertEqual(response.data['status'], 'Awaiting Client')

    def test_send_back_then_reprice(self):
        wo = self.priced_and_submitted()
        response = self.post(self.femi, f'{WORK_ORDERS}{wo.slug}/flow-send-back/', {'reason': 'Price too high'})
        self.assertEqual(response.data['status'], 'Sent Back')
        self.price(wo, client_unit='140000')
        response = self.post(self.chidi, f'{WORK_ORDERS}{wo.slug}/flow-submit/')
        self.assertEqual(response.data['status'], 'Awaiting Review')
        self.assertEqual([a.action for a in history(wo)], ['raised', 'sent_back', 'resubmitted'])

    def test_client_sees_client_price_only(self):
        wo = self.priced_and_submitted()
        self.post(self.femi, f'{WORK_ORDERS}{wo.slug}/flow-review/', {'signature': 'Femi Test'})
        data = self.api(self.ngozi).get(f'{WORK_ORDERS}{wo.slug}/flow/').data
        self.assertEqual(data['pricing'], {'client_price': '150000.00'})
        self.assertNotIn('unit_cost_vendor', data['lines'][0])
        self.assertIsNone(data['vendor'])
        self.assertEqual(data['price_check'], [])
        self.assertEqual(data['my_actions'], ['approve', 'reject'])

    def test_client_must_confirm_they_agree_to_pay(self):
        wo = self.priced_and_submitted()
        self.post(self.femi, f'{WORK_ORDERS}{wo.slug}/flow-review/', {'signature': 'Femi Test'})
        response = self.post(self.ngozi, f'{WORK_ORDERS}{wo.slug}/flow-approve/', {'signature': 'Ngozi Test'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('agrees to pay', response.data['error'])

    def test_client_approval_commits_and_tells_the_contractor(self):
        wo = self.approved()
        wo.refresh_from_db()
        self.assertEqual(wo.approval_status, 'Approved')
        self.assertTrue(Notification.objects.filter(recipient=self.emeka).exists())
        response = self.post(self.bola, f'{WORK_ORDERS}{wo.slug}/flow-pricing/', {'po_number': 'X'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)  # price is locked

    def test_client_rejection_ends_the_job(self):
        wo = self.priced_and_submitted()
        self.post(self.femi, f'{WORK_ORDERS}{wo.slug}/flow-review/', {'signature': 'Femi Test'})
        response = self.post(self.ngozi, f'{WORK_ORDERS}{wo.slug}/flow-reject/', {'reason': 'Above budget'})
        self.assertEqual(response.data['status'], 'Client Rejected')
        self.wr.refresh_from_db()
        self.assertEqual(self.wr.approval_status, 'Client Rejected')

    # ── contractor ───────────────────────────────────────────────────────────

    def test_contractor_sees_and_accepts_own_job(self):
        wo = self.approved()
        listed = self.api(self.emeka).get(WORK_ORDERS).data
        results = listed['results'] if isinstance(listed, dict) else listed
        self.assertEqual([r['slug'] for r in results], [wo.slug])
        data = self.api(self.emeka).get(f'{WORK_ORDERS}{wo.slug}/flow/').data
        self.assertEqual(data['pricing'], {'vendor_cost': '120000.00'})  # never the client price
        response = self.post(self.emeka, f'{WORK_ORDERS}{wo.slug}/flow-accept/',
                             {'start_date': '2026-10-28', 'technician': 'Emeka Obi'})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['accepted']['technician'], 'Emeka Obi')
        self.assertEqual(history(wo).last().action, 'accepted')

    def test_other_vendor_cannot_see_or_accept(self):
        wo = self.approved()
        other = make_user('frost@example.com', 'CONTRACTOR', 'Frost', vendor=self.no_bank)
        listed = self.api(other).get(WORK_ORDERS).data
        results = listed['results'] if isinstance(listed, dict) else listed
        self.assertEqual(results, [])
        response = self.post(other, f'{WORK_ORDERS}{wo.slug}/flow-accept/', {'start_date': '2026-10-28', 'technician': 'X'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_generic_edit_is_refused(self):
        wo = self.priced_and_submitted()
        response = self.api(self.bola).patch(f'{WORK_ORDERS}{wo.slug}/', {'cost': '1'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
