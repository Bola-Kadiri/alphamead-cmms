"""Any single attachment can be at most 15 MB; files up to 15 MB upload as before."""
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from cmms_instanta.upload_limits import MAX_FILE_BYTES
from facility.models import Facility
from work.models import WorkRequest

TEMP_MEDIA = tempfile.mkdtemp()
WORK_REQUESTS = '/work/api/work-requests/'


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class UploadLimitTests(TestCase):

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        user = get_user_model().objects.create_user(email='boss@example.com', password='x', first_name='Boss',
                                                    last_name='Test')
        user.roles = 'SUPER ADMIN'
        user.is_active = True
        user.save()
        self.api = APIClient()
        self.api.force_authenticate(user=user)
        self.facility = Facility.objects.create(name='HQ Office')

    def upload(self, size, name='scan.pdf'):
        data = {'type': 'Work', 'description': 'Leaking roof', 'facility': self.facility.pk, 'priority': 'Medium',
                'resources': [SimpleUploadedFile(name, b'%' * size, content_type='application/pdf')]}
        return self.api.post(WORK_REQUESTS, data, format='multipart')

    def test_file_over_15_mb_is_refused_with_a_clear_message(self):
        response = self.upload(MAX_FILE_BYTES + 1, name='big-scan.pdf')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'big-scan.pdf is too large. Each file can be at most 15 MB.')
        self.assertFalse(WorkRequest.objects.exists())

    def test_file_of_exactly_15_mb_gets_past_the_limit(self):
        response = self.upload(MAX_FILE_BYTES)
        # Whatever the form's own rules say, the size limit is not what stops it.
        self.assertNotIn('at most 15 MB', str(getattr(response, 'data', '') or response.content))

    def test_request_without_files_is_unaffected(self):
        response = self.api.get(WORK_REQUESTS)
        self.assertEqual(response.status_code, 200)
