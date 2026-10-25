"""
My Tasks: everything waiting on the person, across the five-stage flow.
Stage 1 (Work Requests) for now; later stages add their own rows.
"""
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

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
        return Response(rows)
