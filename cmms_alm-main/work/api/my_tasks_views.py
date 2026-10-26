"""
My Tasks: everything waiting on the person, across the five-stage flow.
Stage 1 (Work Requests) for now; later stages add their own rows.
"""
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from work.models import completion_flow as stage3
from work.models import invoice_flow as stage4
from work.models import payment_flow as stage5
from work.models import work_order_flow as stage2
from work.models import work_request_flow as stage1


def _who(user):
    return (user.name.strip() or user.email) if user else None


def _timing(timing):
    return {'state': timing.get('state'), 'due_at': timing.get('due_at')} if timing else None


class MyTasksView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rows = []
        for task in stage1.my_tasks(request.user):
            wr = task['request']
            timing = task['timing'] or {}
            rows.append({
                'kind': 'work_request',
                'id': wr.id,
                'slug': wr.slug,
                'number': wr.work_request_number,
                'facility': wr.facility.name if wr.facility_id else None,
                'description': wr.description,
                'priority': wr.priority,
                'status': wr.approval_status,
                'step': task['step'],
                'step_label': stage1.STEP_LABELS[task['step']],
                'on_behalf_of': (task['on_behalf_of'].name.strip() or task['on_behalf_of'].email)
                                if task['on_behalf_of'] else None,
                'waiting_since': wr.updated_at,
                'timing': {'state': timing.get('state'), 'due_at': timing.get('due_at')} if timing else None,
            })
        for task in stage2.my_tasks(request.user):
            if task['kind'] == 'work_order_to_raise':
                wr = task['request']
                rows.append({
                    'kind': 'work_order_to_raise', 'id': wr.id, 'slug': wr.slug, 'number': wr.work_request_number,
                    'facility': wr.facility.name if wr.facility_id else None, 'description': wr.description,
                    'priority': wr.priority, 'status': wr.approval_status, 'step': 'procurement',
                    'step_label': stage2.STEP_LABELS['procurement'], 'on_behalf_of': None,
                    'waiting_since': wr.fully_approved_at, 'timing': _timing(task['timing']),
                })
                continue
            wo = task['order']
            rows.append({
                'kind': 'work_order', 'id': wo.id, 'slug': wo.slug, 'number': wo.work_order_number,
                'facility': wo.facility.name if wo.facility_id else None, 'description': wo.description,
                'priority': wo.priority, 'status': wo.approval_status, 'step': task['step'],
                'step_label': stage2.STEP_LABELS.get(task['step'], task['step']),
                'on_behalf_of': _who(task['on_behalf_of']),
                'waiting_since': wo.updated_at, 'timing': _timing(task['timing']),
            })
        for task in stage3.my_tasks(request.user):
            if task['kind'] == 'wcc_to_raise':
                wo = task['order']
                rows.append({
                    'kind': 'wcc_to_raise', 'id': wo.id, 'slug': wo.slug, 'number': wo.work_order_number,
                    'facility': wo.facility.name if wo.facility_id else None, 'description': wo.description,
                    'priority': wo.priority, 'status': wo.approval_status, 'step': 'requester',
                    'step_label': stage3.STEP_LABELS['requester'], 'on_behalf_of': None,
                    'waiting_since': wo.updated_at, 'timing': None,
                })
                continue
            wcc = task['completion']
            rows.append({
                'kind': 'wcc', 'id': wcc.id, 'slug': str(wcc.id), 'number': f"WCC-{wcc.wcc_number}",
                'facility': wcc.work_order.facility.name if wcc.work_order.facility_id else None,
                'description': wcc.work_order.description, 'priority': wcc.work_order.priority,
                'status': wcc.approval_status, 'step': task['step'],
                'step_label': stage3.STEP_LABELS.get(task['step'], task['step']),
                'on_behalf_of': _who(task['on_behalf_of']),
                'waiting_since': wcc.updated_at, 'timing': _timing(task['timing']),
            })
        for task in stage4.my_tasks(request.user):
            if task['kind'] == 'invoice_to_raise':
                wcc = task['completion']
                rows.append({
                    'kind': 'invoice_to_raise', 'id': wcc.id, 'slug': str(wcc.id), 'number': f"WCC-{wcc.wcc_number}",
                    'facility': wcc.work_order.facility.name if wcc.work_order.facility_id else None,
                    'description': wcc.work_order.description, 'priority': wcc.work_order.priority,
                    'status': wcc.approval_status, 'step': task['step'],
                    'step_label': stage4.STEP_LABELS[task['step']], 'on_behalf_of': None,
                    'waiting_since': wcc.updated_at, 'timing': None,
                })
                continue
            inv = task['invoice']
            rows.append({
                'kind': 'invoice', 'id': inv.id, 'slug': str(inv.id), 'number': inv.invoice_number,
                'facility': inv.facility.name if inv.facility_id else None,
                'description': inv.work_order.description if inv.work_order_id else '', 'priority': None,
                'status': inv.approval_status, 'step': task['step'],
                'step_label': stage4.STEP_LABELS.get(task['step'], task['step']),
                'on_behalf_of': _who(task['on_behalf_of']),
                'waiting_since': inv.updated_at, 'timing': _timing(task['timing']),
            })
        for task in stage5.my_tasks(request.user):
            if task['kind'] == 'voucher_to_raise':
                inv = task['invoice']
                rows.append({
                    'kind': 'voucher_to_raise', 'id': inv.id, 'slug': str(inv.id), 'number': inv.invoice_number,
                    'facility': inv.facility.name if inv.facility_id else None,
                    'description': inv.work_order.description if inv.work_order_id else '', 'priority': None,
                    'status': inv.approval_status, 'step': 'ap_officer', 'step_label': stage5.STEP_LABELS['ap_officer'],
                    'on_behalf_of': None, 'waiting_since': inv.updated_at, 'timing': None,
                })
                continue
            v = task['voucher']
            rows.append({
                'kind': 'voucher', 'id': v.id, 'slug': str(v.id), 'number': v.voucher_number,
                'facility': v.facility.name if v.facility_id else None,
                'description': v.work_order.description, 'priority': None,
                'status': v.status, 'step': task['step'],
                'step_label': stage5.STEP_LABELS.get(task['step'], task['step']),
                'on_behalf_of': _who(task['on_behalf_of']),
                'waiting_since': v.updated_at, 'timing': _timing(task['timing']),
            })
        return Response(rows)
