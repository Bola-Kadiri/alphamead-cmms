from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Vendor

User = get_user_model()
URL = '/accounts/api/vendors/bulk-import/'
HEADER = 'name,type,phone,email,account_name,bank,account_number,currency,status\n'


def make_user(email, roles):
    user = User.objects.create_user(email=email, password='x', first_name='T', last_name='U')
    user.roles = roles
    user.is_active = True
    user.save()
    return user


def csv_file(*rows):
    return SimpleUploadedFile('vendors.csv', (HEADER + '\n'.join(rows) + '\n').encode('utf-8'), content_type='text/csv')


class VendorBulkUploadTests(TestCase):
    """Super Admin bulk upload of vendors / payees (EKEDC, LAWMA…) with bank details."""

    EKEDC = 'EKEDC,Company,08000000000,billing@ekedc.example,EKEDC Collections,Zenith Bank,1012345678,NGN,Active'
    LAWMA = 'LAWMA,company,08000000001,,LAWMA Revenue,Access Bank,0698765432,ngn,'

    def setUp(self):
        self.client = APIClient()
        self.super_admin = make_user('super@example.com', 'SUPER ADMIN')
        self.client.force_authenticate(user=self.super_admin)

    def upload(self, *rows, dry_run=False):
        return self.client.post(URL, {'file': csv_file(*rows), 'dry_run': 'true' if dry_run else 'false'}, format='multipart')

    def test_only_super_admin_can_upload(self):
        self.client.force_authenticate(user=make_user('admin@example.com', 'ADMIN'))
        self.assertEqual(self.upload(self.EKEDC).status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Vendor.objects.exists())

    def test_preview_saves_nothing(self):
        response = self.upload(self.EKEDC, self.LAWMA, dry_run=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['counts'], {'created': 2})
        self.assertFalse(Vendor.objects.exists())

    def test_upload_creates_vendors_with_bank_details(self):
        response = self.upload(self.EKEDC, self.LAWMA)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        ekedc = Vendor.objects.get(name='EKEDC')
        self.assertEqual((ekedc.bank, ekedc.account_number, ekedc.currency), ('Zenith Bank', '1012345678', 'NGN'))
        lawma = Vendor.objects.get(name='LAWMA')
        self.assertEqual((lawma.type, lawma.currency, lawma.status), ('Company', 'NGN', 'Active'))  # normalised

    def test_bad_row_blocks_the_whole_file(self):
        bad = 'XYZ Ltd,Partnership,0800,,XYZ,GTB,1112223334,NGN,Active'
        response = self.upload(self.EKEDC, bad)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('type must be one of', response.data['rows'][1]['message'])
        self.assertFalse(Vendor.objects.exists())

    def test_account_number_used_by_another_vendor_is_rejected(self):
        self.upload(self.EKEDC)
        clash = 'Other Co,Company,0800,,Other,Zenith Bank,1012345678,NGN,Active'
        response = self.upload(clash)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already used by vendor 'EKEDC'", response.data['rows'][0]['message'])

    def test_reuploading_same_vendor_is_skipped(self):
        self.upload(self.EKEDC)
        response = self.upload(self.EKEDC)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['counts'], {'skipped': 1})
        self.assertEqual(Vendor.objects.count(), 1)

    def test_vendor_list_without_bank_details(self):
        """The real vendor list: spaced headers, currency label, no bank details, Excel-damaged phones."""
        content = (
            'Name,Type,Status,Phone,Email,Account name,Bank,Account number,Currency\n'
            'GAC Global Resources Ltd,Company,Active,,gacglobal6@gmail.com,,,,Nigerian Naira\n'
            'PROVAC ENGINEERING,Individual,Active,8068774221,enquiry@provacng.com,,,,Nigerian Naira\n'
            'Mundial Solutions Ltd,Company,Active,2.34802E+12,,,,,Nigerian Naira\n'
            'Musibau Oladepo,Individual,Inactive,,,,,,Nigerian Naira\n'
        )
        upload = SimpleUploadedFile('vendors.csv', content.encode('utf-8'), content_type='text/csv')
        response = self.client.post(URL, {'file': upload, 'dry_run': 'false'}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['counts'], {'created': 4})

        provac = Vendor.objects.get(name='PROVAC ENGINEERING')
        self.assertEqual(provac.phone, '08068774221')
        self.assertEqual(provac.currency, 'NGN')
        self.assertIsNone(provac.account_number)
        self.assertFalse(provac.has_bank_details)
        self.assertEqual(Vendor.objects.get(name='Mundial Solutions Ltd').phone, '')
        self.assertEqual(Vendor.objects.get(name='Musibau Oladepo').status, 'Inactive')

    def test_reupload_with_bank_details_fills_them_in(self):
        self.upload('LAWMA,Company,,,,,,NGN,Active')
        response = self.upload('LAWMA,Company,,,LAWMA Revenue,Access Bank,0698765432,NGN,Active')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['counts'], {'updated': 1})
        lawma = Vendor.objects.get()
        self.assertTrue(lawma.has_bank_details)
        self.assertEqual(lawma.account_number, '0698765432')

    def test_same_name_without_details_is_skipped(self):
        self.upload('LAWMA,Company,,,,,,NGN,Active')
        response = self.upload('lawma,Company,,,,,,NGN,Active')
        self.assertEqual(response.data['counts'], {'skipped': 1})
        self.assertEqual(Vendor.objects.count(), 1)

    def test_template_download(self):
        response = self.client.get('/accounts/api/vendors/bulk-import-template/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.content.decode().startswith('name,type,phone'))


class VendorPermissionTests(TestCase):
    """Vendors (bank details): everyone can view; only a Super Admin can change them."""

    def setUp(self):
        self.client = APIClient()
        self.vendor = Vendor.objects.create(
            name='EKEDC', type='Company', phone='0800', account_name='EKEDC', bank='Zenith Bank',
            account_number='1012345678', currency='NGN',
        )

    def test_other_roles_can_view_but_not_change(self):
        for role in ('REQUESTER', 'ADMIN', 'PROCUREMENT AND STORE', 'FINANCE'):
            self.client.force_authenticate(user=make_user(f'{role.replace(" ", "")}@example.com', role))
            self.assertEqual(self.client.get('/accounts/api/vendors/').status_code, status.HTTP_200_OK)
            self.assertEqual(self.client.patch(f'/accounts/api/vendors/{self.vendor.slug}/',
                                               {'account_number': '9999999999'}, format='json').status_code,
                             status.HTTP_403_FORBIDDEN)
            self.assertEqual(self.client.post('/accounts/api/vendors/', {
                'name': 'X', 'type': 'Company', 'phone': '1', 'account_name': 'X', 'bank': 'B',
                'account_number': '1', 'currency': 'NGN',
            }, format='json').status_code, status.HTTP_403_FORBIDDEN)
            self.assertEqual(self.client.delete(f'/accounts/api/vendors/{self.vendor.slug}/').status_code,
                             status.HTTP_403_FORBIDDEN)
        self.vendor.refresh_from_db()
        self.assertEqual(self.vendor.account_number, '1012345678')

    def test_super_admin_can_add_vendors_without_bank_details(self):
        self.client.force_authenticate(user=make_user('super3@example.com', 'SUPER ADMIN'))
        for name in ('Vendor A', 'Vendor B'):
            response = self.client.post('/accounts/api/vendors/', {
                'name': name, 'type': 'Company', 'phone': '', 'account_name': '', 'bank': '',
                'account_number': '', 'currency': 'NGN',
            }, format='json')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
            self.assertFalse(response.data['has_bank_details'])
        self.assertEqual(Vendor.objects.filter(account_number__isnull=True).count(), 2)

    def test_super_admin_can_change(self):
        self.client.force_authenticate(user=make_user('super2@example.com', 'SUPER ADMIN'))
        response = self.client.patch(f'/accounts/api/vendors/{self.vendor.slug}/', {'bank': 'GTBank'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(self.client.delete(f'/accounts/api/vendors/{self.vendor.slug}/').status_code,
                         status.HTTP_204_NO_CONTENT)
