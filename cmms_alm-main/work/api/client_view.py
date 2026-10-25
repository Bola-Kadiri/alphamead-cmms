"""
What a CLIENT user may see on work requests, work orders and WCCs.

Clients see their facilities' work and what Alpha Mead charges them (client
price). They never see vendor cost, Alpha Mead's margin, quotation line items,
vendor / payee details (incl. bank details), PO / vendor invoice documents,
internal approval routing, internal remarks or staff contact details.

Applied in the serializers' to_representation, so nested data (e.g. the work
order inside a WCC) is masked too.
"""

def is_client_request(context):
    request = (context or {}).get('request')
    return getattr(getattr(request, 'user', None), 'roles', None) == 'CLIENT'


def _name_only(person):
    if not isinstance(person, dict):
        return person
    return {'first_name': person.get('first_name'), 'last_name': person.get('last_name')}


# Fields removed from every record type.
_INTERNAL_COMMON = {
    'request_to', 'request_to_detail', 'reviewers', 'reviewers_detail', 'approver', 'approver_detail',
    'reviewer_reason', 'approver_reason', 'digital_signature', 'follow_up', 'follow_up_notes',
    'technician', 'technician_detail', 'owner', 'add_discount', 'exclude_management_fee',
}

_WORK_REQUEST_HIDDEN = _INTERNAL_COMMON | {
    'total_cost_vendor', 'margin', 'quotation_items', 'cost',
    'vendor', 'vendor_detail', 'po_vendor', 'po_vendor_detail', 'po_amount', 'po_number',
    'po_document', 'vendor_invoice', 'invoice_no', 'cp_reason', 'require_mobilization_fee',
    'payment_requisition',
}

_WORK_ORDER_HIDDEN = _INTERNAL_COMMON | {
    'vendor', 'vendor_detail', 'payee', 'payee_detail', 'item_cost', 'invoice_no',
    'linked_payment_requisition', 'withholding_tax', 'remark', 'payment_requisition',
    'mobilization_fee_required', 'require_mobilization_fee', 'po_required', 'allow_resubmission',
}

_COMPLETION_HIDDEN = _INTERNAL_COMMON | {'reviewer_notes', 'approver_notes', 'is_reviewed'}


def mask_work_request(data):
    for field in _WORK_REQUEST_HIDDEN:
        data.pop(field, None)
    if 'requester_detail' in data:
        data['requester_detail'] = _name_only(data['requester_detail'])
    return data


def mask_work_order(data, instance):
    """`cost` becomes the client price: the source work request's client total, or
    the bill amount for a Raise Payment. Otherwise (e.g. PPM) it is not shown."""
    for field in _WORK_ORDER_HIDDEN:
        data.pop(field, None)
    if 'requester_detail' in data:
        data['requester_detail'] = _name_only(data['requester_detail'])

    source = getattr(instance, 'source_work_request', None)
    if source is not None:
        client_total = source.total_cost_client
        data['cost'] = str(client_total) if client_total is not None else None
        data['source_work_request_detail'] = {
            'id': source.id,
            'work_request_number': source.work_request_number,
            'total_cost_client': data['cost'],
        }
    elif instance.type == instance.RAISE_PAYMENT:
        data['source_work_request_detail'] = None  # cost = the bill amount, kept as is
    else:
        data['cost'] = None
        data['source_work_request_detail'] = None
    return data


def mask_completion(data):
    for field in _COMPLETION_HIDDEN:
        data.pop(field, None)
    return data
