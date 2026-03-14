from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from work.models import WorkRequest, PaymentItem, Comment, PaymentRequisition, PPM, WorkOrder, WorkOrderCompletion
from utils.models import FileAttachment

from accounts.api.serializers import (
    CategorySerializer, SubcategorySerializer,  UserSerializer, VendorSerializer
)
from facility.api.serializers import FacilitySerializer
from asset_inventory.api.serializers import (AssetSerializer, 
                                             DepartmentSerializer, AssetSubCategorySerializer,
                                             AssetCategorySerializer)
from utils.serializers import FileAttachmentSerializer


class WorkRequestSerializer(serializers.ModelSerializer):
    requester_detail = UserSerializer(source='requester', read_only=True)
    request_to_detail = UserSerializer(source='request_to', many=True, read_only=True)
    category_detail = AssetCategorySerializer(source='category', read_only=True)
    subcategory_detail = AssetSubCategorySerializer(source='subcategory', read_only=True)
    facility_detail = FacilitySerializer(source='facility', read_only=True)
    asset_detail = AssetSerializer(source='asset', read_only=True)
    department_detail = DepartmentSerializer(source='department', read_only=True)

    # Upload fields
    resources = serializers.ListField(child=serializers.FileField(), write_only=True, required=False)
    resources_data = FileAttachmentSerializer(many=True, read_only=True, source='resources')

    class Meta:
        model = WorkRequest
        fields = '__all__'
        read_only_fields = ['id', 'slug', 'work_request_number', 'resources_data', 'requester_detail', 'requester', 
                            'request_to_detail', 'category_detail', 'subcategory_detail', 
                            'department_detail', 'facility_detail', 'apartment_detail', 'asset_detail', 'resources_data', 'owner'] 

    def create(self, validated_data):
        resource_uploads = validated_data.pop('resources', [])
        request_to_users = validated_data.pop('request_to', [])

        instance = WorkRequest.objects.create(**validated_data)

        if request_to_users:
            instance.request_to.set(request_to_users)

        # self._attach_files(instance, file_uploads, 'work_request_files')
        self._attach_files(instance, resource_uploads, 'work_request_resources')

        # Check for approval status and create work order
        if instance.approval_status == 'Approved':
            self._create_work_order_from_request(instance)

        return instance

    def update(self, instance, validated_data):
        resource_uploads = validated_data.pop('resources', [])
        request_to_users = validated_data.pop('request_to', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if request_to_users is not None:
            instance.request_to.set(request_to_users)

        self._attach_files(instance, resource_uploads, 'work_request_resources')

        # Create work order on approval
        if instance.approval_status == 'Approved':
            self._create_work_order_from_request(instance)

        return instance

    def _attach_files(self, instance, file_list, relation_name):
        content_type = ContentType.objects.get_for_model(instance)
        for file in file_list:
            FileAttachment.objects.create(
                content_type=content_type,
                object_id=instance.id,
                file=file
            )

    def _create_work_order_from_request(self, work_request):
        from work.models import WorkOrder

        work_order, created = WorkOrder.objects.get_or_create(
            title=f"Work Order from Request #{work_request.work_request_number}",
            defaults={
                'type': work_request.type,
                'facility': work_request.facility,
                'category': work_request.category,
                'subcategory': work_request.subcategory,
                'department': work_request.department,
                'priority': work_request.priority,
                'description': work_request.description,
                'requester': work_request.requester,
                'request_to': work_request.owner,
                'approval_status': work_request.approval_status,
                'currency': work_request.currency,
                'add_discount': work_request.add_discount,
                'exclude_management_fee': work_request.exclude_management_fee,
                'require_mobilization_fee': work_request.require_mobilization_fee,
                'follow_up_notes': work_request.follow_up_notes,
                'invoice_no': work_request.invoice_no,
                'payment_requisition': work_request.payment_requisition,
                'apartment': work_request.apartment,
                'asset': work_request.asset,
                'owner': work_request.owner,
            }
        )

        if created:
            for attachment in work_request.files.all():
                work_order.files.add(attachment)

        return work_order
    
    
class WorkOrderSerializer(serializers.ModelSerializer):
    requester_detail = UserSerializer(source='requester', read_only=True)
    request_to_detail = UserSerializer(source='request_to', read_only=True)
    category_detail = CategorySerializer(source='category', read_only=True)
    subcategory_detail = SubcategorySerializer(source='subcategory', read_only=True)
    facility_detail = FacilitySerializer(source='facility', read_only=True)
    asset_detail = AssetSerializer(source='asset', read_only=True)

    resources = serializers.ListField(child=serializers.FileField(), write_only=True, required=False)
    resources_data = FileAttachmentSerializer(many=True, read_only=True, source='resources')

    class Meta:
        model = WorkOrder
        fields = '__all__'
        read_only_fields = ['id', 'slug', 'work_order_number', 'resources_data', 'owner', 'requester_detail', 'requester', 
                            'request_to_detail', 'category_detail', 'subcategory_detail', 'department_detail', 'facility_detail', 'apartment_detail', 'asset_detail', 'resources_data']

    def create(self, validated_data):
        resource_uploads = validated_data.pop('resources', [])
        instance = WorkOrder.objects.create(**validated_data)
        self._attach_files(instance, resource_uploads, 'work_order_resources')
        return instance

    def update(self, instance, validated_data):
        resource_uploads = validated_data.pop('resources', [])
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        self._attach_files(instance, resource_uploads, 'work_order_resources')
        return instance

    def _attach_files(self, instance, file_list, relation_name):
        content_type = ContentType.objects.get_for_model(instance)
        for file in file_list:
            FileAttachment.objects.create(
                content_type=content_type,
                object_id=instance.id,
                file=file
            )
            
            
            
class PaymentItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentItem
        fields = '__all__'


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = '__all__'


class PaymentRequisitionSerializer(serializers.ModelSerializer):
    pay_to_detail = VendorSerializer(source='pay_to', read_only=True)
    request_to_detail = UserSerializer(source='request_to', many=True, read_only=True)
    work_orders_detail = WorkOrderSerializer(source='work_orders', many=True, read_only=True)
    items_detail = PaymentItemSerializer(source='items', many=True, read_only=True)
    attachment_data = FileAttachmentSerializer(source='attachment', many=True, read_only=True)

    class Meta:
        model = PaymentRequisition
        fields = '__all__'
        read_only_fields = ['id', 'requisition_number', 'attachment_data']
        
        
class PPMSerializer(serializers.ModelSerializer):
    category_detail = CategorySerializer(source='category', read_only=True)
    subcategory_detail = SubcategorySerializer(source='subcategory', read_only=True)
    assets_detail = AssetSerializer(source='assets', many=True, read_only=True)
    facilities_detail = FacilitySerializer(source='facilities', many=True, read_only=True)
    items_detail = PaymentItemSerializer(source='items', many=True, read_only=True)

    class Meta:
        model = PPM
        fields = '__all__'
        read_only_fields = ['id']


class WorkOrderCompletionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkOrderCompletion
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
