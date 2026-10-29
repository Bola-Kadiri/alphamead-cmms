"""
Stage 5 (Payment) of the five-stage flow: payment vouchers and the withholding tax rates.
"""
from decimal import Decimal

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from work.models import payment_flow as stage5
from work.models.action_log import history
from work.models.flow_rules import ActionRefused
from work.models.invoice import Invoice
from work.models.payment_voucher import PaymentVoucher, WithholdingTaxRate

FINANCE_SIDE = {'SUPER ADMIN', 'ADMIN', 'AP OFFICER', 'REVIEWER', 'HEAD OF FINANCE & TREASURY'}
RATE_KEEPERS = {'SUPER ADMIN', 'HEAD OF FINANCE & TREASURY'}


def _person(slot_people):
    return (slot_people[0].name.strip() or slot_people[0].email) if slot_people else None


def _history(document):
    return [
        {'action': a.action, 'label': a.get_action_display(), 'actor': a.actor_name, 'role': a.actor_role,
         'on_behalf_of': a.on_behalf_of_name or None, 'reason': a.reason or None, 'signature': a.signature or None,
         'at': a.at, 'since_previous_seconds': a.since_previous.total_seconds() if a.since_previous else None}
        for a in history(document)
    ]


def _row(v):
    """One line in a list of vouchers."""
    return {
        'id': v.pk, 'number': v.voucher_number, 'status': v.status, 'status_label': v.get_status_display(),
        'vendor': v.vendor.name, 'bank': v.vendor.bank, 'account_last4': (v.vendor.account_number or '')[-4:],
        # Only the finance side lists vouchers, so the full account to pay into is shown.
        'account_name': v.vendor.account_name, 'account_number': v.vendor.account_number or '',
        'invoice': v.invoice.vendor_invoice_number or v.invoice.invoice_number,
        'description': v.work_order.description, 'facility': v.facility.name if v.facility_id else None,
        'net_amount': str(v.net_amount), 'failure_reason': v.failure_reason or None,
        'approved_at': history(v).filter(action='approved').values_list('at', flat=True).last(),
        'paid_at': v.paid_at,
    }


def voucher_flow_data(v, user):
    """Everything the voucher screen needs. The contractor only ever sees the remittance advice."""
    if user.roles == 'CONTRACTOR':
        return {'number': v.voucher_number, 'status': v.status, 'remittance': stage5.remittance(v) if v.status == 'Paid' else None}
    actions = stage5.available_actions(v, user)
    chain = []
    for step in ('ap_officer', 'reviewer', 'head_of_finance'):
        people = stage5.people_for(v, step)
        entry = {'step': step, 'label': stage5.STEP_LABELS[step], 'kind': 'named' if step == 'head_of_finance' else 'team'}
        if step == 'head_of_finance':
            entry['person'] = _person(people)
        else:
            entry['people'] = len(people)
        chain.append(entry)
    inv, wo = v.invoice, v.work_order
    return {
        'id': v.pk,
        'number': v.voucher_number,
        'status': v.status,
        'status_label': v.get_status_display(),
        'waiting_on': stage5.waiting_on(v),
        'chain': chain,
        # The full account to pay into, read live from the vendor record (kept by the Super Admin).
        'vendor': {'id': v.vendor_id, 'name': v.vendor.name, 'bank': v.vendor.bank,
                   'account_name': v.vendor.account_name, 'account_number': v.vendor.account_number or '',
                   'account_last4': (v.vendor.account_number or '')[-4:], 'has_bank_details': v.vendor.has_bank_details},
        'invoice': {'id': inv.pk, 'number': inv.invoice_number, 'vendor_invoice_number': inv.vendor_invoice_number},
        'work_order': {'slug': wo.slug, 'number': wo.work_order_number, 'description': wo.description,
                       'client_price': str(wo.client_price) if wo.client_price is not None else None},
        'facility': v.facility.name if v.facility_id else None,
        'amounts': {'amount': str(v.amount), 'vat': str(v.vat), 'wht_rate': v.wht_rate_id,
                    'wht_label': str(v.wht_rate) if v.wht_rate_id else None, 'wht_percent': str(v.wht_percent),
                    'wht_amount': str(v.wht_amount), 'net_amount': str(v.net_amount)},
        'payment_method': v.payment_method,
        'payment': {'payment_date': v.payment_date, 'bank_reference': v.bank_reference, 'paid_at': v.paid_at,
                    'paid_by': (v.paid_by.name.strip() or v.paid_by.email) if v.paid_by_id else None,
                    'failure_reason': v.failure_reason or None},
        'files': [{'id': f.id, 'url': f.file.url if f.file else None, 'name': f.file.name.rsplit('/', 1)[-1] if f.file else ''}
                  for f in v.attachments.all()],
        'trail': stage5.trail(v),
        'checks': stage5.checks(v),
        'problems': stage5.problems(v) if 'submit' in actions else [],
        'remittance': stage5.remittance(v) if v.status == 'Paid' else None,
        'history': _history(v),
        'timing': stage5.timing(v),
        'my_actions': actions,
    }


class PaymentVoucherViewSet(viewsets.ReadOnlyModelViewSet):
    """Five-stage payment vouchers. Every change goes through the actions below and the Stage 5 rules."""
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = PaymentVoucher.objects.select_related('vendor', 'invoice', 'facility', 'work_order')
        if user.roles in FINANCE_SIDE:
            return qs
        if user.roles == 'CONTRACTOR' and user.vendor_id:
            return qs.filter(vendor_id=user.vendor_id, status='Paid')
        return qs.none()

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        if request.query_params.get('status'):
            qs = qs.filter(status=request.query_params['status'])
        return Response([_row(v) for v in qs])

    def retrieve(self, request, *args, **kwargs):
        return Response(voucher_flow_data(self.get_object(), request.user))

    def _call(self, request, func, *args, **kwargs):
        voucher = self.get_object()
        try:
            func(voucher, request.user, *args, **kwargs)
        except ActionRefused as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        voucher.refresh_from_db()
        return Response(voucher_flow_data(voucher, request.user))

    def _selected(self, request):
        ids = request.data.getlist('vouchers') if hasattr(request.data, 'getlist') else request.data.get('vouchers', [])
        vouchers = list(self.get_queryset().filter(pk__in=ids))
        if len(vouchers) != len(set(map(str, ids))):
            raise ActionRefused("One or more selected vouchers could not be found.")
        return vouchers

    @action(detail=False, methods=['get'], url_path='to-raise')
    def to_raise(self, request):
        """Approved invoices waiting for their payment voucher (AP Officers)."""
        return Response([
            {'invoice_id': inv.pk, 'invoice_number': inv.invoice_number, 'vendor_invoice_number': inv.vendor_invoice_number,
             'vendor': inv.vendor.name if inv.vendor_id else None, 'facility': inv.facility.name if inv.facility_id else None,
             'description': inv.work_order.description if inv.work_order_id else '', 'total': str(inv.total_amount),
             'approved_at': inv.updated_at}
            for inv in stage5.to_raise(request.user)
        ])

    @action(detail=False, methods=['post'], url_path='flow-start')
    def flow_start(self, request):
        invoice = get_object_or_404(Invoice, pk=request.data.get('invoice'))
        try:
            voucher = stage5.start(invoice, request.user)
        except ActionRefused as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(voucher_flow_data(voucher, request.user), status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='flow-details')
    def flow_details(self, request, pk=None):
        return self._call(request, stage5.save_details, wht_rate=request.data.get('wht_rate'),
                          payment_method=request.data.get('payment_method'))

    @action(detail=True, methods=['post'], url_path='flow-submit')
    def flow_submit(self, request, pk=None):
        return self._call(request, stage5.submit)

    @action(detail=True, methods=['post'], url_path='flow-review')
    def flow_review(self, request, pk=None):
        return self._call(request, stage5.review, request.data.get('signature', ''), request.data.get('note', ''))

    @action(detail=True, methods=['post'], url_path='flow-return')
    def flow_return(self, request, pk=None):
        return self._call(request, stage5.return_voucher, request.data.get('reason', ''))

    @action(detail=True, methods=['post'], url_path='flow-approve')
    def flow_approve(self, request, pk=None):
        return self._call(request, stage5.approve, request.data.get('signature', ''))

    @action(detail=True, methods=['post'], url_path='payment-failed')
    def payment_failed(self, request, pk=None):
        return self._call(request, stage5.payment_failed, request.data.get('reason', ''))

    @action(detail=False, methods=['get'], url_path='to-pay')
    def to_pay(self, request):
        """Approved vouchers waiting to be paid, for the Pay and confirm screen."""
        return Response([{**_row(v), 'my_actions': stage5.available_actions(v, request.user),
                          'receipts': v.attachments.count()} for v in stage5.to_pay(request.user)])

    @action(detail=False, methods=['post'], url_path='attach-receipt')
    def attach_receipt(self, request):
        try:
            stage5.attach_receipt(self._selected(request), request.user,
                                  request.FILES.getlist('file') or request.FILES.getlist('files'))
        except ActionRefused as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'message': 'Receipt attached.'})

    @action(detail=False, methods=['post'], url_path='confirm-paid')
    def confirm_paid(self, request):
        try:
            vouchers = self._selected(request)
            stage5.confirm_paid(vouchers, request.user, payment_date=request.data.get('payment_date'),
                                bank_reference=request.data.get('bank_reference', ''))
        except ActionRefused as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'message': f"{len(vouchers)} payment(s) confirmed.", 'paid': [v.voucher_number for v in vouchers]})


class WithholdingTaxRateViewSet(viewsets.ModelViewSet):
    """Finance's withholding tax rates. Everyone on the finance side reads them; Finance keeps them."""
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']
    pagination_class = None

    def get_queryset(self):
        qs = WithholdingTaxRate.objects.all()
        return qs if self.request.query_params.get('all') else qs.filter(is_active=True)

    def _data(self, rate):
        return {'id': rate.pk, 'name': rate.name, 'rate': str(rate.rate), 'is_active': rate.is_active, 'label': str(rate)}

    def list(self, request, *args, **kwargs):
        if request.user.roles not in FINANCE_SIDE:
            return Response([])
        return Response([self._data(r) for r in self.get_queryset()])

    def retrieve(self, request, *args, **kwargs):
        return Response(self._data(get_object_or_404(WithholdingTaxRate, pk=kwargs['pk'])))

    def _save(self, request, rate):
        if request.user.roles not in RATE_KEEPERS:
            return Response({'error': "Only the Head of Finance & Treasury keeps the withholding tax rates."},
                            status=status.HTTP_403_FORBIDDEN)
        data = request.data
        if 'name' in data:
            rate.name = (data.get('name') or '').strip()
        if 'rate' in data:
            rate.rate = data.get('rate')
        if 'is_active' in data:
            rate.is_active = str(data.get('is_active')).lower() in ('true', '1', 'yes')
        try:
            value = Decimal(str(rate.rate))
        except Exception:
            return Response({'error': "The rate must be a number, e.g. 5."}, status=status.HTTP_400_BAD_REQUEST)
        if not rate.name or not (0 <= value <= 100):
            return Response({'error': "Give the rate a name and a percent between 0 and 100."},
                            status=status.HTTP_400_BAD_REQUEST)
        if WithholdingTaxRate.objects.filter(name__iexact=rate.name).exclude(pk=rate.pk).exists():
            return Response({'error': "A rate with this name already exists."}, status=status.HTTP_400_BAD_REQUEST)
        rate.rate = value
        rate.save()
        return Response(self._data(rate), status=status.HTTP_201_CREATED)

    def create(self, request, *args, **kwargs):
        return self._save(request, WithholdingTaxRate())

    def partial_update(self, request, *args, **kwargs):
        rate = get_object_or_404(WithholdingTaxRate, pk=kwargs['pk'])
        response = self._save(request, rate)
        if response.status_code == status.HTTP_201_CREATED:
            response.status_code = status.HTTP_200_OK
        return response
