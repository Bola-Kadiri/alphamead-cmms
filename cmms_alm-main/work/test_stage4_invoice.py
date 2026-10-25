"""
Stage 4 · Vendor Invoice in the five-stage flow: the contractor submits against the
approved WCC (or AP enters it for a vendor without a login) → AP Officers (team)
check the three-way match → Head of Finance & Treasury (named) approves.
"""
import shutil
import tempfile
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Client, Vendor
from asset_inventory.models import AssetCategory, AssetSubCategory
from facility.models import Facility
from work.models import ApprovalMatrix, CompanyApprovers, Invoice, Notification, WorkRequest
from work.models import completion_flow as stage3
from work.models import work_order_flow as stage2
from work.models import work_request_flow as stage1
from work.models.action_log import history

User = get_user_model()
INVOICES = '/work/api/invoices/'
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


def pdf(name='invoice.pdf'):
    return SimpleUploadedFile(name, b'%PDF-1.4 invoice', content_type='application/pdf')


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class Stage4InvoiceTests(TestCase):

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        nestle = Client.objects.create(name='NESTLE (H.O) NIG', type='Company', code='CLI-W4')
        agbara = Facility.objects.create(name='Nestle Agbara', code='NA-01', client=nestle)
        hvac = AssetCategory.objects.create(type='Asset', code='HVAC', name='HVAC')
        split = AssetSubCategory.objects.create(code='SPLIT', name='Split unit', type='Asset', asset_category=hvac)
        self.cool_air = Vendor.objects.create(name='Cool Air Ltd', type='Company', phone='0800', account_name='Cool Air',
                                              bank='Zenith Bank', account_number='2223334445', currency='NGN')
        self.frost = Vendor.objects.create(name='Frost Tech', type='Company', phone='0801', account_name='Frost',
                                           bank='GTBank', account_number='1112223334', currency='NGN')

        tunde = make_user('tunde@example.com', 'REQUESTER', 'Tunde', [agbara])
        femi = make_user('femi@example.com', 'APPROVER', 'Femi', [agbara])
        ngozi = make_user('ngozi@example.com', 'CLIENT', 'Ngozi', clients=[nestle])
        bola = make_user('bola@example.com', 'PROCUREMENT AND STORE', 'Bola')
        kemi = make_user('kemi@example.com', 'CENTRAL OPERATION', 'Kemi')
        self.emeka = make_user('emeka@coolair.example', 'CONTRACTOR', 'Emeka', vendor=self.cool_air)
        self.frost_user = make_user('frost@example.com', 'CONTRACTOR', 'Frosty', vendor=self.frost)
        self.seun = make_user('seun@example.com', 'AP OFFICER', 'Seun')
        self.tola = make_user('tola@example.com', 'AP OFFICER', 'Tola')
        make_user('ibrahim@example.com', 'REVIEWER', 'Ibrahim')
        self.adaeze = make_user('adaeze@example.com', 'HEAD OF FINANCE & TREASURY', 'Adaeze')
        company = CompanyApprovers.current()
        company.head_of_finance = self.adaeze
        company.save()
        ApprovalMatrix.objects.create(facility=agbara, approver=femi, client_rep=ngozi).go_live(self.adaeze)

        # Stages 1–3 done.
        wr = WorkRequest.objects.create(type='Work', requester=tunde, owner=tunde, facility=agbara, category=hvac,
                                        subcategory=split, priority='High', description='Reception AC not cooling',
                                        flow=WorkRequest.FIVE_STAGE)
        stage1.raise_request(wr, tunde)
        stage1.review(wr, femi, 'Femi Test')
        stage1.client_approve(wr, ngozi, 'Ngozi Test')
        self.wo = stage2.start(wr, bola)
        stage2.save_pricing(self.wo, bola, vendor=self.cool_air, quotation_reference='CA-Q-1', po_number='PO-1',
                            expected_start_date='2026-10-28', files=[pdf('q.pdf')],
                            lines=[{'description': 'Compressor', 'quantity': 1, 'unit_cost_vendor': '120000',
                                    'unit_cost_client': '150000'}])
        stage2.submit(self.wo, bola)
        stage2.review(self.wo, femi, 'Femi Test')
        stage2.client_approve(self.wo, ngozi, 'Ngozi Test', True)
        self.wcc = stage3.start(self.wo, tunde)
        now = timezone.now()
        stage3.save_details(self.wcc, tunde, started_at=now - timedelta(hours=8), finished_at=now - timedelta(hours=2),
                            technician='Emeka Obi', vendor_rating=4, completion_notes='Done')
        for kind in stage3.REQUIRED_EVIDENCE:
            stage3.add_evidence(self.wcc, tunde, kind, SimpleUploadedFile(f'{kind}.jpg', b'img', 'image/jpeg'))
        stage3.submit(self.wcc, tunde)
        stage3.verify(self.wcc, kemi, 'Kemi Test', timezone.localdate())
        stage3.approve(self.wcc, femi, 'Femi Test')

    # ── helpers ──────────────────────────────────────────────────────────────

    def api(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def post(self, user, path, data=None, fmt='json'):
        with self.captureOnCommitCallbacks(execute=True):
            return self.api(user).post(path, data or {}, format=fmt)

    def started(self, user=None):
        response = self.post(user or self.emeka, f'{INVOICES}flow-start/', {'completion': self.wcc.pk})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return Invoice.objects.get(pk=response.data['id'])

    def fill(self, inv, user=None, amount='120000', vat=True, number='INV-CA-0912'):
        return self.post(user or self.emeka, f'{INVOICES}{inv.pk}/flow-details/', {
            'vendor_invoice_number': number, 'invoice_date': timezone.localdate().isoformat(),
            'amount': amount, 'vat_charged': vat, 'files': pdf(),
        }, 'multipart')

    def submitted(self):
        inv = self.started()
        self.fill(inv)
        response = self.post(self.emeka, f'{INVOICES}{inv.pk}/flow-submit/')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return inv

    # ── raising ──────────────────────────────────────────────────────────────

    def test_contractor_sees_the_job_to_invoice(self):
        rows = self.api(self.emeka).get(f'{INVOICES}to-invoice/').data
        self.assertEqual([r['completion_id'] for r in rows], [self.wcc.pk])
        self.assertEqual(self.api(self.frost_user).get(f'{INVOICES}to-invoice/').data, [])  # other vendor
        self.assertEqual([t['kind'] for t in self.api(self.emeka).get(MY_TASKS).data], ['invoice_to_raise'])

    def test_vat_is_optional_and_seven_and_a_half_percent(self):
        inv = self.started()
        response = self.fill(inv, vat=True)
        self.assertEqual(response.data['details']['vat'], '9000.00')
        self.assertEqual(response.data['details']['total'], '129000.00')
        response = self.fill(inv, vat=False)
        self.assertEqual(response.data['details']['vat'], '0.00')
        self.assertEqual(response.data['details']['total'], '120000.00')

    def test_amount_cannot_exceed_the_work_order(self):
        inv = self.started()
        self.fill(inv, amount='125000')
        response = self.post(self.emeka, f'{INVOICES}{inv.pk}/flow-submit/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('cannot be more than the Work Order amount', response.data['error'])

    def test_job_is_invoiced_once(self):
        self.started()
        response = self.post(self.emeka, f'{INVOICES}flow-start/', {'completion': self.wcc.pk})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.api(self.emeka).get(f'{INVOICES}to-invoice/').data, [])

    def test_other_vendor_cannot_invoice_the_job(self):
        response = self.post(self.frost_user, f'{INVOICES}flow-start/', {'completion': self.wcc.pk})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_old_create_refuses_five_stage_jobs(self):
        response = self.api(self.seun).post(INVOICES, {'work_completion': self.wcc.pk}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('five-stage', response.data['error'])

    # ── AP entering for a vendor without a login ─────────────────────────────

    def test_ap_enters_for_vendor_without_login_but_cannot_check_it(self):
        self.emeka.is_active = False
        self.emeka.save()
        self.assertEqual([r['completion_id'] for r in self.api(self.seun).get(f'{INVOICES}to-invoice/').data], [self.wcc.pk])
        inv = self.started(self.seun)
        self.assertTrue(inv.entered_for_vendor)
        self.fill(inv, user=self.seun)
        self.post(self.seun, f'{INVOICES}{inv.pk}/flow-submit/')
        response = self.post(self.seun, f'{INVOICES}{inv.pk}/flow-review/', {'signature': 'Seun Test'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)  # cannot check your own entry
        response = self.post(self.tola, f'{INVOICES}{inv.pk}/flow-review/', {'signature': 'Tola Test'})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_ap_does_not_enter_for_vendors_who_have_a_login(self):
        self.assertEqual(self.api(self.seun).get(f'{INVOICES}to-invoice/').data, [])

    # ── checking and approving ───────────────────────────────────────────────

    def test_three_way_match_all_pass(self):
        inv = self.submitted()
        data = self.api(self.seun).get(f'{INVOICES}{inv.pk}/flow/').data
        self.assertTrue(all(row['ok'] for row in data['match']), data['match'])
        self.assertEqual(data['my_actions'], ['review', 'return'])
        self.assertTrue(Notification.objects.filter(recipient=self.seun).exists())

    def test_contractor_does_not_see_the_internal_match(self):
        inv = self.submitted()
        self.assertEqual(self.api(self.emeka).get(f'{INVOICES}{inv.pk}/flow/').data['match'], [])

    def test_check_then_approve(self):
        inv = self.submitted()
        response = self.post(self.seun, f'{INVOICES}{inv.pk}/flow-review/', {'signature': 'Seun Test'})
        self.assertEqual(response.data['status'], 'Awaiting Approval')
        response = self.post(self.adaeze, f'{INVOICES}{inv.pk}/flow-approve/', {'signature': 'Adaeze Test'})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['status'], 'Approved')
        self.assertTrue(Notification.objects.filter(recipient=self.emeka, title__startswith='Invoice approved').exists())

    def test_return_then_resubmit(self):
        inv = self.submitted()
        response = self.post(self.seun, f'{INVOICES}{inv.pk}/flow-return/', {'reason': 'Wrong invoice date'})
        self.assertEqual(response.data['status'], 'Returned')
        self.fill(inv)
        response = self.post(self.emeka, f'{INVOICES}{inv.pk}/flow-submit/')
        self.assertEqual(response.data['status'], 'Awaiting Review')
        self.assertEqual([a.action for a in history(inv)], ['raised', 'sent_back', 'resubmitted'])

    def test_head_of_finance_can_return_too(self):
        inv = self.submitted()
        self.post(self.seun, f'{INVOICES}{inv.pk}/flow-review/', {'signature': 'Seun Test'})
        response = self.post(self.adaeze, f'{INVOICES}{inv.pk}/flow-return/', {'reason': 'Query on VAT'})
        self.assertEqual(response.data['status'], 'Returned')

    def test_only_the_named_head_of_finance_approves(self):
        inv = self.submitted()
        self.post(self.seun, f'{INVOICES}{inv.pk}/flow-review/', {'signature': 'Seun Test'})
        deputy = make_user('deputy@example.com', 'HEAD OF FINANCE & TREASURY', 'Deputy')
        response = self.post(deputy, f'{INVOICES}{inv.pk}/flow-approve/', {'signature': 'Deputy Test'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_legacy_approve_is_refused(self):
        inv = self.submitted()
        response = self.api(self.adaeze).post(f'{INVOICES}{inv.pk}/approve-by-approver/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_contractor_lists_only_own_invoices(self):
        inv = self.submitted()
        listed = self.api(self.emeka).get(INVOICES).data
        results = listed['results'] if isinstance(listed, dict) else listed
        self.assertEqual([r['id'] for r in results], [inv.pk])
        listed = self.api(self.frost_user).get(INVOICES).data
        results = listed['results'] if isinstance(listed, dict) else listed
        self.assertEqual(results, [])
