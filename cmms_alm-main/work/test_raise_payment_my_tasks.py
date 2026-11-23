"""
Raise Payment bills in My Tasks: each bill shows for whoever it is waiting on (Procurement & Store,
the Requester after a return, the Approver or their stand-in, the Reviewer, the final approver),
and moves to the next person's list when acted on.
"""
from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone

from work.models import Delegation
from work import test_raise_payment_route as route
from work.test_raise_payment_route import LARGE, SMALL, TEMP_MEDIA, make_user

# Borrowed through the module, so the route tests are not collected (and run) a second time here.
Route = route.RaisePaymentApprovalRouteTests
MY_TASKS = '/work/api/my-tasks/'


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class RaisePaymentMyTasksTests(TestCase):
    AUTO = Route.AUTO
    setUp = Route.setUp
    post_bill = Route.post_bill
    raise_bill = Route.raise_bill
    act = Route.act
    procure = Route.procure
    status_of = Route.status_of

    def tasks(self, user):
        self.client.force_authenticate(user=user)
        return [(t['number'], t['step'], t['what']) for t in self.client.get(MY_TASKS).data if t['kind'] == 'raise_payment']

    def steps(self, user):
        return [step for _, step, _ in self.tasks(user)]

    def test_bill_moves_through_everyones_my_tasks(self):
        slug = self.raise_bill(cost=LARGE)
        self.assertEqual(self.steps(self.procurement), ['procurement'])
        for user in (self.approver, self.reviewer, self.requester, self.wole):
            self.assertEqual(self.steps(user), [], user.email)

        self.procure(slug)
        self.assertEqual(self.steps(self.procurement), [])
        self.assertEqual(self.tasks(self.approver)[0][1:], ('approver', 'Approve the bill'))

        self.act(self.approver, slug, 'approve-by-approver')
        self.assertEqual(self.steps(self.approver), [])
        self.assertEqual(self.steps(self.reviewer), ['reviewer'])

        self.act(self.reviewer, slug, 'approve-by-reviewer')
        self.assertEqual(self.status_of(slug), 'Awaiting Final Approval')
        self.assertEqual(self.steps(self.reviewer), [])
        self.assertEqual(self.steps(self.wole), ['final'])

        self.act(self.wole, slug, 'final-approve')
        for user in (self.procurement, self.approver, self.reviewer, self.requester, self.wole):
            self.assertEqual(self.steps(user), [], user.email)

    def test_small_bill_goes_straight_to_the_approver(self):
        self.raise_bill(cost=SMALL)
        self.assertEqual(self.steps(self.approver), ['approver'])
        self.assertEqual(self.steps(self.procurement), [])

    def test_returned_bill_is_on_the_requesters_list(self):
        slug = self.raise_bill(cost=LARGE)
        self.act(self.procurement, slug, 'procurement-return', {'procurement_reason': 'Wrong amount'})
        self.assertEqual(self.tasks(self.requester)[0][1:], ('raised', 'Fix and resubmit the bill'))
        self.assertEqual(self.steps(self.procurement), [])

    def test_stand_in_sees_the_approvers_bill(self):
        tola = make_user('tola@example.com', 'APPROVER')
        now = timezone.now()
        Delegation.objects.create(person=self.approver, stand_in=tola, starts_at=now - timedelta(hours=1),
                                  ends_at=now + timedelta(days=3), reason='Annual leave')
        self.raise_bill(cost=SMALL)
        self.client.force_authenticate(user=tola)
        row = [t for t in self.client.get(MY_TASKS).data if t['kind'] == 'raise_payment'][0]
        self.assertEqual(row['step'], 'approver')
        self.assertTrue(row['on_behalf_of'])

    def test_other_approvers_do_not_see_it(self):
        someone = make_user('other.approver@example.com', 'APPROVER')
        self.raise_bill(cost=SMALL)
        self.assertEqual(self.steps(someone), [])

    def test_procurement_does_not_get_a_bill_they_raised(self):
        from work.models import WorkOrder
        slug = self.raise_bill(cost=LARGE)
        # As if a P&S user had raised it themselves.
        WorkOrder.objects.filter(slug=slug).update(owner=self.procurement, requester=self.procurement)
        self.assertEqual(self.steps(self.procurement), [])


del Route
