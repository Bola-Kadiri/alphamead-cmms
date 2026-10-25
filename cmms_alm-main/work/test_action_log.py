"""
Time stamp on every action: append-only, ordered, with the time taken since the
previous action on the same document, and stand-in (on behalf of) details.
"""
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from facility.models import Facility
from work.models import FlowAction, WorkOrder, WorkRequest
from work.models.action_log import ActionLogError, history, record_action

User = get_user_model()


def make_user(email, roles, first='Test'):
    user = User.objects.create_user(email=email, password='x', first_name=first, last_name='User')
    user.roles = roles
    user.save()
    return user


class ActionTimeStampTests(TestCase):

    def setUp(self):
        self.facility = Facility.objects.create(name='Nestle Agbara', code='NA-01')
        self.tunde = make_user('tunde@example.com', 'REQUESTER', 'Tunde')
        self.femi = make_user('femi@example.com', 'APPROVER', 'Femi')
        self.ada = make_user('ada@example.com', 'APPROVER', 'Ada')
        self.wr = WorkRequest.objects.create(type='Work', requester=self.tunde, owner=self.tunde,
                                             facility=self.facility, description='AC not cooling')

    def stamp_at(self, when, *args, **kwargs):
        with mock.patch('work.models.action_log.timezone.now', return_value=when):
            return record_action(*args, **kwargs)

    def test_records_who_what_when_and_time_taken(self):
        start = timezone.now()
        raised = self.stamp_at(start, self.wr, 'work_request', 'raised', self.tunde)
        reviewed = self.stamp_at(start + timedelta(hours=2, minutes=28), self.wr, 'work_request', 'reviewed',
                                 self.femi, signature='Femi User')

        self.assertIsNone(raised.since_previous)
        self.assertEqual(reviewed.since_previous, timedelta(hours=2, minutes=28))
        self.assertEqual(reviewed.actor_name, 'Femi User')
        self.assertEqual(reviewed.actor_role, 'APPROVER')
        self.assertEqual(reviewed.facility, self.facility)  # taken from the document
        self.assertEqual([a.action for a in history(self.wr)], ['raised', 'reviewed'])

    def test_time_taken_is_per_document(self):
        other = WorkOrder.objects.create(type='Unplanned', requester=self.tunde, owner=self.tunde, facility=self.facility)
        start = timezone.now()
        self.stamp_at(start, self.wr, 'work_request', 'raised', self.tunde)
        first_on_other = self.stamp_at(start + timedelta(hours=5), other, 'work_order', 'raised', self.tunde)
        self.assertIsNone(first_on_other.since_previous)
        self.assertEqual(len(history(other)), 1)

    def test_stand_in_is_recorded(self):
        stamp = record_action(self.wr, 'work_request', 'reviewed', self.ada, on_behalf_of=self.femi)
        self.assertEqual(stamp.on_behalf_of, self.femi)
        self.assertEqual(stamp.on_behalf_of_name, 'Femi User')

    def test_names_and_roles_are_kept_after_changes(self):
        stamp = record_action(self.wr, 'work_request', 'reviewed', self.femi)
        self.femi.first_name = 'Femi-renamed'
        self.femi.roles = 'REVIEWER'
        self.femi.save()
        stamp.refresh_from_db()
        self.assertEqual(stamp.actor_name, 'Femi User')
        self.assertEqual(stamp.actor_role, 'APPROVER')

    def test_cannot_be_changed_or_deleted(self):
        stamp = record_action(self.wr, 'work_request', 'raised', self.tunde, reason='first')
        stamp.reason = 'edited'
        with self.assertRaises(ActionLogError):
            stamp.save()
        with self.assertRaises(ActionLogError):
            stamp.delete()
        with self.assertRaises(ActionLogError):
            FlowAction.objects.filter(pk=stamp.pk).update(reason='edited')
        with self.assertRaises(ActionLogError):
            FlowAction.objects.all().delete()
        stamp.refresh_from_db()
        self.assertEqual(stamp.reason, 'first')
