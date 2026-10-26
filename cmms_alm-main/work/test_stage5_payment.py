"""
Stage 5 · Payment in the five-stage flow: AP Officers raise the voucher against the approved
invoice → REVIEWER (Internal Control) checks the full trail → Head of Finance & Treasury
approves, pays and confirms Paid (AP attaches the receipt but never confirms Paid).
"""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status

from work import test_stage4_invoice as s4
from work.models import Invoice, Notification, PaymentVoucher, WithholdingTaxRate
from work.models import invoice_flow as stage4
from work.models.action_log import history

User = get_user_model()
VOUCHERS = '/work/api/payment-vouchers/'
RATES = '/work/api/wht-rates/'
MY_TASKS = '/work/api/my-tasks/'


def receipt(name='zenith-batch.pdf'):
    return SimpleUploadedFile(name, b'%PDF-1.4 receipt', content_type='application/pdf')


@override_settings(MEDIA_ROOT=s4.TEMP_MEDIA)
class Stage5PaymentTests(TestCase):

    def setUp(self):
        s4.Stage4InvoiceTests.setUp(self)  # Stages 1–3 done, same people and vendors.
        self.ibrahim = User.objects.get(email='ibrahim@example.com')
        self.inv = stage4.start(self.wcc, self.emeka)
        stage4.save_details(self.inv, self.emeka, vendor_invoice_number='INV-CA-0912',
                            invoice_date=timezone.localdate(), amount='120000', vat_charged=True, files=[s4.pdf()])
        stage4.submit(self.inv, self.emeka)
        stage4.review(self.inv, self.seun, 'Seun Test')
        stage4.approve(self.inv, self.adaeze, 'Adaeze Test')
        self.five = WithholdingTaxRate.objects.get(name='Contracts and supplies')

    api = s4.Stage4InvoiceTests.api
    post = s4.Stage4InvoiceTests.post

    def started(self, user=None):
        response = self.post(user or self.seun, f'{VOUCHERS}flow-start/', {'invoice': self.inv.pk})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return PaymentVoucher.objects.get(pk=response.data['id'])

    def submitted(self):
        v = self.started()
        self.post(self.seun, f'{VOUCHERS}{v.pk}/flow-details/', {'wht_rate': self.five.pk, 'payment_method': 'bank_transfer'})
        response = self.post(self.seun, f'{VOUCHERS}{v.pk}/flow-submit/')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return v

    def approved(self):
        v = self.submitted()
        self.assertEqual(self.post(self.ibrahim, f'{VOUCHERS}{v.pk}/flow-review/', {'signature': 'Ibrahim Test'}).status_code, 200)
        response = self.post(self.adaeze, f'{VOUCHERS}{v.pk}/flow-approve/', {'signature': 'Adaeze Test'})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return v

    def attach(self, vouchers, user=None):
        return self.post(user or self.seun, f'{VOUCHERS}attach-receipt/',
                         {'vouchers': [v.pk for v in vouchers], 'file': receipt()}, 'multipart')

    def pay(self, vouchers, user=None, when=None, reference='ZEN-BATCH-B1031'):
        return self.post(user or self.adaeze, f'{VOUCHERS}confirm-paid/', {
            'vouchers': [v.pk for v in vouchers], 'payment_date': (when or timezone.localdate()).isoformat(),
            'bank_reference': reference,
        })

    # ── raising ──────────────────────────────────────────────────────────────

    def test_ap_sees_the_approved_invoice_to_pay(self):
        rows = self.api(self.seun).get(f'{VOUCHERS}to-raise/').data
        self.assertEqual([r['invoice_id'] for r in rows], [self.inv.pk])
        self.assertIn('voucher_to_raise', [t['kind'] for t in self.api(self.seun).get(MY_TASKS).data])
        self.assertEqual(self.api(self.adaeze).get(f'{VOUCHERS}to-raise/').data, [])

    def test_voucher_copies_and_locks_the_invoice_amounts(self):
        v = self.started()
        self.assertRegex(v.voucher_number, r'^PV-\d{4}-00001$')
        self.assertEqual((v.amount, v.vat), (Decimal('120000.00'), Decimal('9000.00')))
        response = self.post(self.seun, f'{VOUCHERS}{v.pk}/flow-details/', {'wht_rate': self.five.pk, 'payment_method': 'bank_transfer'})
        self.assertEqual(response.data['amounts']['wht_amount'], '6000.00')
        self.assertEqual(response.data['amounts']['net_amount'], '123000.00')

    def test_one_voucher_per_invoice(self):
        self.started()
        response = self.post(self.tola, f'{VOUCHERS}flow-start/', {'invoice': self.inv.pk})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.api(self.seun).get(f'{VOUCHERS}to-raise/').data, [])

    def test_only_ap_raises_the_voucher(self):
        for user in (self.emeka, self.adaeze, self.ibrahim):
            response = self.post(user, f'{VOUCHERS}flow-start/', {'invoice': self.inv.pk})
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, user.email)

    def test_submit_needs_the_rate_and_the_method(self):
        v = self.started()
        response = self.post(self.seun, f'{VOUCHERS}{v.pk}/flow-submit/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('withholding tax rate', response.data['error'])
        self.assertIn('how it will be paid', response.data['error'])

    def test_switched_off_rate_cannot_be_chosen(self):
        self.five.is_active = False
        self.five.save()
        v = self.started()
        response = self.post(self.seun, f'{VOUCHERS}{v.pk}/flow-details/', {'wht_rate': self.five.pk})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ── checking and approving ───────────────────────────────────────────────

    def test_internal_control_checks_pass_and_trail_is_complete(self):
        v = self.submitted()
        data = self.api(self.ibrahim).get(f'{VOUCHERS}{v.pk}/').data
        self.assertTrue(all(row['ok'] for row in data['checks']), data['checks'])
        self.assertTrue(all(row['ok'] for row in data['trail']), data['trail'])
        self.assertEqual(data['my_actions'], ['review', 'return'])
        self.assertTrue(Notification.objects.filter(recipient=self.ibrahim).exists())

    def test_review_tells_the_head_of_finance(self):
        v = self.submitted()
        self.post(self.ibrahim, f'{VOUCHERS}{v.pk}/flow-review/', {'signature': 'Ibrahim Test'})
        v.refresh_from_db()
        self.assertEqual(v.status, 'Awaiting Approval')
        self.assertTrue(Notification.objects.filter(recipient=self.adaeze, title__contains=v.voucher_number).exists())

    def test_return_then_resubmit(self):
        v = self.submitted()
        response = self.post(self.ibrahim, f'{VOUCHERS}{v.pk}/flow-return/', {'reason': 'Wrong WHT rate'})
        self.assertEqual(response.data['status'], 'Returned')
        self.assertEqual(self.post(self.ibrahim, f'{VOUCHERS}{v.pk}/flow-return/', {'reason': ''}).status_code, 400)
        response = self.post(self.seun, f'{VOUCHERS}{v.pk}/flow-submit/')
        self.assertEqual(response.data['status'], 'Awaiting Review')
        self.assertEqual(list(history(v).values_list('action', flat=True)), ['raised', 'sent_back', 'resubmitted'])

    def test_only_the_head_of_finance_approves(self):
        v = self.submitted()
        self.post(self.ibrahim, f'{VOUCHERS}{v.pk}/flow-review/', {'signature': 'Ibrahim Test'})
        for user, name in ((self.seun, 'Seun Test'), (self.ibrahim, 'Ibrahim Test')):
            response = self.post(user, f'{VOUCHERS}{v.pk}/flow-approve/', {'signature': name})
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, user.email)

    # ── paying ───────────────────────────────────────────────────────────────

    def test_ap_attaches_the_receipt_but_cannot_confirm_paid(self):
        v = self.approved()
        self.assertEqual(self.attach([v]).status_code, status.HTTP_200_OK)
        response = self.pay([v], user=self.seun)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('cannot confirm Paid', response.data['error'])

    def test_several_receipts_at_once(self):
        v = self.approved()
        response = self.post(self.seun, f'{VOUCHERS}attach-receipt/',
                             {'vouchers': [v.pk], 'file': [receipt('batch.pdf'), receipt('transfer-slip.pdf')]}, 'multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(v.attachments.count(), 2)

    def test_paid_needs_the_receipt(self):
        v = self.approved()
        response = self.pay([v])
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('attach the bank receipt', response.data['error'])

    def test_payment_date_cannot_be_in_the_future(self):
        v = self.approved()
        self.attach([v])
        response = self.pay([v], when=timezone.localdate() + timedelta(days=1))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_confirm_paid_closes_the_job_and_sends_the_remittance(self):
        v = self.approved()
        self.attach([v])
        response = self.pay([v])
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        v.refresh_from_db()
        self.assertEqual((v.status, v.paid_by, v.bank_reference), ('Paid', self.adaeze, 'ZEN-BATCH-B1031'))
        self.assertEqual(Invoice.objects.get(pk=self.inv.pk).status, 'Paid')
        self.wo.refresh_from_db()
        self.assertEqual(self.wo.work_status, 'closed')
        self.assertTrue(Notification.objects.filter(recipient=self.emeka, title__contains='Payment made').exists())
        # The contractor sees the remittance advice and "Paid" on their invoice.
        data = self.api(self.emeka).get(f'{VOUCHERS}{v.pk}/').data
        self.assertEqual(data['remittance']['net_amount'], '123000.00')
        self.assertNotIn('checks', data)
        invoice_flow = self.api(self.emeka).get(f'/work/api/invoices/{self.inv.pk}/flow/').data
        self.assertEqual(invoice_flow['payment']['status'], 'Paid')

    def test_batch_payment_stamps_each_voucher(self):
        v = self.approved()
        self.attach([v])
        self.pay([v])
        self.assertEqual(list(history(v).values_list('action', flat=True)),
                         ['raised', 'reviewed', 'approved', 'paid'])
        self.assertEqual(self.pay([v]).status_code, status.HTTP_400_BAD_REQUEST)  # cannot be paid twice

    def test_payment_failed_then_paid(self):
        v = self.approved()
        self.assertEqual(self.post(self.adaeze, f'{VOUCHERS}{v.pk}/payment-failed/', {'reason': ''}).status_code, 400)
        response = self.post(self.adaeze, f'{VOUCHERS}{v.pk}/payment-failed/', {'reason': 'Account name mismatch'})
        self.assertEqual(response.data['status'], 'Payment Failed')
        self.assertTrue(Notification.objects.filter(recipient=self.seun, title__contains='Payment failed').exists())
        self.attach([v])
        self.assertEqual(self.pay([v]).status_code, status.HTTP_200_OK)

    # ── who sees what ────────────────────────────────────────────────────────

    def test_contractor_sees_only_paid_vouchers(self):
        v = self.approved()
        self.assertEqual(self.api(self.emeka).get(VOUCHERS).data, [])
        self.assertEqual(self.api(self.emeka).get(f'{VOUCHERS}{v.pk}/').status_code, status.HTTP_404_NOT_FOUND)

    def test_client_sees_no_payments(self):
        # With a real login the ClientAccessMiddleware refuses the URL outright (not on the client allow-list).
        v = self.approved()
        ngozi = User.objects.get(email='ngozi@example.com')
        self.assertEqual(self.api(ngozi).get(VOUCHERS).data, [])
        self.assertEqual(self.api(ngozi).get(f'{VOUCHERS}{v.pk}/').status_code, status.HTTP_404_NOT_FOUND)

    def test_invoice_chain_names_the_head_of_finance(self):
        data = self.api(self.seun).get(f'/work/api/invoices/{self.inv.pk}/flow/').data
        self.assertEqual(data['chain'][-1]['person'], 'Adaeze Test')

    def test_only_finance_keeps_the_rates(self):
        self.assertEqual(self.post(self.seun, RATES, {'name': 'Rent', 'rate': '10'}).status_code, status.HTTP_403_FORBIDDEN)
        response = self.post(self.adaeze, RATES, {'name': 'Rent', 'rate': '10'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertIn('Rent', [r['name'] for r in self.api(self.seun).get(RATES).data])
