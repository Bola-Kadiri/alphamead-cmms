"""
Approval Matrix: named signers (APPROVER and CLIENT per facility, HEAD OF FINANCE &
TREASURY company-wide), teams by role, the go-live check, and the one `eligible`
check every stage will use.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Client, Vendor
from facility.models import Facility
from work.models import ApprovalMatrix, CompanyApprovers
from work.models.approval_matrix import eligible

User = get_user_model()
MATRIX = '/work/api/approval-matrix/'
COMPANY = '/work/api/company-approvers/'


def make_user(email, roles, facilities=(), clients=()):
    user = User.objects.create_user(email=email, password='x', first_name=email.split('@')[0].title(), last_name='T')
    user.roles = roles
    user.is_active = True
    user.save()
    user.facility.set(facilities)
    user.clients.set(clients)
    return user


class ApprovalMatrixTests(TestCase):

    def setUp(self):
        self.nestle = Client.objects.create(name='NESTLE (H.O) NIG', type='Company', code='CLI-M1')
        self.other_client = Client.objects.create(name='Other Co', type='Company', code='CLI-M2')
        self.agbara = Facility.objects.create(name='Nestle Agbara', code='NA-01', client=self.nestle)
        self.lekki = Facility.objects.create(name='Lekki Estate', code='LE-01')

        self.admin = make_user('admin@example.com', 'SUPER ADMIN')
        # Teams
        self.tunde = make_user('tunde@example.com', 'REQUESTER', [self.agbara])
        self.kola = make_user('kola@example.com', 'REQUESTER', [self.agbara])
        self.bola = make_user('bola@example.com', 'PROCUREMENT AND STORE')
        self.kemi = make_user('kemi@example.com', 'CENTRAL OPERATION')
        self.seun = make_user('seun@example.com', 'AP OFFICER')
        self.ibrahim = make_user('ibrahim@example.com', 'REVIEWER')
        # Named signers
        self.femi = make_user('femi@example.com', 'APPROVER', [self.agbara])
        self.ngozi = make_user('ngozi@example.com', 'CLIENT', clients=[self.nestle])
        self.adaeze = make_user('adaeze@example.com', 'HEAD OF FINANCE & TREASURY')

        self.api = APIClient()
        self.api.force_authenticate(user=self.admin)

    def set_head_of_finance(self, user=None):
        return self.api.patch(COMPANY, {'head_of_finance': (user or self.adaeze).pk}, format='json')

    def name_agbara_signers(self, **overrides):
        data = {'approver': self.femi.pk, 'client_rep': self.ngozi.pk}
        data.update(overrides)
        return self.api.patch(f'{MATRIX}{self.agbara.pk}/', data, format='json')

    def go_live_agbara(self):
        self.set_head_of_finance()
        self.name_agbara_signers()
        return self.api.post(f'{MATRIX}{self.agbara.pk}/go-live/')

    # ── access ───────────────────────────────────────────────────────────────

    def test_only_super_admin(self):
        for user in (self.tunde, self.femi, self.adaeze):
            api = APIClient()
            api.force_authenticate(user=user)
            self.assertEqual(api.get(MATRIX).status_code, status.HTTP_403_FORBIDDEN, user.roles)
            self.assertEqual(api.patch(f'{MATRIX}{self.agbara.pk}/', {}, format='json').status_code,
                             status.HTTP_403_FORBIDDEN)

    # ── named signers ────────────────────────────────────────────────────────

    def test_name_signers_then_go_live(self):
        self.assertEqual(self.set_head_of_finance().status_code, status.HTTP_200_OK)
        response = self.name_agbara_signers()
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['problems'], [])
        self.assertEqual(response.data['slots']['approver']['id'], self.femi.pk)
        self.assertEqual(response.data['slots']['head_of_finance']['id'], self.adaeze.pk)

        response = self.api.post(f'{MATRIX}{self.agbara.pk}/go-live/')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        matrix = ApprovalMatrix.objects.get(facility=self.agbara)
        self.assertTrue(matrix.is_live)
        self.assertEqual(matrix.went_live_by, self.admin)
        self.assertIsNotNone(matrix.went_live_at)

    def test_only_signers_are_named(self):
        for model, expected in ((ApprovalMatrix, {'approver', 'client_rep'}), (CompanyApprovers, {'head_of_finance'})):
            people = {f.name for f in model._meta.get_fields()
                      if f.is_relation and f.related_model is User and f.name != 'went_live_by'}
            self.assertEqual(people, expected)

    def test_wrong_role_is_refused(self):
        response = self.name_agbara_signers(approver=self.tunde.pk)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('APPROVER', str(response.data['approver']))

    def test_signer_not_assigned_to_facility_is_refused(self):
        outsider = make_user('outsider@example.com', 'APPROVER', [self.lekki])
        response = self.name_agbara_signers(approver=outsider.pk)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('not assigned to Nestle Agbara', str(response.data['approver']))

    def test_client_rep_must_belong_to_facility_client(self):
        stranger = make_user('stranger@example.com', 'CLIENT', clients=[self.other_client])
        response = self.name_agbara_signers(client_rep=stranger.pk)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("this facility's client", str(response.data['client_rep']))

    def test_inactive_signer_is_refused(self):
        self.femi.is_active = False
        self.femi.save()
        response = self.name_agbara_signers()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('inactive', str(response.data['approver']))

    def test_head_of_finance_must_hold_the_role(self):
        response = self.set_head_of_finance(self.seun)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('HEAD OF FINANCE & TREASURY', str(response.data['head_of_finance']))

    # ── teams ────────────────────────────────────────────────────────────────

    def test_teams_are_counted_not_named(self):
        detail = self.api.get(f'{MATRIX}{self.agbara.pk}/').data
        self.assertEqual(detail['teams']['requester'], {'role': 'REQUESTER', 'scope': 'facility', 'people': 2})
        self.assertEqual(detail['teams']['ap_officer'], {'role': 'AP OFFICER', 'scope': 'company', 'people': 1})
        lekki = self.api.get(f'{MATRIX}{self.lekki.pk}/').data
        self.assertEqual(lekki['teams']['requester']['people'], 0)  # nobody assigned to Lekki

    def test_go_live_needs_every_team(self):
        self.set_head_of_finance()
        self.name_agbara_signers()
        self.seun.is_active = False
        self.seun.save()
        response = self.api.post(f'{MATRIX}{self.agbara.pk}/go-live/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('No active user holds the AP OFFICER role.', response.data['problems'])

    def test_go_live_needs_a_site_manager_at_the_facility(self):
        self.tunde.facility.set([self.lekki])
        self.kola.facility.set([self.lekki])
        self.set_head_of_finance()
        self.name_agbara_signers()
        response = self.api.post(f'{MATRIX}{self.agbara.pk}/go-live/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('No active user holds the REQUESTER role assigned to Nestle Agbara.', response.data['problems'])

    # ── go-live check ────────────────────────────────────────────────────────

    def test_go_live_blocked_while_signers_missing(self):
        response = self.api.post(f'{MATRIX}{self.agbara.pk}/go-live/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(response.data['problems']), 3)  # approver, client rep, head of finance
        self.assertFalse(ApprovalMatrix.objects.get(facility=self.agbara).is_live)

    def test_facility_without_client_goes_live_without_a_client_rep(self):
        self.set_head_of_finance()
        self.femi.facility.add(self.lekki)
        make_user('ade@example.com', 'REQUESTER', [self.lekki])
        self.api.patch(f'{MATRIX}{self.lekki.pk}/', {'approver': self.femi.pk}, format='json')
        response = self.api.post(f'{MATRIX}{self.lekki.pk}/go-live/')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(ApprovalMatrix.objects.get(facility=self.lekki).is_live)

    def test_live_facility_cannot_lose_a_signer(self):
        self.go_live_agbara()
        response = self.name_agbara_signers(approver=None)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ApprovalMatrix.objects.get(facility=self.agbara).approver, self.femi)

        response = self.api.patch(COMPANY, {'head_of_finance': None}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(CompanyApprovers.current().head_of_finance, self.adaeze)

    def test_live_facility_can_replace_a_signer(self):
        self.go_live_agbara()
        ada = make_user('ada@example.com', 'APPROVER', [self.agbara])
        response = self.name_agbara_signers(approver=ada.pk)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(response.data['is_live'])

    def test_switch_off_then_change(self):
        self.go_live_agbara()
        self.assertEqual(self.api.post(f'{MATRIX}{self.agbara.pk}/switch-off/').status_code, status.HTTP_200_OK)
        response = self.name_agbara_signers(approver=None)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_live'])

    def test_deactivated_signer_shows_as_problem(self):
        self.go_live_agbara()
        self.adaeze.is_active = False
        self.adaeze.save()
        response = self.api.get(f'{MATRIX}{self.agbara.pk}/')
        self.assertTrue(any('inactive' in p for p in response.data['problems']))

    # ── overview ─────────────────────────────────────────────────────────────

    def test_list_shows_every_facility_without_creating_rows(self):
        response = self.api.get(MATRIX)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual({row['facility']['name'] for row in response.data}, {'Nestle Agbara', 'Lekki Estate'})
        self.assertTrue(all(not row['ready'] for row in response.data))
        self.assertEqual(ApprovalMatrix.objects.count(), 0)

    def test_candidates_are_only_for_named_signers(self):
        make_user('outsider@example.com', 'APPROVER', [self.lekki])
        response = self.api.get(f'{MATRIX}{self.agbara.pk}/candidates/')
        self.assertEqual(set(response.data), {'approver', 'client_rep', 'head_of_finance'})
        self.assertEqual([p['id'] for p in response.data['approver']], [self.femi.pk])
        self.assertEqual([p['id'] for p in response.data['client_rep']], [self.ngozi.pk])
        self.assertEqual([p['id'] for p in response.data['head_of_finance']], [self.adaeze.pk])

    def test_chain_follows_the_workflow_table(self):
        response = self.api.get(f'{MATRIX}{self.agbara.pk}/')
        chain = {row['stage']: row for row in response.data['chain']}
        steps = lambda stage: (chain[stage]['raises'], chain[stage]['reviews'], chain[stage]['approves'])
        self.assertEqual(steps('Work Request'), ('requester', 'approver', 'client_rep'))
        self.assertEqual(steps('Work Order'), ('procurement', 'approver', 'client_rep'))
        self.assertEqual(steps('Completion (WCC)'), ('requester', 'central_operation', 'approver'))
        self.assertEqual(steps('Vendor Invoice'), ('contractor', 'ap_officer', 'head_of_finance'))
        self.assertEqual(steps('Payment'), ('ap_officer', 'reviewer', 'head_of_finance'))
        # Preparing and checking is team work; signing off is named.
        self.assertEqual(chain['Payment']['kinds'], {'raises': 'team', 'reviews': 'team', 'approves': 'named'})
        self.assertEqual(chain['Work Request']['kinds'], {'raises': 'team', 'reviews': 'named', 'approves': 'named'})


class EligibleTests(TestCase):
    """The one check every stage uses before anyone acts."""

    def setUp(self):
        self.nestle = Client.objects.create(name='NESTLE (H.O) NIG', type='Company', code='CLI-E1')
        self.agbara = Facility.objects.create(name='Nestle Agbara', code='NA-01', client=self.nestle)
        self.lekki = Facility.objects.create(name='Lekki Estate', code='LE-01')
        self.cool_air = Vendor.objects.create(name='Cool Air Ltd', type='Company', currency='NGN')
        self.other_vendor = Vendor.objects.create(name='Frost Tech', type='Company', currency='NGN')

        self.kola = make_user('kola@example.com', 'REQUESTER', [self.agbara])
        self.seun = make_user('seun@example.com', 'AP OFFICER')
        self.tola = make_user('tola@example.com', 'AP OFFICER')
        self.femi = make_user('femi@example.com', 'APPROVER', [self.agbara])
        self.ada = make_user('ada@example.com', 'APPROVER', [self.agbara])
        self.ngozi = make_user('ngozi@example.com', 'CLIENT', clients=[self.nestle])
        self.adaeze = make_user('adaeze@example.com', 'HEAD OF FINANCE & TREASURY')
        self.deputy = make_user('deputy@example.com', 'HEAD OF FINANCE & TREASURY')
        self.contractor = make_user('emeka@coolair.example', 'CONTRACTOR')
        self.contractor.vendor = self.cool_air
        self.contractor.save()

        ApprovalMatrix.objects.create(facility=self.agbara, approver=self.femi, client_rep=self.ngozi)
        company = CompanyApprovers.current()
        company.head_of_finance = self.adaeze
        company.save()

    def test_team_step_anyone_with_the_role(self):
        self.assertTrue(eligible(self.seun, 'ap_officer', self.agbara))
        self.assertTrue(eligible(self.tola, 'ap_officer', self.lekki))  # company-wide team
        self.assertFalse(eligible(self.kola, 'ap_officer', self.agbara))

    def test_facility_team_needs_the_facility(self):
        self.assertTrue(eligible(self.kola, 'requester', self.agbara))
        self.assertFalse(eligible(self.kola, 'requester', self.lekki))

    def test_named_step_only_the_named_person(self):
        self.assertTrue(eligible(self.femi, 'approver', self.agbara))
        self.assertFalse(eligible(self.ada, 'approver', self.agbara))  # same role, not named
        self.assertTrue(eligible(self.ngozi, 'client_rep', self.agbara))
        self.assertTrue(eligible(self.adaeze, 'head_of_finance', self.lekki))
        self.assertFalse(eligible(self.deputy, 'head_of_finance', self.agbara))

    def test_named_step_at_facility_without_matrix(self):
        self.assertFalse(eligible(self.femi, 'approver', self.lekki))

    def test_contractor_only_for_own_vendor(self):
        self.assertTrue(eligible(self.contractor, 'contractor', self.agbara, vendor=self.cool_air))
        self.assertFalse(eligible(self.contractor, 'contractor', self.agbara, vendor=self.other_vendor))

    def test_inactive_user_is_never_eligible(self):
        self.femi.is_active = False
        self.femi.save()
        self.assertFalse(eligible(self.femi, 'approver', self.agbara))
