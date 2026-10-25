"""
Approval Matrix API (Super Admin only).

  GET   approval-matrix/                      every facility, live or not, and what is missing
  GET   approval-matrix/<facility_id>/        one facility's slots, chain and problems
  PATCH approval-matrix/<facility_id>/        set the facility's named signers
  GET   approval-matrix/<facility_id>/candidates/   who may be each named signer
  POST  approval-matrix/<facility_id>/go-live/      switch the facility on (blocked while anything is missing)
  POST  approval-matrix/<facility_id>/switch-off/
  GET   company-approvers/   PATCH company-approvers/
"""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from facility.models import Facility
from utils.csv_import import is_super_admin
from work.models import ApprovalMatrix, CompanyApprovers
from work.models.approval_matrix import (
    COMPANY_SLOTS, FACILITY_SLOTS, SLOT_LABELS, TEAM_SLOTS, slot_error, team_members,
)

User = get_user_model()


class IsSuperAdmin(BasePermission):
    message = "Only a Super Admin can view or change the Approval Matrix."

    def has_permission(self, request, view):
        return is_super_admin(request.user)


def person(user):
    if user is None:
        return None
    return {'id': user.id, 'name': user.name.strip() or user.email, 'email': user.email, 'roles': user.roles}


def matrix_for(facility):
    """The facility's matrix row, or an unsaved one so reading never writes."""
    try:
        return facility.approval_matrix
    except ApprovalMatrix.DoesNotExist:
        return ApprovalMatrix(facility=facility)


def matrix_data(matrix):
    facility = matrix.facility
    company = CompanyApprovers.current()
    slots = {slot: person(getattr(matrix, slot)) for slot in FACILITY_SLOTS}
    slots.update({slot: person(getattr(company, slot)) for slot in COMPANY_SLOTS})
    return {
        'facility': {'id': facility.id, 'name': facility.name,
                     'client': facility.client.name if facility.client_id else None},
        'slots': slots,
        'slot_labels': SLOT_LABELS,
        'company_wide_slots': list(COMPANY_SLOTS),
        'teams': {
            slot: {'role': role, 'scope': scope, 'people': team_members(slot, facility).count()}
            for slot, (role, scope) in TEAM_SLOTS.items()
        },
        'chain': matrix.chain(),
        'problems': matrix.problems(),
        'is_live': matrix.is_live,
        'went_live_at': matrix.went_live_at,
        'went_live_by': person(matrix.went_live_by),
    }


class SlotsSerializer(serializers.Serializer):
    """Validates any of the given slots; each must hold a user who may fill it."""

    def __init__(self, *args, slots, facility=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.facility = facility
        for slot in slots:
            self.fields[slot] = serializers.PrimaryKeyRelatedField(
                queryset=User.objects.all(), allow_null=True, required=False,
            )

    def validate(self, data):
        errors = {
            slot: error for slot, user in data.items()
            if user is not None and (error := slot_error(slot, user, self.facility))
        }
        if errors:
            raise serializers.ValidationError(errors)
        return data


class ApprovalMatrixViewSet(viewsets.ViewSet):
    permission_classes = [IsSuperAdmin]
    lookup_field = 'facility_id'

    def list(self, request):
        rows = []
        for facility in Facility.objects.select_related('client').order_by('name'):
            matrix = matrix_for(facility)
            problems = matrix.problems()
            rows.append({
                'facility': {'id': facility.id, 'name': facility.name,
                             'client': facility.client.name if facility.client_id else None},
                'is_live': matrix.is_live,
                'ready': not problems,
                'problem_count': len(problems),
            })
        return Response(rows)

    def retrieve(self, request, facility_id=None):
        facility = get_object_or_404(Facility, pk=facility_id)
        return Response(matrix_data(matrix_for(facility)))

    def partial_update(self, request, facility_id=None):
        facility = get_object_or_404(Facility, pk=facility_id)
        serializer = SlotsSerializer(data=request.data, slots=FACILITY_SLOTS, facility=facility)
        serializer.is_valid(raise_exception=True)
        matrix = matrix_for(facility)
        for slot, user in serializer.validated_data.items():
            setattr(matrix, slot, user)
        if matrix.is_live and matrix.problems():
            return Response(
                {'error': "A live facility must keep every named signer. Choose a replacement or switch it off first.",
                 'problems': matrix.problems()},
                status=status.HTTP_400_BAD_REQUEST,
            )
        matrix.save()
        return Response(matrix_data(matrix))

    update = partial_update

    @action(detail=True, methods=['get'])
    def candidates(self, request, facility_id=None):
        """Active users who may be each named signer here (facility and company-wide)."""
        facility = get_object_or_404(Facility, pk=facility_id)
        data = {}
        for slot, role in {**FACILITY_SLOTS, **COMPANY_SLOTS}.items():
            scope = facility if slot in FACILITY_SLOTS else None
            users = User.objects.filter(roles=role, is_active=True).order_by('first_name', 'last_name')
            data[slot] = [person(u) for u in users if slot_error(slot, u, scope) is None]
        return Response(data)

    @action(detail=True, methods=['post'], url_path='go-live')
    def go_live(self, request, facility_id=None):
        facility = get_object_or_404(Facility, pk=facility_id)
        matrix = matrix_for(facility)
        if matrix.pk is None:
            matrix.save()
        try:
            matrix.go_live(request.user)
        except DjangoValidationError as exc:
            return Response(
                {'error': "This facility cannot go live yet.", 'problems': exc.messages},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(matrix_data(matrix))

    @action(detail=True, methods=['post'], url_path='switch-off')
    def switch_off(self, request, facility_id=None):
        facility = get_object_or_404(Facility, pk=facility_id)
        matrix = matrix_for(facility)
        if matrix.pk is not None:
            matrix.switch_off()
        return Response(matrix_data(matrix))


class CompanyApproversView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        company = CompanyApprovers.current()
        return Response({
            'slots': {slot: person(getattr(company, slot)) for slot in COMPANY_SLOTS},
            'slot_labels': {slot: SLOT_LABELS[slot] for slot in COMPANY_SLOTS},
            'problems': company.problems(),
        })

    def patch(self, request):
        serializer = SlotsSerializer(data=request.data, slots=COMPANY_SLOTS)
        serializer.is_valid(raise_exception=True)
        company = CompanyApprovers.current()
        for slot, user in serializer.validated_data.items():
            setattr(company, slot, user)
        if company.problems():
            live = ApprovalMatrix.objects.filter(is_live=True).select_related('facility')
            if live.exists():
                return Response(
                    {'error': "Live facilities need the Head of Finance & Treasury. Choose a replacement or switch them off first.",
                     'problems': company.problems(),
                     'live_facilities': [m.facility.name for m in live]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        company.save()
        return self.get(request)

    put = patch
