from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from asset_inventory.models import ItemRequest
from facility.models import Facility
from report.models import UserLoginLog
from report.services import get_user_facility_report_queryset
from work.models import WorkRequest

User = get_user_model()


def make_user(email, roles='SUPER ADMIN', **extra):
    user = User.objects.create_user(
        email=email,
        password='testpass123',
        first_name=extra.pop('first_name', 'Test'),
        last_name=extra.pop('last_name', 'User'),
    )
    user.roles = roles
    user.is_active = True
    user.save()
    return user


class UserFacilityReportServiceTestCase(TestCase):
    """Tests for report.services.get_user_facility_report_queryset"""

    def setUp(self):
        self.facility_a = Facility.objects.create(name='Facility A')
        self.facility_b = Facility.objects.create(name='Facility B')

        self.alice = make_user('alice@example.com', first_name='Alice', last_name='Smith')
        self.alice.facility.add(self.facility_a)

        self.bob = make_user('bob@example.com', first_name='Bob', last_name='Jones')
        self.bob.facility.add(self.facility_b)

        WorkRequest.objects.create(type='Work', requester=self.alice, facility=self.facility_a)
        WorkRequest.objects.create(type='Work', requester=self.alice, facility=self.facility_a)
        ItemRequest.objects.create(requested_by=self.alice, facility=self.facility_a)

        UserLoginLog.objects.create(user=self.alice)
        UserLoginLog.objects.create(user=self.alice)
        UserLoginLog.objects.create(user=self.bob)

    def test_counts_are_accurate_and_not_inflated_by_joins(self):
        """
        Regression guard for the classic Django multi-Count() JOIN
        fan-out bug: combining login/work-request/item-request counts on
        one annotated queryset must not multiply any of them together.
        """
        alice_row = get_user_facility_report_queryset().get(pk=self.alice.pk)
        self.assertEqual(alice_row.login_count, 2)
        self.assertEqual(alice_row.work_request_count, 2)
        self.assertEqual(alice_row.item_request_count, 1)

        bob_row = get_user_facility_report_queryset().get(pk=self.bob.pk)
        self.assertEqual(bob_row.login_count, 1)
        self.assertEqual(bob_row.work_request_count, 0)
        self.assertEqual(bob_row.item_request_count, 0)

    def test_facility_filter(self):
        qs = get_user_facility_report_queryset(facility_id=self.facility_a.id)
        self.assertIn(self.alice, qs)
        self.assertNotIn(self.bob, qs)

    def test_search_filter(self):
        qs = get_user_facility_report_queryset(search='bob')
        self.assertIn(self.bob, qs)
        self.assertNotIn(self.alice, qs)


class UserFacilityReportAPITestCase(TestCase):
    """Tests for GET /report/api/user-facility/"""

    def setUp(self):
        self.client = APIClient()
        self.facility = Facility.objects.create(name='Facility A')

        self.admin = make_user('admin@example.com', roles='SUPER ADMIN')
        self.requester = make_user('req@example.com', roles='REQUESTER')

        self.alice = make_user('alice2@example.com', first_name='Alice', last_name='Smith')
        self.alice.facility.add(self.facility)
        WorkRequest.objects.create(type='Work', requester=self.alice, facility=self.facility)
        UserLoginLog.objects.create(user=self.alice)

        self.url = '/report/api/user-facility/'

    def test_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_role_without_report_access_is_forbidden(self):
        self.client.force_authenticate(user=self.requester)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_returns_wrapped_success_response(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['message'], 'User facility report retrieved successfully')
        self.assertIn('results', response.data['data'])

        rows_by_email = {row['email']: row for row in response.data['data']['results']}
        self.assertEqual(rows_by_email['alice2@example.com']['work_request_count'], 1)
        self.assertEqual(rows_by_email['alice2@example.com']['login_count'], 1)
        # Alice has an explicit facility assignment, so it's not inferred.
        self.assertEqual(rows_by_email['alice2@example.com']['facilities'], ['Facility A'])
        self.assertFalse(rows_by_email['alice2@example.com']['facilities_inferred'])
        # No visitor-pass feature exists yet — must be null, not a fabricated 0.
        self.assertIsNone(rows_by_email['alice2@example.com']['visitor_pass_count'])

    def test_facility_falls_back_to_work_request_history_when_unassigned(self):
        """
        Most users in this system have no explicit facility assignment
        (neither User.facility nor accounts.Personnel.facility is
        populated in practice) — the report should still surface a
        facility when their own work request history implies one,
        clearly flagged as inferred rather than assigned.
        """
        unassigned = make_user('unassigned@example.com', first_name='No', last_name='Assignment')
        WorkRequest.objects.create(type='Work', requester=unassigned, facility=self.facility)

        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.url, {'search': 'unassigned'})

        row = response.data['data']['results'][0]
        self.assertEqual(row['facilities'], ['Facility A'])
        self.assertTrue(row['facilities_inferred'])

    def test_facility_is_empty_with_no_assignment_or_history(self):
        no_data_user = make_user('nodata@example.com', first_name='No', last_name='Data')

        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.url, {'search': 'nodata'})

        row = response.data['data']['results'][0]
        self.assertEqual(row['facilities'], [])
        self.assertFalse(row['facilities_inferred'])

    def test_facility_query_param_filters_results(self):
        other_facility = Facility.objects.create(name='Facility Z')
        outsider = make_user('outsider@example.com', first_name='Out', last_name='Sider')
        outsider.facility.add(other_facility)

        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.url, {'facility': self.facility.id})

        emails = [row['email'] for row in response.data['data']['results']]
        self.assertIn('alice2@example.com', emails)
        self.assertNotIn('outsider@example.com', emails)


class UserFacilityReportPageTestCase(TestCase):
    """
    Tests for the report/user_facility.html page view.

    Note: a full render() of this page (and of every other page in the
    app) currently raises NoReverseMatch from inside
    templates/partials/sidebar.html, which references ~40 `{% url %}`
    names — 'work:work_request', 'accounts:users', etc. — that aren't
    registered in their apps' urls.py yet. That is a pre-existing,
    app-wide defect unrelated to the report module (see the one-line fix
    already applied to dashboard/urls.py for the 'dashboard:dashboard'
    case it shared), so we only exercise the view's own logic here via
    resolve()/the login gate, rather than asserting a 200 render.
    """

    def setUp(self):
        self.user = make_user('viewer@example.com')
        Facility.objects.create(name='Facility A')

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get('/report/user_facility/')
        self.assertEqual(response.status_code, 302)

    def test_view_passes_facilities_in_context(self):
        """
        Isolates the view's own context-building from the shared,
        currently-broken template chain (see class docstring) by
        stubbing out the render() call it hands off to.
        """
        from unittest.mock import patch
        from django.http import HttpResponse
        from django.test import RequestFactory
        from report import views as report_views

        request = RequestFactory().get('/report/user_facility/')
        request.user = self.user

        with patch.object(report_views, 'render', return_value=HttpResponse()) as mock_render:
            report_views.user_facility(request)

        template_name, context = mock_render.call_args[0][1], mock_render.call_args[0][2]
        self.assertEqual(template_name, 'report/user_facility.html')
        self.assertEqual(list(context['facilities']), list(Facility.objects.all()))


class LoginTrackingTestCase(TestCase):
    """Tests for the login-count data source behind the report."""

    def setUp(self):
        self.user = make_user('tracked@example.com')

    def test_user_logged_in_signal_creates_a_login_log(self):
        user_logged_in.send(sender=User, request=None, user=self.user)
        self.assertEqual(UserLoginLog.objects.filter(user=self.user).count(), 1)

    def test_jwt_login_records_a_login_log(self):
        """
        utils.serializers.CustomTokenObtainPairSerializer.get_token emits
        user_logged_in on every successful token issuance — verify that
        wiring end-to-end through the real /auth/token/ endpoint.
        """
        response = self.client.post('/auth/token/', {
            'email': self.user.email,
            'password': 'testpass123',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(UserLoginLog.objects.filter(user=self.user).count(), 1)


class DashboardAnalyticsTestCase(TestCase):
    """
    Tests for report.analytics — the org-wide CMMS analytics behind
    GET /report/api/dashboard/.
    """

    def setUp(self):
        from datetime import date, timedelta

        self.today = date.today()
        self.facility = Facility.objects.create(name='Facility A')
        self.user = make_user('analytics@example.com')

        # A stale, still-open work request (backlog + insight trigger)
        wr = WorkRequest.objects.create(
            type='Work', requester=self.user, facility=self.facility,
            approval_status='Pending Review',
        )
        WorkRequest.objects.filter(pk=wr.pk).update(
            created_at=self.today - timedelta(days=10)
        )

        # A fully approved one, for cycle-time
        approved_wr = WorkRequest.objects.create(
            type='Work', requester=self.user, facility=self.facility,
            approval_status='Fully Approved',
        )
        WorkRequest.objects.filter(pk=approved_wr.pk).update(
            created_at=self.today - timedelta(days=3),
            fully_approved_at=self.today,
        )

    def test_work_request_analytics_backlog_and_cycle_time(self):
        from report.analytics import get_work_request_analytics

        data = get_work_request_analytics()
        self.assertEqual(data['total'], 2)
        self.assertEqual(data['backlog'], 1)
        self.assertEqual(data['stale_backlog_count'], 1)
        self.assertIsNotNone(data['avg_approval_cycle_days'])
        self.assertEqual(data['top_facilities'][0]['facility__name'], 'Facility A')

    def test_work_order_overdue_detection(self):
        from datetime import timedelta

        from work.models import WorkOrder
        from report.analytics import get_work_order_analytics

        WorkOrder.objects.create(
            requester=self.user, facility=self.facility, approval_status='Approved',
            expected_start_date=self.today - timedelta(days=5),
        )
        data = get_work_order_analytics()
        self.assertEqual(data['overdue'], 1)

    def test_invoice_overdue_amount(self):
        from datetime import timedelta

        from work.models import WorkOrderCompletion, WorkOrder, Invoice
        from report.analytics import get_invoice_analytics

        wo = WorkOrder.objects.create(requester=self.user, facility=self.facility)
        wcc = WorkOrderCompletion.objects.create(work_order=wo, approval_status='Approved')
        Invoice.objects.create(
            work_completion=wcc, work_order=wo, facility=self.facility,
            invoice_date=self.today - timedelta(days=20),
            due_date=self.today - timedelta(days=5),
            total_amount=1000,
            approval_status='Pending',
        )
        data = get_invoice_analytics()
        self.assertEqual(data['overdue_count'], 1)
        self.assertEqual(data['overdue_amount'], 1000)

    def test_low_stock_inventory_detection(self):
        from asset_inventory.models import AssetCategory, AssetSubCategory, Inventory
        from report.analytics import get_asset_analytics

        category = AssetCategory.objects.create(type='General', code='CAT1', name='Cat')
        subcategory = AssetSubCategory.objects.create(
            type='General', code='SUB1', name='Sub', asset_category=category
        )
        Inventory.objects.create(
            category=category, subcategory=subcategory,
            quantity=1, reorder_level=5, unit_price=10,
        )
        data = get_asset_analytics()
        self.assertEqual(data['inventory']['low_stock_count'], 1)

    def test_generate_insights_flags_real_issues(self):
        from report.analytics import get_dashboard_analytics

        data = get_dashboard_analytics()
        self.assertIn('insights', data)
        self.assertTrue(len(data['insights']) >= 1)
        messages = ' '.join(i['message'] for i in data['insights'])
        self.assertIn('7 days', messages)  # the stale backlog insight

    def test_dashboard_analytics_endpoint_returns_wrapped_success(self):
        admin = make_user('admin2@example.com', roles='SUPER ADMIN')
        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.get('/report/api/dashboard/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        for key in ('work_requests', 'work_orders', 'completions', 'invoices',
                    'payment_requisitions', 'ppm', 'procurement', 'assets', 'insights'):
            self.assertIn(key, response.data['data'])

    def test_dashboard_analytics_endpoint_requires_report_access(self):
        requester = make_user('requester2@example.com', roles='REQUESTER')
        client = APIClient()
        client.force_authenticate(user=requester)

        response = client.get('/report/api/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
