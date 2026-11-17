"""
Raise Payment bills of ₦100,000 or more: Procurement & Store either add the PO (as before), or
switch "PO needed" off and price the bill as quote lines (item, quantity, amount). The lines'
total is the quotation amount, so it must still match the bill amount.
"""
import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework import status

from work.models import WorkOrder
from work import test_raise_payment_route as route
from work.test_raise_payment_route import LARGE, TEMP_MEDIA

# Borrowed through the module, so the route tests are not collected (and run) a second time here.
Base = route.RaisePaymentApprovalRouteTests


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class RaisePaymentNoPoTests(TestCase):
    # Same set-up and helpers as the Raise Payment route tests, without re-running those tests.
    AUTO = Base.AUTO
    setUp = Base.setUp
    post_bill = Base.post_bill
    raise_bill = Base.raise_bill
    act = Base.act
    procure = Base.procure
    status_of = Base.status_of

    def submit_without_po(self, slug, lines, client_price='0'):
        return self.act(self.procurement, slug, 'procurement-submit', {
            'no_po_needed': 'true', 'lines': json.dumps(lines), 'client_price': client_price,
            'quotation_reference': 'Q-9',
        }, 'multipart')

    def test_bill_without_a_po_is_priced_as_lines_and_moves_on(self):
        slug = self.raise_bill(cost=LARGE)  # 2,500,000.00
        response = self.submit_without_po(slug, [
            {'description': 'Diesel', 'quantity': '2', 'amount': '1000000'},
            {'description': 'Delivery', 'quantity': '1', 'amount': '500000'},
        ])
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        wo = WorkOrder.objects.get(slug=slug)
        self.assertTrue(wo.no_po_needed)
        self.assertEqual(wo.po_number, '')
        self.assertFalse(wo.po_document)
        self.assertEqual(str(wo.quotation_amount), '2500000.00')
        self.assertEqual(wo.approval_status, 'Pending')  # on to the Approver
        self.assertEqual([(l['description'], l['total']) for l in response.data['raise_payment_lines']],
                         [('Diesel', '2000000.00'), ('Delivery', '500000.00')])

    def test_lines_total_must_match_the_bill(self):
        slug = self.raise_bill(cost=LARGE)
        response = self.submit_without_po(slug, [{'description': 'Diesel', 'quantity': '1', 'amount': '100'}])
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('quotation_amount', response.data)
        self.assertEqual(self.status_of(slug), 'Awaiting Procurement')

    def test_lines_are_required_and_must_be_complete(self):
        slug = self.raise_bill(cost=LARGE)
        self.assertIn('lines', self.submit_without_po(slug, []).data)
        self.assertIn('lines', self.submit_without_po(slug, [{'description': '', 'quantity': '1', 'amount': '5'}]).data)
        self.assertIn('lines', self.submit_without_po(slug, [{'description': 'X', 'quantity': '0', 'amount': '5'}]).data)
        self.assertEqual(self.status_of(slug), 'Awaiting Procurement')

    def test_po_route_unchanged_and_still_needs_the_po(self):
        slug = self.raise_bill(cost=LARGE)
        response = self.act(self.procurement, slug, 'procurement-submit', {'quotation_amount': LARGE, 'client_price': '0'}, 'multipart')
        self.assertIn('po_number', response.data)
        self.assertIn('po_document', response.data)
        self.procure(slug)
        wo = WorkOrder.objects.get(slug=slug)
        self.assertFalse(wo.no_po_needed)
        self.assertEqual(wo.po_number, 'PO-2026-0101')
        self.assertEqual(wo.quote_lines.count(), 0)

    def test_returned_bill_resubmitted_with_a_po_drops_the_old_lines(self):
        slug = self.raise_bill(cost=LARGE)
        self.assertEqual(self.submit_without_po(slug, [{'description': 'Diesel', 'quantity': '1', 'amount': LARGE}]).status_code,
                         status.HTTP_200_OK)
        # Back to P&S (as after a return and resubmission), who now add a PO instead.
        WorkOrder.objects.filter(slug=slug).update(approval_status='Awaiting Procurement')
        self.procure(slug)
        wo = WorkOrder.objects.get(slug=slug)
        self.assertFalse(wo.no_po_needed)
        self.assertEqual(wo.quote_lines.count(), 0)
        self.assertEqual(wo.po_number, 'PO-2026-0101')


del Base
