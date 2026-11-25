"""
?search=<text> on list endpoints searches all records (not just the first page), and every
searchable endpoint accepts it without error. Role-based filtering still applies first.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import URLPattern, URLResolver, get_resolver
from rest_framework.test import APIClient

from accounts.models import Vendor
from facility.models import Facility
from work.models import WorkRequest


def searchable_list_urls():
    """Every list endpoint that has search_fields, as '/path/'."""
    def walk(patterns, prefix=''):
        for p in patterns:
            if isinstance(p, URLResolver):
                yield from walk(p.url_patterns, prefix + str(p.pattern))
            elif isinstance(p, URLPattern):
                cls = getattr(p.callback, 'cls', None)
                actions = getattr(p.callback, 'actions', None) or {}
                if cls is not None and actions.get('get') == 'list' and getattr(cls, 'search_fields', None):
                    yield '/' + (prefix + str(p.pattern)).replace('^', '').replace('$', '')
    return sorted({u for u in walk(get_resolver().url_patterns) if '(?P<format>' not in u})


def make_user(email, roles):
    user = get_user_model().objects.create_user(email=email, password='x', first_name='Test', last_name='User')
    user.roles = roles
    user.is_active = True
    user.save()
    return user


class SearchTests(TestCase):

    def setUp(self):
        self.boss = make_user('boss@example.com', 'SUPER ADMIN')
        self.api = APIClient()
        self.api.force_authenticate(user=self.boss)

    def test_every_searchable_endpoint_accepts_search(self):
        urls = searchable_list_urls()
        self.assertGreater(len(urls), 30)
        for url in urls:
            with self.subTest(url=url):
                response = self.api.get(url, {'search': 'zz-nothing-matches'})
                self.assertLess(response.status_code, 500, f'{url} -> {response.status_code}')

    def test_search_finds_an_old_record_beyond_the_first_page(self):
        facility = Facility.objects.create(name='HQ Office')
        old = WorkRequest.objects.create(type='Work', requester=self.boss, owner=self.boss, facility=facility,
                                         description='Broken water heater in kitchen')
        for n in range(25):  # more than a page of newer requests
            WorkRequest.objects.create(type='Work', requester=self.boss, owner=self.boss, facility=facility,
                                       description=f'Routine check {n}')
        data = self.api.get('/work/api/work-requests/', {'search': 'water heater'}).data
        rows = data['results'] if isinstance(data, dict) else data
        self.assertEqual([r['id'] for r in rows], [old.id])
        # Without a search, the list is unchanged (first page of 20).
        self.assertEqual(len(self.api.get('/work/api/work-requests/').data['results']), 20)

    def test_search_on_vendors_matches_name_or_account(self):
        Vendor.objects.create(name='Cool Air Ltd', type='Company', currency='NGN', account_number='0123456789')
        Vendor.objects.create(name='Bright Power', type='Company', currency='NGN')
        names = lambda q: [v['name'] for v in self.api.get('/accounts/api/vendors/', {'search': q}).data]
        self.assertEqual(names('cool'), ['Cool Air Ltd'])
        self.assertEqual(names('0123456789'), ['Cool Air Ltd'])
        self.assertEqual(len(names('')), 2)

    def test_search_does_not_widen_what_a_role_can_see(self):
        facility = Facility.objects.create(name='HQ Office')
        someone = make_user('other@example.com', 'REQUESTER')
        WorkRequest.objects.create(type='Work', requester=someone, owner=someone, facility=facility,
                                   description='Secret roof job')
        requester = make_user('req@example.com', 'REQUESTER')
        api = APIClient()
        api.force_authenticate(user=requester)
        data = api.get('/work/api/work-requests/', {'search': 'roof'}).data
        rows = data['results'] if isinstance(data, dict) else data
        self.assertEqual(rows, [])
