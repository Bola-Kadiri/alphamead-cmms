"""
Action rules (who may act, no self-approval, reasons and signatures, only the client
ends a job, approval limits, stand-ins stamped, send-back alert) and stage time limits.
"""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from accounts.models import Client
from facility.models import Facility
from work.models import ApprovalMatrix, CompanyApprovers, Delegation, Notification, StageTimeLimit, WorkRequest
from work.models.action_log import history
from work.models.flow_rules import ActionRefused, perform_action
from work.models.time_limits import step_timing, time_limit_for

User = get_user_model()


def make_user(email, roles, first, facilities=(), clients=()):
    user = User.objects.create_user(email=email, password='x', first_name=first, last_name='Test')
    user.roles = roles
    user.is_active = True
    user.save()
    user.facility.set(facilities)
    user.clients.set(clients)
    return user


class ActionRuleTests(TestCase):

    def setUp(self):
        self.nestle = Client.objects.create(name='NESTLE (H.O) NIG', type='Company', code='CLI-R1')
        self.agbara = Facility.objects.create(name='Nestle Agbara', code='NA-01', client=self.nestle)
        self.admin = make_user('admin@example.com', 'SUPER ADMIN', 'Sys')
        self.tunde = make_user('tunde@example.com', 'REQUESTER', 'Tunde', [self.agbara])
        self.femi = make_user('femi@example.com', 'APPROVER', 'Femi', [self.agbara])
        self.ada = make_user('ada@example.com', 'APPROVER', 'Ada', [self.agbara])
        self.ngozi = make_user('ngozi@example.com', 'CLIENT', 'Ngozi', clients=[self.nestle])
        self.adaeze = make_user('adaeze@example.com', 'HEAD OF FINANCE & TREASURY', 'Adaeze')
        ApprovalMatrix.objects.create(facility=self.agbara, approver=self.femi, client_rep=self.ngozi)
        company = CompanyApprovers.current()
        company.head_of_finance = self.adaeze
        company.save()
        self.wr = WorkRequest.objects.create(type='Work', requester=self.tunde, owner=self.tunde,
                                             facility=self.agbara, description='Reception AC not cooling')

    def act(self, slot, action, user, **kwargs):
        return perform_action(self.wr, 'work_request', slot, action, user, facility=self.agbara, **kwargs)

    def raise_it(self):
        return self.act('requester', 'raised', self.tunde)

    # 1. who may act
    def test_wrong_person_is_refused(self):
        self.raise_it()
        with self.assertRaisesMessage(ActionRefused, 'not the person for this step'):
            self.act('approver', 'reviewed', self.ada, signature='Ada Test')

    def test_named_signer_reviews(self):
        self.raise_it()
        stamp = self.act('approver', 'reviewed', self.femi, signature='Femi Test')
        self.assertEqual(stamp.actor, self.femi)
        self.assertIsNone(stamp.on_behalf_of)

    # 2. no self-approval
    def test_cannot_decide_on_own_work(self):
        self.raise_it()
        self.femi.roles = 'REQUESTER'
        self.femi.save()
        self.act('requester', 'raised', self.femi)  # Femi raises too (as a Site Manager)…
        self.femi.roles = 'APPROVER'
        self.femi.save()
        with self.assertRaisesMessage(ActionRefused, 'work you raised or reviewed'):
            self.act('approver', 'reviewed', self.femi, signature='Femi Test')  # …so cannot review it

    # 3. reasons and signatures
    def test_send_back_needs_a_reason(self):
        self.raise_it()
        with self.assertRaisesMessage(ActionRefused, 'Give a reason'):
            self.act('approver', 'sent_back', self.femi, reason='  ')

    def test_review_needs_own_signature(self):
        self.raise_it()
        with self.assertRaisesMessage(ActionRefused, 'Type your full name'):
            self.act('approver', 'reviewed', self.femi)
        with self.assertRaisesMessage(ActionRefused, 'your own full name'):
            self.act('approver', 'reviewed', self.femi, signature='Ada Test')
        stamp = self.act('approver', 'reviewed', self.femi, signature='  femi   TEST ')
        self.assertEqual(stamp.signature, 'femi   TEST')

    # 4. only the client ends a job
    def test_internal_checker_cannot_reject(self):
        self.raise_it()
        with self.assertRaisesMessage(ActionRefused, 'Only the client can reject'):
            self.act('approver', 'rejected', self.femi, reason='Not needed')

    def test_client_can_reject_with_reason(self):
        self.raise_it()
        self.act('approver', 'reviewed', self.femi, signature='Femi Test')
        stamp = self.act('client_rep', 'rejected', self.ngozi, reason='Not in budget')
        self.assertEqual(stamp.action, 'rejected')
        self.assertEqual(stamp.reason, 'Not in budget')

    # 5. approval limit
    def test_approval_limit(self):
        self.femi.approval_limit = Decimal('100000.00')
        self.femi.save()
        self.raise_it()
        with self.assertRaisesMessage(ActionRefused, 'above your approval limit'):
            self.act('approver', 'approved', self.femi, signature='Femi Test', amount=Decimal('150000'))
        self.act('approver', 'approved', self.femi, signature='Femi Test', amount=Decimal('90000'))

    # stand-ins
    def test_stand_in_is_stamped_on_behalf_of(self):
        now = timezone.now()
        Delegation.objects.create(person=self.femi, stand_in=self.ada, reason='Leave',
                                  starts_at=now - timedelta(hours=1), ends_at=now + timedelta(days=1))
        self.raise_it()
        stamp = self.act('approver', 'reviewed', self.ada, signature='Ada Test')
        self.assertEqual(stamp.actor, self.ada)
        self.assertEqual(stamp.on_behalf_of, self.femi)

    # send-back alert
    def test_super_admin_alerted_after_three_send_backs(self):
        self.raise_it()
        for round_number in range(3):
            self.act('approver', 'sent_back', self.femi, reason=f'Fix {round_number}')
            self.act('requester', 'resubmitted', self.tunde)
            if round_number < 2:
                self.assertEqual(Notification.objects.filter(recipient=self.admin).count(), 0)
        alert = Notification.objects.get(recipient=self.admin)
        self.assertIn('sent back 3 times', alert.message)
        self.assertEqual([a.action for a in history(self.wr)][:3], ['raised', 'sent_back', 'resubmitted'])

    def test_refused_action_is_not_stamped(self):
        self.raise_it()
        with self.assertRaises(ActionRefused):
            self.act('approver', 'reviewed', self.ada, signature='Ada Test')
        self.assertEqual(history(self.wr).count(), 1)


class StageTimeLimitTests(TestCase):

    def setUp(self):
        self.nestle = Client.objects.create(name='NESTLE (H.O) NIG', type='Company', code='CLI-T1')
        self.other = Client.objects.create(name='Other Co', type='Company', code='CLI-T2')

    def test_built_in_defaults(self):
        self.assertEqual(time_limit_for('work_request'), (24, 75))
        self.assertEqual(time_limit_for('work_order'), (48, 75))
        self.assertEqual(time_limit_for('wcc'), (72, 75))
        self.assertEqual(time_limit_for('vendor_invoice'), (48, 75))
        self.assertEqual(time_limit_for('payment'), (72, 75))

    def test_company_default_then_client_override(self):
        StageTimeLimit.objects.create(stage='work_request', hours=36, reminder_percent=80)
        StageTimeLimit.objects.create(client=self.nestle, stage='work_request', hours=12)
        self.assertEqual(time_limit_for('work_request'), (36, 80))
        self.assertEqual(time_limit_for('work_request', self.other), (36, 80))
        self.assertEqual(time_limit_for('work_request', self.nestle), (12, 75))

    def test_on_time_reminder_late(self):
        start = timezone.now()
        timing = lambda hours: step_timing('work_request', start, now=start + timedelta(hours=hours))['state']
        self.assertEqual(timing(10), 'on_time')
        self.assertEqual(timing(18), 'reminder')   # 75% of 24 h
        self.assertEqual(timing(24), 'late')
