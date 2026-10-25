"""
My Tasks: everything waiting on the person, across the five-stage flow.
Stage 1 (Work Requests) for now; later stages add their own rows.
"""
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from work.models import work_request_flow as stage1


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
        return Response(rows)
