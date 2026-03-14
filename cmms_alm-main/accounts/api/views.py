from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.hashers import make_password
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from cmms_instanta.permissions import RoleBasedPermissionMixin

from accounts.models import (
    User, Personnel, Vendor, Client, Category,
    Subcategory, Department, BankAccount, UnitOfMeasurement, 
    Onboarding, 
)
from .serializers import (
    UserSerializer, PersonnelSerializer, VendorSerializer,
    ClientSerializer, CategorySerializer, SubcategorySerializer,
    BankAccountSerializer, UnitOfMeasurementSerializer, 
    SimpleUserSerializer, DepartmentSerializer,
    OnboardingRetrieveSerializer, OnboardingCompleteSerializer
)

class OnboardingViewSet(viewsets.ViewSet):
    lookup_field = "token"

    @action(detail=True, methods=['get'], url_path='')
    def retrieve_onboarding(self, request, token=None):
        """
        GET /onboarding/{token}/retrieve_onboarding/
        """
        try:
            onboarding = Onboarding.objects.get(token=token, is_onboarded=False)
            if hasattr(onboarding, 'is_expired') and onboarding.is_expired():
                return Response({'error': 'Token has expired'}, status=400)
            serializer = OnboardingRetrieveSerializer(onboarding.user)
            return Response(serializer.data)
        except Onboarding.DoesNotExist:
            return Response({'error': 'Invalid or expired token.'}, status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        operation_description="Complete onboarding with password",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'password': openapi.Schema(type=openapi.TYPE_STRING, description='User\'s password', example='your_secure_password123'),
                'confirm_password': openapi.Schema(type=openapi.TYPE_STRING, description='Confirm the password', example='your_secure_password123')
            },
            required=['password', 'confirm_password']
        ),
        responses={
            200: openapi.Response('Success', schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={'message': openapi.Schema(type=openapi.TYPE_STRING)},
                example={'message': 'Password set successfully. You can now log in.'}
            )),
            400: openapi.Response('Validation Error', schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'password': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING)),
                    'confirm_password': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING))
                },
                example={'password': ['This field is required.'], 'confirm_password': ['This field is required.']}
            )),
            404: openapi.Response('Not Found', schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={'error': openapi.Schema(type=openapi.TYPE_STRING)},
                example={'error': 'Invalid or expired token.'}
            ))
        }
    )
    @action(detail=True, methods=['post'], url_path='complete')
    def complete_onboarding(self, request, token=None):
        """
        POST /onboarding/{token}/complete/
        """
        serializer = OnboardingCompleteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            onboarding = Onboarding.objects.get(token=token, is_onboarded=False)
            if hasattr(onboarding, 'is_expired') and onboarding.is_expired():
                return Response({'error': 'Token has expired'}, status=400)

            user = onboarding.user
            user.is_active = True
            user.password = make_password(serializer.validated_data['password'])
            user.save()

            onboarding.is_onboarded = True
            onboarding.save()

            return Response({'message': 'Password set successfully. You can now log in.'})
        except Onboarding.DoesNotExist:
            return Response({'error': 'Invalid or expired token.'}, status=status.HTTP_404_NOT_FOUND)
        
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("-id")
    permission_classes = [AllowAny]
    lookup_field = 'slug'

    def get_serializer_class(self):
        if self.action == 'list':
            return SimpleUserSerializer
        return UserSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.save()
        response_data = self.get_serializer(user).data

        # Include email_sent from serializer if available
        email_sent = getattr(serializer, 'email_sent', False)
        response_data['email_sent'] = email_sent

        return Response(response_data, status=status.HTTP_201_CREATED)

"""
Have another view that takes the token, validate the token and helps you change the password. Also when the password is changed, make is_onboarded=True
"""

class PersonnelViewSet(viewsets.ModelViewSet):
    queryset = Personnel.objects.all().order_by('-id')
    serializer_class = PersonnelSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'slug'

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class VendorViewSet(viewsets.ModelViewSet):
    queryset = Vendor.objects.all().order_by('-id')
    serializer_class = VendorSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'slug'

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all().order_by('-id')
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'slug'

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all().order_by('-id')
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['get'], url_path='subcategories')
    def list_subcategories(self, request, pk=None):
        category = self.get_object()
        subs = category.subcategory_set.all()
        serializer = SubcategorySerializer(subs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='subcategories')
    def create_subcategory(self, request, pk=None):
        category = self.get_object()
        data = request.data.copy()
        data['category'] = category.id

        serializer = SubcategorySerializer(data=data)
        if serializer.is_valid():
            serializer.save(owner=self.request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
class SubcategoryViewSet(viewsets.ModelViewSet):
    queryset = Subcategory.objects.all().order_by('-id')
    serializer_class = SubcategorySerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class BankAccountViewSet(viewsets.ModelViewSet):
    queryset = BankAccount.objects.all().order_by('-id')
    serializer_class = BankAccountSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'slug'

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all().order_by('-id')
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class UnitOfMeasurementViewSet(viewsets.ModelViewSet):
    queryset = UnitOfMeasurement.objects.all().order_by('-id')
    serializer_class = UnitOfMeasurementSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'code'

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

