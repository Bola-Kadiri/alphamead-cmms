"""
Stage 1 · Work Request in the five-stage flow (facilities switched on in the
Approval Matrix): Site Managers raise → Category Manager reviews or sends back →
Client approves, or rejects and the job ends. Facilities not switched on are untouched.
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import Client
from asset_inventory.models import AssetCategory, AssetSubCategory
from facility.models import Facility
from work.models import ApprovalMatrix, CompanyApprovers, Delegation, Notification, WorkOrder, WorkRequest
from work.models.action_log import history

User = get_user_model()
WORK_REQUESTS = '/work/api/work-requests/'
MY_TASKS = '/work/api/my-tasks/'


def make_user(email, roles, first, facilities=(), clients=()):
    user = User.objects.create_user(email=email, password='x', first_name=first, last_name='Test')
    user.roles = roles
    user.is_active = True
    user.save()
    user.facility.set(facilities)
    user.clients.set(clients)
    return user


class Stage1WorkRequestTests(TestCase):

    def setUp(self):
        self.nestle = Client.objects.create(name='NESTLE (H.O) NIG', type='Company', code='CLI-S1')
        self.agbara = Facility.objects.create(name='Nestle Agbara', code='NA-01', client=self.nestle)
        self.lekki = Facility.objects.create(name='Lekki Estate', code='LE-01')
        self.hvac = AssetCategory.objects.create(type='Asset', code='HVAC', name='HVAC')
        self.split = AssetSubCategory.objects.create(code='SPLIT', name='Split unit', type='Asset', asset_category=self.hvac)

        self.tunde = make_user('tunde@example.com', 'REQUESTER', 'Tunde', [self.agbara, self.lekki])
        self.kola = make_user('kola@example.com', 'REQUESTER', 'Kola', [self.agbara])
        self.ade = make_user('ade@example.com', 'REQUESTER', 'Ade', [self.lekki])
        self.femi = make_user('femi@example.com', 'APPROVER', 'Femi', [self.agbara])
        self.ada = make_user('ada@example.com', 'APPROVER', 'Ada', [self.agbara])
        self.ngozi = make_user('ngozi@example.com', 'CLIENT', 'Ngozi', clients=[self.nestle])
        self.bola = make_user('bola@example.com', 'PROCUREMENT AND STORE', 'Bola')
        make_user('kemi@example.com', 'CENTRAL OPERATION', 'Kemi')
        make_user('seun@example.com', 'AP OFFICER', 'Seun')
        make_user('ibrahim@example.com', 'REVIEWER', 'Ibrahim')
        self.adaeze = make_user('adaeze@example.com', 'HEAD OF FINANCE & TREASURY', 'Adaeze')
        self.admin = make_user('admin@example.com', 'ADMIN', 'Admin')

        company = CompanyApprovers.current()
        company.head_of_finance = self.adaeze
        company.save()
        matrix = ApprovalMatrix.objects.create(facility=self.agbara, approver=self.femi, client_rep=self.ngozi)
        matrix.go_live(self.admin)

    # ── helpers ──────────────────────────────────────────────────────────────

    def api(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def raise_request(self, user=None, facility=None, **extra):
        data = {'type': 'Work', 'facility': (facility or self.agbara).pk, 'category': self.hvac.pk,
                'subcategory': self.split.pk, 'priority': 'High',
                'description': 'Reception AC not cooling since Monday.', **extra}
        with self.captureOnCommitCallbacks(execute=True):
            return self.api(user or self.tunde).post(WORK_REQUESTS, data, format='multipart')

    def act(self, user, slug, action, **data):
        with self.captureOnCommitCallbacks(execute=True):
            return self.api(user).post(f'{WORK_REQUESTS}{slug}/{action}/', data, format='json')

    def raised(self):
        response = self.raise_request()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return WorkRequest.objects.get(slug=response.data['slug'])

    def notified(self, user):
        return Notification.objects.filter(recipient=user).exists()

    # ── raising ──────────────────────────────────────────────────────────────

    def test_raise_routes_to_the_category_manager(self):
        wr = self.raised()
        self.assertEqual(wr.flow, WorkRequest.FIVE_STAGE)
        self.assertEqual(wr.approval_status, 'Awaiting Review')
        self.assertTrue(wr.is_locked)
        self.assertEqual([a.action for a in history(wr)], ['raised'])
        self.assertTrue(self.notified(self.femi))
        self.assertFalse(self.notified(self.bola))  # Procurement only after approval

    def test_routing_fields_from_the_form_are_ignored(self):
        response = self.raise_request(approver=self.ada.pk)
        wr = WorkRequest.objects.get(slug=response.data['slug'])
        self.assertIsNone(wr.approver)

    def test_only_site_managers_raise_on_live_facilities(self):
        response = self.raise_request(user=self.admin)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(WorkRequest.objects.count(), 0)

    def test_facility_not_switched_on_keeps_original_flow(self):
        response = self.raise_request(facility=self.lekki)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        wr = WorkRequest.objects.get(slug=response.data['slug'])
        self.assertEqual(wr.flow, WorkRequest.LEGACY)
        self.assertEqual(wr.approval_status, 'Pending Review')
        self.assertEqual(history(wr).count(), 0)

    # ── who sees it ──────────────────────────────────────────────────────────

    def test_site_manager_team_sees_facility_requests(self):
        wr = self.raised()
        slugs = lambda user: {r['slug'] for r in self.api(user).get(WORK_REQUESTS).data['results']}
        self.assertIn(wr.slug, slugs(self.kola))     # same facility
        self.assertNotIn(wr.slug, slugs(self.ade))   # other facility
        self.assertIn(wr.slug, slugs(self.femi))     # the facility's Category Manager

    # ── review / send back / resubmit ────────────────────────────────────────

    def test_review_sends_it_to_the_client(self):
        wr = self.raised()
        response = self.act(self.femi, wr.slug, 'flow-review', signature='Femi Test', note='Needs a vendor')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['status'], 'Awaiting Client')
        self.assertTrue(self.notified(self.ngozi))

    def test_only_the_named_category_manager_reviews(self):
        wr = self.raised()
        response = self.act(self.ada, wr.slug, 'flow-review', signature='Ada Test')
        self.assertIn(response.status_code, (status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND))
        wr.refresh_from_db()
        self.assertEqual(wr.approval_status, 'Awaiting Review')

    def test_send_back_then_any_site_manager_resubmits(self):
        wr = self.raised()
        response = self.act(self.femi, wr.slug, 'flow-send-back', reason='Wrong asset selected')
        self.assertEqual(response.data['status'], 'Sent Back')
        self.assertTrue(self.notified(self.kola))
        response = self.act(self.kola, wr.slug, 'flow-resubmit')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['status'], 'Awaiting Review')
        self.assertEqual([a.action for a in history(wr)], ['raised', 'sent_back', 'resubmitted'])

    def test_send_back_needs_a_reason(self):
        wr = self.raised()
        response = self.act(self.femi, wr.slug, 'flow-send-back', reason='')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('reason', response.data['error'])

    # ── client decision ──────────────────────────────────────────────────────

    def test_client_approves(self):
        wr = self.raised()
        self.act(self.femi, wr.slug, 'flow-review', signature='Femi Test')
        response = self.act(self.ngozi, wr.slug, 'flow-approve', signature='Ngozi Test')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        wr.refresh_from_db()
        self.assertEqual(wr.approval_status, 'Fully Approved')
        self.assertIsNotNone(wr.fully_approved_at)
        self.assertTrue(self.notified(self.bola))
        self.assertEqual(WorkOrder.objects.count(), 0)  # pricing happens in Stage 2

    def test_client_rejection_ends_the_job(self):
        wr = self.raised()
        self.act(self.femi, wr.slug, 'flow-review', signature='Femi Test')
        response = self.act(self.ngozi, wr.slug, 'flow-reject', reason='Not in this year’s budget')
        self.assertEqual(response.data['status'], 'Client Rejected')
        for user, action in ((self.ngozi, 'flow-approve'), (self.kola, 'flow-resubmit'), (self.femi, 'flow-review')):
            self.assertEqual(self.act(user, wr.slug, action, signature='x').status_code, status.HTTP_400_BAD_REQUEST)

    def test_raise_again_from_a_rejected_request(self):
        wr = self.raised()
        self.act(self.femi, wr.slug, 'flow-review', signature='Femi Test')
        self.act(self.ngozi, wr.slug, 'flow-reject', reason='Too early')
        response = self.raise_request(replaces=wr.pk)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        new = WorkRequest.objects.get(slug=response.data['slug'])
        self.assertEqual(new.replaces, wr)

    def test_cannot_raise_again_from_a_live_request(self):
        wr = self.raised()
        response = self.raise_request(replaces=wr.pk)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_price_only_client_skips_the_client_step(self):
        self.nestle.approves_work_requests = False
        self.nestle.save()
        wr = self.raised()
        response = self.act(self.femi, wr.slug, 'flow-review', signature='Femi Test')
        self.assertEqual(response.data['status'], 'Fully Approved')
        self.assertEqual([s['step'] for s in response.data['chain']], ['requester', 'approver'])

    # ── my tasks, stand-ins, screen data ─────────────────────────────────────

    def test_my_tasks_follow_the_request(self):
        wr = self.raised()
        numbers = lambda user: [t['number'] for t in self.api(user).get(MY_TASKS).data]
        self.assertEqual(numbers(self.femi), [wr.work_request_number])
        self.assertEqual(numbers(self.ngozi), [])
        self.act(self.femi, wr.slug, 'flow-review', signature='Femi Test')
        self.assertEqual(numbers(self.femi), [])
        self.assertEqual(numbers(self.ngozi), [wr.work_request_number])

    def test_stand_in_reviews_on_behalf_of_the_category_manager(self):
        now = timezone.now()
        Delegation.objects.create(person=self.femi, stand_in=self.ada, reason='Leave',
                                  starts_at=now - timedelta(hours=1), ends_at=now + timedelta(days=2))
        wr = self.raised()
        tasks = self.api(self.ada).get(MY_TASKS).data
        self.assertEqual(tasks[0]['on_behalf_of'], 'Femi Test')
        response = self.act(self.ada, wr.slug, 'flow-review', signature='Ada Test')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['history'][-1]['on_behalf_of'], 'Femi Test')

    def test_flow_screen_data(self):
        wr = self.raised()
        data = self.api(self.femi).get(f'{WORK_REQUESTS}{wr.slug}/flow/').data
        self.assertEqual(data['my_actions'], ['review', 'send_back'])
        self.assertEqual(data['chain'][1]['person'], 'Femi Test')
        self.assertEqual(data['timing']['state'], 'on_time')
        self.assertEqual(self.api(self.tunde).get(f'{WORK_REQUESTS}{wr.slug}/flow/').data['my_actions'], [])

    def test_client_acts_through_their_real_login(self):
        wr = self.raised()
        self.act(self.femi, wr.slug, 'flow-review', signature='Femi Test')
        client_api = APIClient()
        client_api.credentials(HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(self.ngozi).access_token}')
        self.assertEqual(client_api.get(MY_TASKS).status_code, status.HTTP_200_OK)
        with self.captureOnCommitCallbacks(execute=True):
            response = client_api.post(f'{WORK_REQUESTS}{wr.slug}/flow-approve/', {'signature': 'Ngozi Test'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_form_preview_shows_who_will_handle_it(self):
        data = self.api(self.tunde).get(f'{WORK_REQUESTS}flow-preview/', {'facility': self.agbara.pk}).data
        self.assertTrue(data['live'])
        self.assertEqual([s['step'] for s in data['chain']], ['requester', 'approver', 'client_rep'])
        self.assertEqual(data['chain'][2]['person'], 'Ngozi Test')
        self.assertFalse(self.api(self.tunde).get(f'{WORK_REQUESTS}flow-preview/', {'facility': self.lekki.pk}).data['live'])
