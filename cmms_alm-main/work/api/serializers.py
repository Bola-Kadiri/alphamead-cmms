from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from work.models import WorkRequest, PaymentItem, Comment, PaymentRequisition, PPM, WorkOrder, WorkOrderCompletion, Invoice, InvoiceLineItem
from utils.models import FileAttachment

from accounts.api.serializers import (
    UserSerializer, VendorSerializer
)
from facility.api.serializers import FacilitySerializer
from asset_inventory.api.serializers import (AssetSerializer,
                                             DepartmentSerializer, AssetSubCategorySerializer,
                                             AssetCategorySerializer)
from utils.serializers import FileAttachmentSerializer


class WorkRequestSerializer(serializers.ModelSerializer):
    requester_detail = UserSerializer(source='requester', read_only=True)
    request_to_detail = UserSerializer(source='request_to', many=True, read_only=True)
    approver_detail = UserSerializer(source='approver', read_only=True)
    reviewers_detail = UserSerializer(source='reviewers', many=True, read_only=True)
    category_detail = AssetCategorySerializer(source='category', read_only=True)
    subcategory_detail = AssetSubCategorySerializer(source='subcategory', read_only=True)
    facility_detail = FacilitySerializer(source='facility', read_only=True)
    asset_detail = AssetSerializer(source='asset', read_only=True)
    department_detail = DepartmentSerializer(source='department', read_only=True)
    vendor_detail = VendorSerializer(source='vendor', read_only=True)
    po_vendor_detail = VendorSerializer(source='po_vendor', read_only=True)

    # Upload fields
    resources = serializers.ListField(child=serializers.FileField(), write_only=True, required=False)
    resources_data = FileAttachmentSerializer(many=True, read_only=True, source='resources')

    class Meta:
        model = WorkRequest
        fields = '__all__'
        read_only_fields = [
            'id', 'slug', 'work_request_number', 'owner', 'requester',
            # Detail expansions
            'requester_detail', 'request_to_detail', 'approver_detail', 'reviewers_detail',
            'category_detail', 'subcategory_detail', 'department_detail',
            'facility_detail', 'asset_detail', 'resources_data',
            'vendor_detail', 'po_vendor_detail',
            # Workflow state — managed exclusively by action endpoints
            'approval_status', 'is_locked', 'po_number', 'po_document', 'po_vendor', 'po_amount',
            'cp_reason', 'reviewer_reason', 'approver_reason',
            'digital_signature', 'fully_approved_at',
        ]

    def create(self, validated_data):
        resource_uploads = validated_data.pop('resources', [])
        request_to_users = validated_data.pop('request_to', [])
        reviewers = validated_data.pop('reviewers', [])

        with transaction.atomic():
            instance = WorkRequest.objects.create(**validated_data)
            if request_to_users:
                instance.request_to.set(request_to_users)
            if reviewers:
                instance.reviewers.set(reviewers)
            self._attach_files(instance, resource_uploads, 'work_request_resources')
        return instance

    def update(self, instance, validated_data):
        resource_uploads = validated_data.pop('resources', [])
        request_to_users = validated_data.pop('request_to', None)
        reviewers = validated_data.pop('reviewers', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if request_to_users is not None:
            instance.request_to.set(request_to_users)
        if reviewers is not None:
            instance.reviewers.set(reviewers)

        self._attach_files(instance, resource_uploads, 'work_request_resources')
        return instance

    def _attach_files(self, instance, file_list, relation_name):
        content_type = ContentType.objects.get_for_model(instance)
        for file in file_list:
            FileAttachment.objects.create(
                content_type=content_type,
                object_id=instance.id,
                file=file
            )


class WorkOrderSerializer(serializers.ModelSerializer):
    requester_detail = UserSerializer(source='requester', read_only=True)
    request_to_detail = UserSerializer(source='request_to', read_only=True)
    approver_detail = UserSerializer(source='approver', read_only=True)
    reviewers_detail = UserSerializer(source='reviewers', many=True, read_only=True)
    category_detail = AssetCategorySerializer(source='category', read_only=True)
    subcategory_detail = AssetSubCategorySerializer(source='subcategory', read_only=True)
    facility_detail = FacilitySerializer(source='facility', read_only=True)
    asset_detail = AssetSerializer(source='asset', read_only=True)

    resources = serializers.ListField(child=serializers.FileField(), write_only=True, required=False)
    resources_data = FileAttachmentSerializer(many=True, read_only=True, source='resources')
    source_work_request_detail = serializers.SerializerMethodField()

    def get_source_work_request_detail(self, obj):
        wr = obj.source_work_request
        if not wr:
            return None
        return {
            'id': wr.id,
            'work_request_number': wr.work_request_number,
            'po_number': wr.po_number,
            'po_document': wr.po_document.url if wr.po_document and wr.po_document.name else None,
        }

    class Meta:
        model = WorkOrder
        fields = '__all__'
        read_only_fields = [
            'id', 'slug', 'work_order_number', 'owner', 'requester',
            'requester_detail', 'request_to_detail', 'approver_detail', 'reviewers_detail',
            'category_detail', 'subcategory_detail', 'facility_detail', 'asset_detail',
            'resources_data', 'allow_resubmission',
        ]

    REJECTED_STATUSES = {'Reviewer Rejected', 'Approver Rejected'}

    def validate_source_work_request(self, value):
        if value is not None:
            qs = WorkOrder.objects.filter(source_work_request=value).exclude(
                approval_status__in=self.REJECTED_STATUSES, allow_resubmission=True
            )
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    f"A work order already exists for work request #{value.work_request_number}. "
                    "An Admin must unlock resubmission on the rejected work order before a new one can be raised."
                )
        return value

    def validate_source_ppm(self, value):
        if value is not None:
            qs = WorkOrder.objects.filter(source_ppm=value).exclude(
                approval_status__in=self.REJECTED_STATUSES, allow_resubmission=True
            )
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    f"A work order already exists for PPM #{value.id}. "
                    "An Admin must unlock resubmission on the rejected work order before a new one can be raised."
                )
        return value

    def create(self, validated_data):
        resource_uploads = validated_data.pop('resources', [])
        reviewers = validated_data.pop('reviewers', [])
        with transaction.atomic():
            instance = WorkOrder.objects.create(**validated_data)
            if reviewers:
                instance.reviewers.set(reviewers)
            self._attach_files(instance, resource_uploads, 'work_order_resources')
        return instance

    def update(self, instance, validated_data):
        resource_uploads = validated_data.pop('resources', [])
        reviewers = validated_data.pop('reviewers', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if reviewers is not None:
            instance.reviewers.set(reviewers)
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
    category_detail = AssetCategorySerializer(source='category', read_only=True)
    subcategory_detail = AssetSubCategorySerializer(source='subcategory', read_only=True)
    assets_detail = AssetSerializer(source='assets', many=True, read_only=True)
    facilities_detail = FacilitySerializer(source='facilities', many=True, read_only=True)
    items_detail = PaymentItemSerializer(source='items', many=True, read_only=True)
    approver_detail = UserSerializer(source='approver', read_only=True)

    class Meta:
        model = PPM
        fields = '__all__'
        read_only_fields = ['id', 'owner', 'approver_detail']


class WorkOrderCompletionSerializer(serializers.ModelSerializer):
    approver_detail = UserSerializer(source='approver', read_only=True)
    reviewers_detail = UserSerializer(source='reviewers', many=True, read_only=True)
    resources = serializers.ListField(child=serializers.FileField(), write_only=True, required=False)
    resources_data = FileAttachmentSerializer(many=True, read_only=True, source='resources')

    class Meta:
        model = WorkOrderCompletion
        fields = '__all__'
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at', 'approval_status', 'is_reviewed',
                            'reviewer_notes', 'approver_notes', 'approver_detail', 'reviewers_detail', 'resources_data']

    def validate_work_order(self, value):
        ACTIVE_STATUSES = {'Pending', 'Reviewed', 'Approved'}
        qs = WorkOrderCompletion.objects.filter(
            work_order=value,
            approval_status__in=ACTIVE_STATUSES,
        )
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            existing = qs.first()
            raise serializers.ValidationError(
                f"A Work Completion Certificate already exists for this Work Order "
                f"(WCC-{existing.pk}, status: {existing.approval_status}). "
                "Resolve or reject the existing WCC before creating a new one."
            )
        return value

    def _attach_files(self, instance, files):
        if not files:
            return
        from django.contrib.contenttypes.models import ContentType
        ct = ContentType.objects.get_for_model(instance)
        for f in files:
            FileAttachment.objects.create(content_type=ct, object_id=instance.pk, file=f)

    def create(self, validated_data):
        files = validated_data.pop('resources', [])
        reviewers = validated_data.pop('reviewers', [])
        with transaction.atomic():
            instance = WorkOrderCompletion.objects.create(**validated_data)
            if reviewers:
                instance.reviewers.set(reviewers)
            self._attach_files(instance, files)
        return instance

    def update(self, instance, validated_data):
        files = validated_data.pop('resources', [])
        reviewers = validated_data.pop('reviewers', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if reviewers is not None:
            instance.reviewers.set(reviewers)
        self._attach_files(instance, files)
        return instance


class InvoiceLineItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLineItem
        fields = ['id', 'item_name', 'amount', 'description']


class InvoiceSerializer(serializers.ModelSerializer):
    raised_by_detail = UserSerializer(source='raised_by', read_only=True)
    approver_detail = UserSerializer(source='approver', read_only=True)
    reviewers_detail = UserSerializer(source='reviewers', many=True, read_only=True)
    items_detail = InvoiceLineItemSerializer(source='items', many=True, read_only=True)
    attachments_data = FileAttachmentSerializer(source='attachments', many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = '__all__'
        read_only_fields = [
            'id', 'invoice_number', 'owner', 'raised_by',
            'raised_by_detail', 'approver_detail', 'reviewers_detail',
            'items_detail', 'attachments_data',
            'approval_status', 'is_reviewed', 'is_approved',
            'reviewer_notes', 'approver_notes',
            'created_at', 'updated_at',
        ]

    def validate_work_completion(self, value):
        if value is None:
            raise serializers.ValidationError(
                "An invoice must be linked to a Work Completion Certificate."
            )
        if value.approval_status != 'Approved':
            raise serializers.ValidationError(
                f"Invoice can only be raised against an Approved WCC. "
                f"Current status: '{value.approval_status}'."
            )
        return value

    def validate(self, attrs):
        if not attrs.get('work_completion'):
            raise serializers.ValidationError(
                {"work_completion": "An invoice must be linked to an approved Work Completion Certificate."}
            )
        return attrs

    def _attach_files(self, instance, files):
        if not files:
            return
        ct = ContentType.objects.get_for_model(instance)
        for f in files:
            FileAttachment.objects.create(content_type=ct, object_id=instance.pk, file=f)

    def create(self, validated_data):
        files = validated_data.pop('attachments_files', [])
        reviewers = validated_data.pop('reviewers', [])
        items_data = validated_data.pop('items_data', [])
        with transaction.atomic():
            instance = Invoice.objects.create(**validated_data)
            if reviewers:
                instance.reviewers.set(reviewers)
            for item in items_data:
                InvoiceLineItem.objects.create(invoice=instance, **item)
            self._attach_files(instance, files)
        return instance

    def update(self, instance, validated_data):
        files = validated_data.pop('attachments_files', [])
        reviewers = validated_data.pop('reviewers', None)
        items_data = validated_data.pop('items_data', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if reviewers is not None:
            instance.reviewers.set(reviewers)
        if items_data is not None:
            instance.items.all().delete()
            for item in items_data:
                InvoiceLineItem.objects.create(invoice=instance, **item)
        self._attach_files(instance, files)
        return instance
