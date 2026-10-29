"""
A facility with no client (e.g. Alpha Mead's own office) can use the five-stage flow:
there are no client steps, so the Approver's check fully approves the request and
approves the Work Order price. The rest of the flow is unchanged.
"""
import shutil
import tempfile
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import Vendor
from asset_inventory.models import AssetCategory, AssetSubCategory
from facility.models import Facility
from work.models import ApprovalMatrix, CompanyApprovers, WithholdingTaxRate, WorkRequest
from work.models import completion_flow as stage3
from work.models import invoice_flow as stage4
from work.models import payment_flow as stage5
from work.models import work_order_flow as stage2
from work.models import work_request_flow as stage1

User = get_user_model()
TEMP_MEDIA = tempfile.mkdtemp()


def make_user(email, roles, first, facilities=(), vendor=None):
    user = User.objects.create_user(email=email, password='x', first_name=first, last_name='Test')
    user.roles = roles
    user.is_active = True
    user.vendor = vendor
    user.save()
    user.facility.set(facilities)
    return user


def pdf(name='file.pdf'):
    return SimpleUploadedFile(name, b'%PDF-1.4 file', content_type='application/pdf')


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class NoClientFacilityTests(TestCase):

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.office = Facility.objects.create(name='Alpha Mead HQ', code='AM-HQ')  # no client
        hvac = AssetCategory.objects.create(type='Asset', code='HVAC', name='HVAC')
        self.split = AssetSubCategory.objects.create(code='SPLIT', name='Split unit', type='Asset', asset_category=hvac)
        self.hvac = hvac
        self.vendor = Vendor.objects.create(name='Cool Air Ltd', type='Company', phone='0800', account_name='Cool Air',
                                            bank='Zenith Bank', account_number='2223334445', currency='NGN')
        self.tunde = make_user('tunde@example.com', 'REQUESTER', 'Tunde', [self.office])
        self.femi = make_user('femi@example.com', 'APPROVER', 'Femi', [self.office])
        self.bola = make_user('bola@example.com', 'PROCUREMENT AND STORE', 'Bola')
        self.kemi = make_user('kemi@example.com', 'CENTRAL OPERATION', 'Kemi')
        self.emeka = make_user('emeka@coolair.example', 'CONTRACTOR', 'Emeka', vendor=self.vendor)
        self.seun = make_user('seun@example.com', 'AP OFFICER', 'Seun')
        self.ibrahim = make_user('ibrahim@example.com', 'REVIEWER', 'Ibrahim')
        self.adaeze = make_user('adaeze@example.com', 'HEAD OF FINANCE & TREASURY', 'Adaeze')
        company = CompanyApprovers.current()
        company.head_of_finance = self.adaeze
        company.save()
        matrix = ApprovalMatrix.objects.create(facility=self.office, approver=self.femi)
        self.assertEqual(matrix.problems(), [])
        matrix.go_live(self.adaeze)

    def approved_request(self):
        wr = WorkRequest.objects.create(type='Work', requester=self.tunde, owner=self.tunde, facility=self.office,
                                        category=self.hvac, subcategory=self.split, priority='High',
                                        description='Boardroom AC not cooling', flow=WorkRequest.FIVE_STAGE)
        stage1.raise_request(wr, self.tunde)
        stage1.review(wr, self.femi, 'Femi Test')
        wr.refresh_from_db()
        return wr

    def approved_work_order(self):
        wo = stage2.start(self.approved_request(), self.bola)
        stage2.save_pricing(wo, self.bola, vendor=self.vendor, quotation_reference='CA-Q-1', po_number='PO-1',
                            expected_start_date='2026-10-28', files=[pdf('q.pdf')],
                            lines=[{'description': 'Compressor', 'quantity': 1, 'unit_cost_vendor': '120000',
                                    'unit_cost_client': '150000'}])
        stage2.submit(wo, self.bola)
        stage2.review(wo, self.femi, 'Femi Test')
        wo.refresh_from_db()
        return wo

    def test_request_is_fully_approved_by_the_approver(self):
        wr = self.approved_request()
        self.assertEqual(wr.approval_status, 'Fully Approved')
        self.assertFalse(stage1.client_approves(wr))

    def test_approver_check_approves_the_price(self):
        wo = self.approved_work_order()
        self.assertEqual(wo.approval_status, 'Approved')
        self.assertTrue(wo.is_approved)
        self.assertFalse(stage2.client_signs(wo))

    def test_the_rest_of_the_flow_runs_and_the_trail_is_complete(self):
        wo = self.approved_work_order()
        wcc = stage3.start(wo, self.tunde)
        now = timezone.now()
        stage3.save_details(wcc, self.tunde, started_at=now - timedelta(hours=8), finished_at=now - timedelta(hours=2),
                            technician='Emeka Obi', vendor_rating=4, completion_notes='Done')
        for kind in stage3.REQUIRED_EVIDENCE:
            stage3.add_evidence(wcc, self.tunde, kind, SimpleUploadedFile(f'{kind}.jpg', b'img', 'image/jpeg'))
        stage3.submit(wcc, self.tunde)
        stage3.verify(wcc, self.kemi, 'Kemi Test', timezone.localdate())
        stage3.approve(wcc, self.femi, 'Femi Test')

        inv = stage4.start(wcc, self.emeka)
        stage4.save_details(inv, self.emeka, vendor_invoice_number='INV-CA-1', invoice_date=timezone.localdate(),
                            amount='120000', vat_charged=False, files=[pdf()])
        stage4.submit(inv, self.emeka)
        stage4.review(inv, self.seun, 'Seun Test')
        stage4.approve(inv, self.adaeze, 'Adaeze Test')

        voucher = stage5.start(inv, self.seun)
        stage5.save_details(voucher, self.seun, wht_rate=WithholdingTaxRate.objects.get(name='None').pk,
                            payment_method='bank_transfer')
        stage5.submit(voucher, self.seun)
        self.assertTrue(all(row['ok'] for row in stage5.trail(voucher)), stage5.trail(voucher))
        self.assertTrue(all(row['ok'] for row in stage5.checks(voucher)), stage5.checks(voucher))
        stage5.review(voucher, self.ibrahim, 'Ibrahim Test')
        voucher.refresh_from_db()
        self.assertEqual(voucher.status, 'Awaiting Approval')
