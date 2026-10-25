"""
Stage 3 · Work Completion Certificate in the five-stage flow: Site Managers (team)
raise it with evidence → Central Operations (team) verify on site → Category Manager
(named) approves. Send-backs return it to the Site Managers. Approval is blocked
without all three pieces of evidence. The original flow's actions refuse five-stage records.
"""
import shutil
import tempfile
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Client, Vendor
from asset_inventory.models import AssetCategory, AssetSubCategory
from facility.models import Facility
from work.models import (ApprovalMatrix, CompanyApprovers, Notification, PaymentRequisition, WorkOrder,
                         WorkOrderCompletion, WorkRequest)
from work.models import work_order_flow as stage2
from work.models import work_request_flow as stage1
from work.models.action_log import history

User = get_user_model()
WCC = '/work/api/work-order-completions/'
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


def upload(name='photo.jpg'):
    return SimpleUploadedFile(name, b'\xff\xd8\xff evidence', content_type='image/jpeg')


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class Stage3CompletionTests(TestCase):

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.nestle = Client.objects.create(name='NESTLE (H.O) NIG', type='Company', code='CLI-W3')
        self.agbara = Facility.objects.create(name='Nestle Agbara', code='NA-01', client=self.nestle)
        self.lekki = Facility.objects.create(name='Lekki Estate', code='LE-01')
        hvac = AssetCategory.objects.create(type='Asset', code='HVAC', name='HVAC')
        split = AssetSubCategory.objects.create(code='SPLIT', name='Split unit', type='Asset', asset_category=hvac)
        self.cool_air = Vendor.objects.create(name='Cool Air Ltd', type='Company', phone='0800', account_name='Cool Air',
                                              bank='Zenith Bank', account_number='2223334445', currency='NGN')

        self.tunde = make_user('tunde@example.com', 'REQUESTER', 'Tunde', [self.agbara])
        self.kola = make_user('kola@example.com', 'REQUESTER', 'Kola', [self.agbara])
        self.ade = make_user('ade@example.com', 'REQUESTER', 'Ade', [self.lekki])
        self.femi = make_user('femi@example.com', 'APPROVER', 'Femi', [self.agbara])
        self.ngozi = make_user('ngozi@example.com', 'CLIENT', 'Ngozi', clients=[self.nestle])
        self.bola = make_user('bola@example.com', 'PROCUREMENT AND STORE', 'Bola')
        self.kemi = make_user('kemi@example.com', 'CENTRAL OPERATION', 'Kemi')
        self.emeka = make_user('emeka@coolair.example', 'CONTRACTOR', 'Emeka', vendor=self.cool_air)
        self.admin = make_user('admin@example.com', 'SUPER ADMIN', 'Admin')
        make_user('seun@example.com', 'AP OFFICER', 'Seun')
        make_user('ibrahim@example.com', 'REVIEWER', 'Ibrahim')
        adaeze = make_user('adaeze@example.com', 'HEAD OF FINANCE & TREASURY', 'Adaeze')
        company = CompanyApprovers.current()
        company.head_of_finance = adaeze
        company.save()
        ApprovalMatrix.objects.create(facility=self.agbara, approver=self.femi, client_rep=self.ngozi).go_live(adaeze)

        # Stages 1 and 2 done: a client-approved Work Order.
        wr = WorkRequest.objects.create(type='Work', requester=self.tunde, owner=self.tunde, facility=self.agbara,
                                        category=hvac, subcategory=split, priority='High',
                                        description='Reception AC not cooling', flow=WorkRequest.FIVE_STAGE)
        stage1.raise_request(wr, self.tunde)
        stage1.review(wr, self.femi, 'Femi Test')
        stage1.client_approve(wr, self.ngozi, 'Ngozi Test')
        self.wo = stage2.start(wr, self.bola)
        stage2.save_pricing(self.wo, self.bola, vendor=self.cool_air, quotation_reference='CA-Q-1', po_number='PO-1',
                            expected_start_date='2026-10-28', files=[SimpleUploadedFile('q.pdf', b'%PDF', 'application/pdf')],
                            lines=[{'description': 'Compressor', 'quantity': 1, 'unit_cost_vendor': '120000',
                                    'unit_cost_client': '150000'}])
        stage2.submit(self.wo, self.bola)
        stage2.review(self.wo, self.femi, 'Femi Test')
        stage2.client_approve(self.wo, self.ngozi, 'Ngozi Test', True)

    # ── helpers ──────────────────────────────────────────────────────────────

    def api(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def post(self, user, path, data=None, fmt='json'):
        with self.captureOnCommitCallbacks(execute=True):
            return self.api(user).post(path, data or {}, format=fmt)

    def started(self, user=None):
        response = self.post(user or self.tunde, f'{WCC}flow-start/', {'work_order': self.wo.slug})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return WorkOrderCompletion.objects.get(pk=response.data['id'])

    def fill(self, wcc, user=None, evidence=('before_photo', 'after_photo', 'signed_checklist')):
        user = user or self.tunde
        now = timezone.now()
        response = self.post(user, f'{WCC}{wcc.pk}/flow-details/', {
            'started_at': (now - timedelta(hours=8)).isoformat(), 'finished_at': (now - timedelta(hours=2)).isoformat(),
            'technician': 'Emeka Obi', 'vendor_rating': 4, 'completion_notes': 'Compressor replaced, cooling at 18°C.',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        for kind in evidence:
            response = self.post(user, f'{WCC}{wcc.pk}/flow-evidence/', {'kind': kind, 'file': upload(f'{kind}.jpg')}, 'multipart')
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def submitted(self):
        wcc = self.started()
        self.fill(wcc)
        response = self.post(self.tunde, f'{WCC}{wcc.pk}/flow-submit/')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return wcc

    def verified(self):
        wcc = self.submitted()
        response = self.post(self.kemi, f'{WCC}{wcc.pk}/flow-verify/',
                             {'signature': 'Kemi Test', 'site_visit_date': timezone.localdate().isoformat()})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return wcc

    # ── raising ──────────────────────────────────────────────────────────────

    def test_site_manager_at_the_facility_raises(self):
        self.assertEqual([t['kind'] for t in self.api(self.kola).get(MY_TASKS).data], ['wcc_to_raise'])
        wcc = self.started(self.kola)  # any Site Manager at the facility
        self.assertEqual(wcc.flow, WorkOrderCompletion.FIVE_STAGE)
        self.assertEqual(wcc.technician, '')  # contractor had not accepted yet

    def test_site_manager_elsewhere_cannot_raise(self):
        response = self.post(self.ade, f'{WCC}flow-start/', {'work_order': self.wo.slug})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_one_active_certificate_per_work_order(self):
        self.started()
        response = self.post(self.kola, f'{WCC}flow-start/', {'work_order': self.wo.slug})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_submit_lists_everything_missing(self):
        wcc = self.started()
        response = self.post(self.tunde, f'{WCC}{wcc.pk}/flow-submit/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        for text in ('started', 'finished', 'technician', 'Rate the vendor', 'completion notes',
                     'before photo', 'after photo', 'signed inspection checklist'):
            self.assertIn(text, response.data['error'])

    def test_finish_must_be_after_start(self):
        wcc = self.started()
        now = timezone.now()
        self.post(self.tunde, f'{WCC}{wcc.pk}/flow-details/', {
            'started_at': (now - timedelta(hours=2)).isoformat(), 'finished_at': (now - timedelta(hours=3)).isoformat()})
        response = self.post(self.tunde, f'{WCC}{wcc.pk}/flow-submit/')
        self.assertIn('finish time must be after the start time', response.data['error'])

    def test_rating_is_one_to_five(self):
        wcc = self.started()
        response = self.post(self.tunde, f'{WCC}{wcc.pk}/flow-details/', {'vendor_rating': 7})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_new_evidence_replaces_old(self):
        wcc = self.started()
        self.post(self.tunde, f'{WCC}{wcc.pk}/flow-evidence/', {'kind': 'after_photo', 'file': upload('blurry.jpg')}, 'multipart')
        self.post(self.tunde, f'{WCC}{wcc.pk}/flow-evidence/', {'kind': 'after_photo', 'file': upload('clear.jpg')}, 'multipart')
        self.assertEqual(wcc.evidence.filter(kind='after_photo').count(), 1)
        self.assertIn('clear', wcc.evidence.get(kind='after_photo').file.name)

    # ── verification and approval ────────────────────────────────────────────

    def test_submit_goes_to_central_operations(self):
        wcc = self.submitted()
        wcc.refresh_from_db()
        self.assertEqual(wcc.approval_status, 'Awaiting Verification')
        self.assertTrue(Notification.objects.filter(recipient=self.kemi).exists())

    def test_verify_needs_a_site_visit_date(self):
        wcc = self.submitted()
        response = self.post(self.kemi, f'{WCC}{wcc.pk}/flow-verify/', {'signature': 'Kemi Test'})
        self.assertIn('site', response.data['error'])

    def test_verified_goes_to_the_category_manager(self):
        wcc = self.verified()
        data = self.api(self.femi).get(f'{WCC}{wcc.pk}/flow/').data
        self.assertEqual(data['status'], 'Awaiting Approval')
        self.assertEqual(data['my_actions'], ['approve', 'send_back'])
        self.assertEqual(data['details']['time_on_job_minutes'], 360)

    def test_approval_tells_the_contractor(self):
        wcc = self.verified()
        response = self.post(self.femi, f'{WCC}{wcc.pk}/flow-approve/', {'signature': 'Femi Test'})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['status'], 'Approved')
        self.assertTrue(Notification.objects.filter(recipient=self.emeka).exists())
        self.assertEqual(PaymentRequisition.objects.count(), 0)  # payment comes in Stage 5, not here

    def test_approval_blocked_without_evidence(self):
        wcc = self.verified()
        wcc.evidence.filter(kind='signed_checklist').delete()
        response = self.post(self.femi, f'{WCC}{wcc.pk}/flow-approve/', {'signature': 'Femi Test'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('without its evidence', response.data['error'])

    def test_send_back_from_approval_restarts_at_central_operations(self):
        wcc = self.verified()
        response = self.post(self.femi, f'{WCC}{wcc.pk}/flow-send-back/', {'reason': 'After photo is blurry'})
        self.assertEqual(response.data['status'], 'Sent Back')
        self.post(self.kola, f'{WCC}{wcc.pk}/flow-evidence/', {'kind': 'after_photo', 'file': upload('clear.jpg')}, 'multipart')
        response = self.post(self.kola, f'{WCC}{wcc.pk}/flow-submit/')
        self.assertEqual(response.data['status'], 'Awaiting Verification')
        self.assertEqual([a.action for a in history(wcc)], ['raised', 'reviewed', 'sent_back', 'resubmitted'])

    # ── who sees it ──────────────────────────────────────────────────────────

    def test_contractor_sees_only_approved_certificates(self):
        wcc = self.verified()
        listed = self.api(self.emeka).get(WCC).data
        results = listed['results'] if isinstance(listed, dict) else listed
        self.assertEqual(results, [])
        self.post(self.femi, f'{WCC}{wcc.pk}/flow-approve/', {'signature': 'Femi Test'})
        listed = self.api(self.emeka).get(WCC).data
        results = listed['results'] if isinstance(listed, dict) else listed
        self.assertEqual([r['id'] for r in results], [wcc.pk])

    # ── the original flow's actions refuse five-stage records ────────────────

    def test_legacy_wcc_approve_is_refused(self):
        wcc = self.verified()
        response = self.api(self.admin).post(f'{WCC}{wcc.pk}/approve-by-approver/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        wcc.refresh_from_db()
        self.assertEqual(wcc.approval_status, 'Awaiting Approval')
        self.assertEqual(PaymentRequisition.objects.count(), 0)

    def test_legacy_work_order_actions_are_refused(self):
        for path in ('approve-by-approver', 'set-status', 'create-payment-requisition'):
            response = self.api(self.admin).post(f'{WORK_ORDERS}{self.wo.slug}/{path}/', {'work_status': 'closed'}, format='json')
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, path)

    def test_generic_edit_is_refused(self):
        wcc = self.submitted()
        response = self.api(self.admin).patch(f'{WCC}{wcc.pk}/', {'technician': 'X'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
