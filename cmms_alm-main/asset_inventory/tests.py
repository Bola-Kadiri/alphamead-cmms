from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from asset_inventory.models import AssetCategory, AssetSubCategory
from work.models import WorkOrder

User = get_user_model()
URL = '/asset_inventory/api/asset-subcategories/bulk-import/'
HEADER = 'category,category_code,category_type,is_known_cost,subcategory,subcategory_code,subcategory_type,active\n'


def make_user(email, roles):
    user = User.objects.create_user(email=email, password='x', first_name='T', last_name='U')
    user.roles = roles
    user.is_active = True
    user.save()
    return user


def csv_file(*rows):
    return SimpleUploadedFile('categories.csv', (HEADER + '\n'.join(rows) + '\n').encode('utf-8'), content_type='text/csv')


class CategoryBulkUploadTests(TestCase):
    """Super Admin bulk upload of categories → subcategories (e.g. PHCN/Power Payment → EKEDC)."""

    def setUp(self):
        self.client = APIClient()
        self.super_admin = make_user('super@example.com', 'SUPER ADMIN')
        self.client.force_authenticate(user=self.super_admin)
        self.water = AssetCategory.objects.create(type='Active', code='WTR', name='Water')

    def upload(self, *rows, dry_run=False):
        return self.client.post(URL, {'file': csv_file(*rows), 'dry_run': 'true' if dry_run else 'false'}, format='multipart')

    def test_only_super_admin_can_upload(self):
        self.client.force_authenticate(user=make_user('req@example.com', 'REQUESTER'))
        response = self.upload('PHCN/Power Payment,PHCN,Expense,yes,EKEDC,EKEDC,Expense,yes')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(AssetSubCategory.objects.exists())

    def test_preview_saves_nothing(self):
        response = self.upload('PHCN/Power Payment,PHCN,Expense,yes,EKEDC,EKEDC,Expense,yes', dry_run=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['saved'])
        self.assertEqual(response.data['counts'], {'created': 1})
        self.assertFalse(AssetCategory.objects.filter(code='PHCN').exists())

    def test_upload_creates_category_and_maps_subcategories(self):
        response = self.upload(
            'PHCN/Power Payment,PHCN,Expense,yes,EKEDC,EKEDC,Expense,yes',
            'PHCN/Power Payment,PHCN,Expense,yes,IKEDC,IKEDC,Expense,yes',
            'Water,WTR,,yes,Water Corporation bill,WATER-CORP,,yes',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(response.data['saved'])
        power = AssetCategory.objects.get(code='PHCN')
        self.assertTrue(power.is_known_cost)
        self.assertEqual(set(power.subcategories.values_list('name', flat=True)), {'EKEDC', 'IKEDC'})
        self.water.refresh_from_db()
        self.assertTrue(self.water.is_known_cost)            # existing category ticked
        self.assertEqual(self.water.name, 'Water')           # never renamed
        self.assertEqual(self.water.subcategories.get().name, 'Water Corporation bill')

    def test_one_bad_row_blocks_the_whole_file(self):
        response = self.upload(
            'PHCN/Power Payment,PHCN,Expense,yes,EKEDC,EKEDC,Expense,yes',
            'PHCN/Power Payment,PHCN,Expense,maybe,IKEDC,IKEDC,Expense,yes',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['errors'], 1)
        self.assertEqual(response.data['rows'][1]['row'], 3)
        self.assertFalse(AssetCategory.objects.filter(code='PHCN').exists())

    def test_category_used_by_jobs_cannot_be_ticked(self):
        requester = make_user('r@example.com', 'REQUESTER')
        WorkOrder.objects.create(type='Unplanned', requester=requester, category=self.water)
        response = self.upload('Water,WTR,,yes,Water Corporation bill,WATER-CORP,,yes')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('already used by 1 work orders', response.data['rows'][0]['message'])
        self.water.refresh_from_db()
        self.assertFalse(self.water.is_known_cost)

    def test_reuploading_same_file_adds_nothing(self):
        row = 'PHCN/Power Payment,PHCN,Expense,yes,EKEDC,EKEDC,Expense,yes'
        self.upload(row)
        response = self.upload(row)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['counts'], {'skipped': 1})
        self.assertEqual(AssetSubCategory.objects.count(), 1)

    def test_subcategory_code_under_another_category_is_rejected(self):
        AssetSubCategory.objects.create(code='EKEDC', name='EKEDC', type='Asset', asset_category=self.water)
        response = self.upload('PHCN/Power Payment,PHCN,Expense,yes,EKEDC,EKEDC,Expense,yes')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already used under 'Water'", response.data['rows'][0]['message'])

    def test_missing_columns_are_reported(self):
        bad = SimpleUploadedFile('x.csv', b'name,code\nA,B\n', content_type='text/csv')
        response = self.client.post(URL, {'file': bad, 'dry_run': 'true'}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('missing these columns', response.data['detail'])

    def test_template_download(self):
        response = self.client.get('/asset_inventory/api/asset-subcategories/bulk-import-template/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.content.decode().startswith('category,category_code'))


class CategoryPermissionTests(TestCase):
    """Categories and subcategories: everyone can view; only a Super Admin can change them."""

    def setUp(self):
        self.client = APIClient()
        self.category = AssetCategory.objects.create(type='Expense', code='PHCN', name='PHCN/Power Payment', is_known_cost=True)
        self.sub = AssetSubCategory.objects.create(code='EKEDC', name='EKEDC', type='Expense', asset_category=self.category)

    def test_other_roles_can_view_but_not_change(self):
        for role in ('REQUESTER', 'ADMIN', 'APPROVER', 'HEAD OF FINANCE & TREASURY'):
            self.client.force_authenticate(user=make_user(f'{role.replace(" ", "")}@example.com', role))
            self.assertEqual(self.client.get('/asset_inventory/api/asset-categories/').status_code, status.HTTP_200_OK)
            self.assertEqual(self.client.get('/asset_inventory/api/asset-subcategories/').status_code, status.HTTP_200_OK)
            self.assertEqual(self.client.patch(f'/asset_inventory/api/asset-categories/{self.category.pk}/',
                                               {'is_known_cost': False}, format='json').status_code, status.HTTP_403_FORBIDDEN)
            self.assertEqual(self.client.post('/asset_inventory/api/asset-subcategories/', {
                'code': 'X', 'name': 'X', 'type': 'Expense', 'asset_category': self.category.pk,
            }, format='json').status_code, status.HTTP_403_FORBIDDEN)
            self.assertEqual(self.client.delete(f'/asset_inventory/api/asset-subcategories/{self.sub.pk}/').status_code,
                             status.HTTP_403_FORBIDDEN)
        self.category.refresh_from_db()
        self.assertTrue(self.category.is_known_cost)
        self.assertTrue(AssetSubCategory.objects.filter(pk=self.sub.pk).exists())

    def test_super_admin_can_change(self):
        self.client.force_authenticate(user=make_user('super@example.com', 'SUPER ADMIN'))
        response = self.client.patch(f'/asset_inventory/api/asset-categories/{self.category.pk}/', {'name': 'Power Bills'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        response = self.client.delete(f'/asset_inventory/api/asset-subcategories/{self.sub.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_anonymous_cannot_view(self):
        self.assertIn(self.client.get('/asset_inventory/api/asset-categories/').status_code,
                      (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))


class AdminBulkUploadTests(TestCase):
    """Django admin: Asset sub categorys → Bulk upload (Super Admin only, preview then confirm)."""

    URL = '/admin/asset_inventory/assetsubcategory/bulk-upload/'
    ROW = 'PHCN/Power Payment,PHCN,Expense,yes,EKEDC,EKEDC,Expense,yes'

    def setUp(self):
        self.super_admin = make_user('super-admin@example.com', 'SUPER ADMIN')
        self.super_admin.is_staff = True
        self.super_admin.is_superuser = True
        self.super_admin.save()
        self.client.force_login(self.super_admin)

    def preview(self, *rows):
        return self.client.post(self.URL, {'action': 'preview', 'csv_file': csv_file(*rows)})

    def test_button_shown_on_subcategory_list(self):
        response = self.client.get('/admin/asset_inventory/assetsubcategory/')
        self.assertContains(response, 'bulk-upload/')

    def test_preview_saves_nothing_then_confirm_saves(self):
        response = self.preview(self.ROW)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Confirm upload')
        self.assertFalse(AssetSubCategory.objects.exists())

        response = self.client.post(self.URL, {'action': 'confirm'})
        self.assertRedirects(response, '/admin/asset_inventory/assetsubcategory/')
        self.assertTrue(AssetCategory.objects.get(code='PHCN').is_known_cost)
        self.assertEqual(AssetSubCategory.objects.get(code='EKEDC').asset_category.code, 'PHCN')

    def test_errors_block_confirm(self):
        response = self.preview(self.ROW, 'PHCN/Power Payment,PHCN,Expense,maybe,IKEDC,IKEDC,Expense,yes')
        self.assertContains(response, 'Nothing has been saved')
        self.assertNotContains(response, 'Confirm upload')
        response = self.client.post(self.URL, {'action': 'confirm'})
        self.assertFalse(AssetSubCategory.objects.exists())

    def test_confirm_without_preview_does_nothing(self):
        response = self.client.post(self.URL, {'action': 'confirm'}, follow=True)
        self.assertContains(response, 'preview it again')
        self.assertFalse(AssetSubCategory.objects.exists())

    def test_only_super_admin(self):
        staff = make_user('staff-admin@example.com', 'ADMIN')
        staff.is_staff = True
        staff.save()
        self.client.force_login(staff)
        self.preview(self.ROW)
        self.client.post(self.URL, {'action': 'confirm'})
        self.assertFalse(AssetSubCategory.objects.exists())

    def test_template_download(self):
        response = self.client.get(self.URL + 'template/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.decode().startswith('category,category_code'))
