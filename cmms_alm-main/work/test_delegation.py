"""
Cover while away: a named signer's stand-in may act for them during the cover,
within its value limit; the rules stop self-cover, wrong roles, overlaps and passing on.
"""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Client
from facility.models import Facility
from work.models import ApprovalMatrix, CompanyApprovers, Delegation
from work.models.approval_matrix import acting_for, eligible

User = get_user_model()
DELEGATIONS = '/work/api/delegations/'


def make_user(email, roles, facilities=(), clients=()):
    user = User.objects.create_user(email=email, password='x', first_name=email.split('@')[0].title(), last_name='T')
    user.roles = roles
    user.is_active = True
    user.save()
    user.facility.set(facilities)
    user.clients.set(clients)
    return user


class CoverWhileAwayTests(TestCase):

    def setUp(self):
        self.nestle = Client.objects.create(name='NESTLE (H.O) NIG', type='Company', code='CLI-D1')
        self.agbara = Facility.objects.create(name='Nestle Agbara', code='NA-01', client=self.nestle)
        self.lekki = Facility.objects.create(name='Lekki Estate', code='LE-01')
        self.admin = make_user('admin@example.com', 'SUPER ADMIN')
        self.femi = make_user('femi@example.com', 'APPROVER', [self.agbara])
        self.ada = make_user('ada@example.com', 'APPROVER', [self.agbara])
        self.musa = make_user('musa@example.com', 'APPROVER', [self.lekki])
        self.ngozi = make_user('ngozi@example.com', 'CLIENT', clients=[self.nestle])
        self.adaeze = make_user('adaeze@example.com', 'HEAD OF FINANCE & TREASURY')
        self.tola = make_user('tola@example.com', 'HEAD OF FINANCE & TREASURY')
        self.seun = make_user('seun@example.com', 'AP OFFICER')

        ApprovalMatrix.objects.create(facility=self.agbara, approver=self.femi, client_rep=self.ngozi)
        company = CompanyApprovers.current()
        company.head_of_finance = self.adaeze
        company.save()

        self.now = timezone.now()

    def api_for(self, user):
        api = APIClient()
        api.force_authenticate(user=user)
        return api

    def cover(self, user, **data):
        payload = {'stand_in': self.ada.pk, 'starts_at': (self.now - timedelta(hours=1)).isoformat(),
                   'ends_at': (self.now + timedelta(days=5)).isoformat(), 'reason': 'Annual leave'}
        payload.update(data)
        return self.api_for(user).post(DELEGATIONS, payload, format='json')

    # ── arranging cover ──────────────────────────────────────────────────────

    def test_signer_arranges_own_cover(self):
        response = self.cover(self.femi)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['person']['id'], self.femi.pk)
        self.assertEqual(response.data['stand_in']['id'], self.ada.pk)
        self.assertEqual(response.data['status'], 'active')

    def test_stand_in_must_hold_the_same_role(self):
        response = self.cover(self.femi, stand_in=self.seun.pk)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('APPROVER', str(response.data['stand_in']))

    def test_no_cover_for_yourself(self):
        response = self.cover(self.femi, stand_in=self.femi.pk)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_end_must_be_after_start(self):
        response = self.cover(self.femi, ends_at=(self.now - timedelta(days=1)).isoformat())
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('ends_at', response.data)

    def test_only_signers_need_cover(self):
        response = self.cover(self.seun, stand_in=self.seun.pk)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_arrange_cover_for_someone_else(self):
        response = self.cover(self.ada, person=self.femi.pk, stand_in=self.musa.pk)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_super_admin_can_arrange_cover_for_anyone(self):
        response = self.cover(self.admin, person=self.femi.pk)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_one_cover_at_a_time(self):
        self.cover(self.femi)
        response = self.cover(self.femi, stand_in=self.musa.pk)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cover_cannot_be_passed_on(self):
        self.cover(self.femi)                      # Ada covers Femi
        response = self.cover(self.ada, stand_in=self.musa.pk)  # Ada tries to hand it on while covering
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_stand_in_who_is_away_is_refused(self):
        self.cover(self.ada, stand_in=self.musa.pk)  # Ada is away
        response = self.cover(self.femi)              # Femi asks Ada
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('away', str(response.data['stand_in']))

    # ── acting under cover ───────────────────────────────────────────────────

    def test_stand_in_acts_on_behalf_of_the_signer(self):
        self.assertFalse(eligible(self.ada, 'approver', self.agbara))
        self.cover(self.femi)
        allowed, on_behalf_of = acting_for(self.ada, 'approver', self.agbara)
        self.assertTrue(allowed)
        self.assertEqual(on_behalf_of, self.femi)
        self.assertTrue(eligible(self.femi, 'approver', self.agbara))  # Femi can still act himself

    def test_stand_in_must_be_allowed_at_the_facility(self):
        self.cover(self.femi, stand_in=self.musa.pk)  # Musa is assigned to Lekki only
        self.assertFalse(eligible(self.musa, 'approver', self.agbara))

    def test_value_limit(self):
        self.cover(self.adaeze, stand_in=self.tola.pk, value_limit='5000000.00')
        self.assertTrue(eligible(self.tola, 'head_of_finance', self.agbara, amount=Decimal('4999999')))
        self.assertFalse(eligible(self.tola, 'head_of_finance', self.agbara, amount=Decimal('5000001')))

    def test_cover_only_counts_between_its_dates(self):
        self.cover(self.femi, starts_at=(self.now + timedelta(days=2)).isoformat(),
                   ends_at=(self.now + timedelta(days=4)).isoformat())
        self.assertFalse(eligible(self.ada, 'approver', self.agbara))
        self.assertEqual(Delegation.objects.get().status, 'scheduled')

    def test_ending_early_stops_the_cover(self):
        cover_id = self.cover(self.femi).data['id']
        response = self.api_for(self.femi).post(f'{DELEGATIONS}{cover_id}/end/')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['status'], 'ended_early')
        self.assertFalse(eligible(self.ada, 'approver', self.agbara))

    def test_stand_in_cannot_end_the_cover(self):
        cover_id = self.cover(self.femi).data['id']
        response = self.api_for(self.ada).post(f'{DELEGATIONS}{cover_id}/end/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ── lists ────────────────────────────────────────────────────────────────

    def test_people_see_only_their_own_covers(self):
        self.cover(self.femi)
        self.assertEqual(len(self.api_for(self.femi).get(DELEGATIONS).data), 1)
        self.assertEqual(len(self.api_for(self.ada).get(DELEGATIONS).data), 1)   # as stand-in
        self.assertEqual(len(self.api_for(self.musa).get(DELEGATIONS).data), 0)
        self.assertEqual(len(self.api_for(self.admin).get(DELEGATIONS).data), 1)

    def test_stand_in_candidates_share_the_role(self):
        names = {p['id'] for p in self.api_for(self.femi).get(f'{DELEGATIONS}stand-ins/').data}
        self.assertEqual(names, {self.ada.pk, self.musa.pk})
