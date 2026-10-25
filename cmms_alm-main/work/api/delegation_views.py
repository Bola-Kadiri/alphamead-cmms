"""
Cover while away API.

  GET   delegations/                 my covers (given and taken); Super Admin sees all
  POST  delegations/                 name a stand-in (a signer for themselves; Super Admin for anyone)
  POST  delegations/<id>/end/        end it early (the person or Super Admin)
  GET   delegations/stand-ins/?person=<id>   who may stand in
"""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from utils.csv_import import is_super_admin
from work.models import Delegation
from work.models.delegation import SIGNER_ROLES

User = get_user_model()


def person(user):
    if user is None:
        return None
    return {'id': user.id, 'name': user.name.strip() or user.email, 'email': user.email, 'roles': user.roles}


class DelegationSerializer(serializers.ModelSerializer):
    person = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False)
    stand_in = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    value_limit = serializers.DecimalField(max_digits=18, decimal_places=2, required=False, allow_null=True,
                                           coerce_to_string=True)
    status = serializers.CharField(read_only=True)

    class Meta:
        model = Delegation
        fields = ['id', 'person', 'stand_in', 'starts_at', 'ends_at', 'value_limit', 'reason', 'status',
                  'created_at', 'ended_early_at']
        read_only_fields = ['created_at', 'ended_early_at']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['person'] = person(instance.person)
        data['stand_in'] = person(instance.stand_in)
        data['ended_early_by'] = person(instance.ended_early_by)
        return data


class DelegationViewSet(viewsets.ModelViewSet):
    serializer_class = DelegationSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']
    pagination_class = None  # a person only ever has a handful of covers; the screen shows them all

    def get_queryset(self):
        qs = Delegation.objects.select_related('person', 'stand_in', 'ended_early_by')
        user = self.request.user
        if is_super_admin(user):
            return qs
        return qs.filter(Q(person=user) | Q(stand_in=user))

    def create(self, request, *args, **kwargs):
        user = request.user
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target = serializer.validated_data.get('person') or user
        if target.pk != user.pk and not is_super_admin(user):
            return Response({'error': "You can only arrange cover for yourself."}, status=status.HTTP_403_FORBIDDEN)
        if target.roles not in SIGNER_ROLES:
            return Response({'error': "Only signers (APPROVER, CLIENT, HEAD OF FINANCE & TREASURY) need cover."},
                            status=status.HTTP_400_BAD_REQUEST)
        delegation = Delegation(created_by=user, **{**serializer.validated_data, 'person': target})
        try:
            delegation.full_clean()
        except DjangoValidationError as exc:
            return Response(exc.message_dict, status=status.HTTP_400_BAD_REQUEST)
        delegation.save()
        return Response(self.get_serializer(delegation).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def end(self, request, pk=None):
        delegation = get_object_or_404(self.get_queryset(), pk=pk)
        if delegation.person_id != request.user.pk and not is_super_admin(request.user):
            return Response({'error': "Only the person covered or a Super Admin can end this cover."},
                            status=status.HTTP_403_FORBIDDEN)
        if delegation.status not in ('active', 'scheduled'):
            return Response({'error': "This cover has already ended."}, status=status.HTTP_400_BAD_REQUEST)
        delegation.end_early(request.user)
        return Response(self.get_serializer(delegation).data)

    @action(detail=False, methods=['get'], url_path='stand-ins')
    def stand_ins(self, request):
        """Active users who hold the same role as the person needing cover."""
        target = request.user
        if request.query_params.get('person') and is_super_admin(request.user):
            target = get_object_or_404(User, pk=request.query_params['person'])
        users = (User.objects.filter(roles=target.roles, is_active=True).exclude(pk=target.pk)
                 .order_by('first_name', 'last_name'))
        return Response([person(u) for u in users])
