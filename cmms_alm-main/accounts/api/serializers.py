import uuid
import smtplib
import socket
from rest_framework import serializers
from accounts.models import (User, 
                             Onboarding
                             )
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.conf import settings
from django.utils.translation import get_language
from django.contrib.contenttypes.models import ContentType
from mail_templated import send_mail
from mail_templated import EmailMessage

from utils.models import FileAttachment
from facility.models import Facility, Building, Apartment
from accounts.models import (Client, Category, Department, Personnel, Vendor, 
                             Contact, Subcategory, BankAccount, UnitOfMeasurement)
from asset_inventory.models import Warehouse, Apartment
from facility.api.serializers import FacilitySerializer, BuildingSerializer

from utils.mixin import TranslatedSerializerMixin
from utils.translation_mixin import TranslatableFieldMixin


class OnboardingRetrieveSerializer(serializers.Serializer):
    first_name = serializers.CharField()

class OnboardingCompleteSerializer(serializers.Serializer):
    password = serializers.CharField(
        write_only=True,
        help_text="User's password",
    )
    confirm_password = serializers.CharField(
        write_only=True,
        help_text="Confirm the password",
    )

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")
        return data

class PersonnelSerializer(serializers.ModelSerializer):
    first_name = serializers.ReadOnlyField(source='user.first_name')
    last_name = serializers.ReadOnlyField(source='user.last_name')
    avatar_url = serializers.ReadOnlyField()
    documents_data = serializers.SerializerMethodField(read_only=True)
    # Accept file uploads through a separate field
    documents = serializers.ListField(
        child=serializers.FileField(), write_only=True, required=False
    )

    categories = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), many=True, required=False
    )

    class Meta:
        model = Personnel
        fields = [
            'id', 'slug', 'user', 'staff_number', 'facility', 'email',
            'phone_number', 'avatar', 'status',
            'access_to_all_categories', 'categories', 'documents', 'documents_data',
            'first_name', 'last_name', 'avatar_url',
        ]
        read_only_fields = ['slug', 'first_name', 'last_name', 'avatar_url']
        
    def get_documents_data(self, obj):
        return [
            {
                "id": doc.id,
                "file": doc.file.url,
                "name": doc.file.name.split('/')[-1],
                "uploaded_at": doc.uploaded_at if hasattr(doc, "uploaded_at") else None
            }
            for doc in obj.documents.all()
        ]

    def create(self, validated_data):
        document_files = validated_data.pop('documents', [])
        categories = validated_data.pop('categories', [])
        personnel = Personnel.objects.create(**validated_data)

        # Set categories
        if personnel.access_to_all_categories:
            personnel.categories.set(Category.objects.all())
        else:
            personnel.categories.set(categories)

        # Save files as FileAttachment
        if document_files:
            content_type = ContentType.objects.get_for_model(Personnel)
            for file in document_files:
                attachment = FileAttachment.objects.create(
                    content_type=content_type,
                    object_id=personnel.id,
                    file=file
                )
                personnel.documents.add(attachment)

        return personnel

    def update(self, instance, validated_data):
        document_files = validated_data.pop('documents', [])
        categories = validated_data.pop('categories', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        # Set categories
        if instance.access_to_all_categories:
            instance.categories.set(Category.objects.all())
        elif categories is not None:
            instance.categories.set(categories)

        # Add any new documents
        if document_files:
            content_type = ContentType.objects.get_for_model(Personnel)
            for file in document_files:
                attachment = FileAttachment.objects.create(
                    content_type=content_type,
                    object_id=instance.id,
                    file=file
                )
                instance.documents.add(attachment)

        return instance
    

class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = [
            'id', 'slug', 'name', 'type', 'phone', 'email',
            'account_name', 'bank', 'account_number', 'currency', 'status'
        ]
        read_only_fields = ['slug']


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ['id', 'first_name', 'last_name', 'email', 'phone', 'status']

class ClientSerializer(serializers.ModelSerializer):
    contacts = ContactSerializer(many=True, write_only=True, required=False)
    contacts_data = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Client
        fields = [
            'id', 'slug', 'type', 'code', 'name', 'email', 'phone',
            'group', 'address', 'status',
            'contacts', 'contacts_data',
        ]
        read_only_fields = ['slug', 'contacts_data']

    def create(self, validated_data):
        contacts_data = validated_data.pop('contacts', [])
        client = Client.objects.create(**validated_data)

        # Create and assign new contact instances
        contact_instances = [
            Contact.objects.create(**contact) for contact in contacts_data
        ]
        client.contacts.set(contact_instances)

        return client

    def update(self, instance, validated_data):
        contacts_data = validated_data.pop('contacts', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        # Update contacts if provided
        if contacts_data is not None:
            new_contacts = [Contact.objects.create(**c) for c in contacts_data]
            instance.contacts.set(new_contacts)

        return instance

    def get_contacts_data(self, obj):
        return ContactSerializer(obj.contacts.all(), many=True).data
    

class SubcategorySerializer(TranslatableFieldMixin, serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    class Meta:
        model = Subcategory
        fields = [
            'id', 'category',
            'title', 
            'description', 
            'exclude_costing_limit', 'status'
        ]
        translatable_fields = ['title', 'description']
    

class CategorySerializer(TranslatableFieldMixin, serializers.ModelSerializer):
    subcategories = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Category
        fields = [
            'id', 'code',
            'title', 
            'description', 
            'problem_type', 
            'work_request_approved',
            'exclude_costing_limit', 'power', 'create_payment_requisition', 'status', 'subcategories'
        ]
        translatable_fields = ['title', 'description', 'problem_type']

    def get_subcategories(self, obj):
        subs = obj.subcategory_set.all()
        return SubcategorySerializer(subs, many=True).data
        
        
class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = [
            'id', 'slug', 'bank', 'account_name', 'account_number',
            'currency', 'address', 'details', 'status'
        ]
        read_only_fields = ['slug', 'id']
        
        
class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'code', 'name', 'email', 'phone', 'status']
        read_only_fields = ['id']
        ref_name = 'AccountDepartment'


class UnitOfMeasurementSerializer(TranslatableFieldMixin, serializers.ModelSerializer):
    class Meta:
        model = UnitOfMeasurement
        fields = ['id', 'code', 'description', 'symbol', 'type', 'status']
        read_only_fields = ['id']
        translatable_fields = ['description']



class SimpleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'user_id', 'slug', 'first_name', 'last_name', 'email', 'roles', 'status']


class UserSerializer(serializers.ModelSerializer):
    facility_detail = serializers.SerializerMethodField(read_only=True)
    buildings_detail = serializers.SerializerMethodField(read_only=True)
    # apartments_detail = serializers.SerializerMethodField(read_only=True)
    categories_detail = serializers.SerializerMethodField(read_only=True)
    warehouse_detail = serializers.SerializerMethodField(read_only=True)
    clients_detail = serializers.SerializerMethodField(read_only=True)
    supervisor_detail = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        # Explicitly list all fields and interleave _detail fields
        fields = [
            'id', 'user_id', 'first_name', 'last_name', 'slug', 'roles', 'email', 'phone',
            'designation', 'date_of_birth', 'gender', 'nationality', 'passport_number', 'address',
            'status', 'avatar', 'team_lead', 'generate_reports', 'approval_limit',
            'date_joined', 'last_login', 'is_verified', 'is_blocked', 'is_active',

            'access_to_all_facilities', 'facility', 'facility_detail',
            'access_to_all_buildings', 'buildings', 'buildings_detail',
            # 'access_to_all_apartments', 'apartments', 'apartments_detail',
            'access_to_all_categories', 'categories', 'categories_detail',
            'access_to_all_warehouses', 'warehouse', 'warehouse_detail',
            'access_to_all_clients', 'clients', 'clients_detail',

            'supervisor', 'supervisor_detail',
        ]
        read_only_fields = ['slug', 'facility_detail', 'buildings_detail', 'apartments_detail',
                            'categories_detail', 'warehouse_detail',  'clients_detail']

    def create(self, validated_data):
        m2m_fields = self.extract_m2m(validated_data)
        
        # Create user with a temporary password
        user = User(**validated_data)
        user.set_password("TempPassword123")
        user.save()

        # Create Onboarding instance
        token = str(uuid.uuid4())
        onboarding = Onboarding.objects.create(
            user=user,
            token=token,
            is_onboarded=False
        )

        self.set_m2m_fields(user, m2m_fields)

        # Send onboarding email
        email_sent = False  # Track email status
        try:
            socket.setdefaulttimeout(10)

            email = EmailMessage(
                template_name='email_template.tpl',
                context={
                    'first_name': user.first_name,
                    # 'url': settings.BASE_URL+"/accounts/api/onboarding/"+token+"/complete"
                    'url': "https://alpha-cmms.vercel.app/onboarding/"+token+"/complete"
                },
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
            )
            email.send()
            email_sent = True
            print("Email sent successfully")
        except Exception as e:
            # Catch all email-related errors including O365 authentication issues
            print(f"Failed to send email: {e}")
            email_sent = False
        finally:
            socket.setdefaulttimeout(None)

        self.email_sent = email_sent 
        return user
    
    def update(self, instance, validated_data):
        m2m_fields = self.extract_m2m(validated_data)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        self.set_m2m_fields(instance, m2m_fields)
        return instance


    def extract_m2m(self, validated_data):
        return {
            "facility": validated_data.pop("facility", []),
            "buildings": validated_data.pop("buildings", []),
            "apartments": validated_data.pop("apartments", []),
            "categories": validated_data.pop("categories", []),
            "warehouse": validated_data.pop("warehouse", []),
            "clients": validated_data.pop("clients", []),
        }

    def set_m2m_fields(self, user, m2m_data):
        M2M_MAPPING = [
            ("access_to_all_facilities", "facility", Facility),
            ("access_to_all_buildings", "buildings", Building),
            ("access_to_all_apartments", "apartments", Apartment),
            ("access_to_all_categories", "categories", Category),
            ("access_to_all_warehouses", "warehouse", Warehouse),
            ("access_to_all_clients", "clients", Client),
        ]
        for flag, field, model in M2M_MAPPING:
            if getattr(user, flag):
                getattr(user, field).set(model.objects.all())
            else:
                getattr(user, field).set(m2m_data.get(field, []))
        user.save()

    # Detail serializers
    def get_facility_detail(self, obj):
        return FacilitySerializer(obj.facility.all(), many=True).data

    def get_buildings_detail(self, obj):
        return BuildingSerializer(obj.buildings.all(), many=True).data

    def get_apartments_detail(self, obj):
        return ApartmentSerializer(obj.apartments.all(), many=True).data

    def get_categories_detail(self, obj):
        return CategorySerializer(obj.categories.all(), many=True).data

    def get_warehouse_detail(self, obj):
        from asset_inventory.api.serializers import WarehouseSerializer
        return WarehouseSerializer(obj.warehouse.all(), many=True).data

    def get_clients_detail(self, obj):
        return ClientSerializer(obj.clients.all(), many=True).data
    
    def get_supervisor_detail(self, obj):
        return SimpleUserSerializer(obj.supervisor).data if obj.supervisor else None
    


