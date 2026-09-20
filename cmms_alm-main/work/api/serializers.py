from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from work.models import WorkRequest, PaymentItem, Comment, PaymentRequisition, PPM, WorkOrder, WorkOrderCompletion, Invoice, InvoiceLineItem
from utils.models import FileAttachment

from accounts.api.serializers import (
    UserSerializer, SimpleUserSerializer, VendorSerializer, PersonnelSerializer
)
from facility.api.serializers import FacilitySerializer, ZoneSerializer, SubsystemSerializer
from facility.models import Facility, Zone, Subsystem
from asset_inventory.api.serializers import (AssetSerializer,
                                             DepartmentSerializer, AssetSubCategorySerializer,
                                             AssetCategorySerializer)
from asset_inventory.models import Asset
from asset_inventory.models.assets_category import AssetCategory, AssetSubCategory
from utils.serializers import FileAttachmentSerializer
from cmms_instanta.permissions import accessible_facilities


class WorkRequestSerializer(serializers.ModelSerializer):
    # Explicitly required (the model itself allows blank/null so existing
    # historical rows created before this rule aren't affected) — required
    # on create, but DRF automatically skips it for a partial (PATCH) update
    # that doesn't touch these fields.
    facility = serializers.PrimaryKeyRelatedField(queryset=Facility.objects.all())
    zone = serializers.PrimaryKeyRelatedField(queryset=Zone.objects.all())
    subsystem = serializers.PrimaryKeyRelatedField(queryset=Subsystem.objects.all())
    asset = serializers.PrimaryKeyRelatedField(queryset=Asset.objects.all())
    category = serializers.PrimaryKeyRelatedField(queryset=AssetCategory.objects.all())
    subcategory = serializers.PrimaryKeyRelatedField(queryset=AssetSubCategory.objects.all())

    requester_detail = SimpleUserSerializer(source='requester', read_only=True)
    request_to_detail = SimpleUserSerializer(source='request_to', many=True, read_only=True)
    approver_detail = SimpleUserSerializer(source='approver', read_only=True)
    reviewers_detail = SimpleUserSerializer(source='reviewers', many=True, read_only=True)
    category_detail = AssetCategorySerializer(source='category', read_only=True)
    subcategory_detail = AssetSubCategorySerializer(source='subcategory', read_only=True)
    facility_detail = FacilitySerializer(source='facility', read_only=True)
    zone_detail = ZoneSerializer(source='zone', read_only=True)
    subsystem_detail = SubsystemSerializer(source='subsystem', read_only=True)
    asset_detail = AssetSerializer(source='asset', read_only=True)
    department_detail = DepartmentSerializer(source='department', read_only=True)
    vendor_detail = VendorSerializer(source='vendor', read_only=True)
    po_vendor_detail = VendorSerializer(source='po_vendor', read_only=True)

    # Upload fields
    resources = serializers.ListField(child=serializers.FileField(), write_only=True, required=False)
    resources_data = FileAttachmentSerializer(many=True, read_only=True, source='resources')

    # Work Order auto-created once the request is Fully Approved (see
    # WorkRequestViewSet._auto_create_work_order). Null until then.
    derived_work_order = serializers.SerializerMethodField()

    def get_derived_work_order(self, obj):
        wo = (
            obj.derived_work_orders
            .exclude(approval_status__in=['Reviewer Rejected', 'Approver Rejected', 'Rejected'])
            .order_by('id')
            .first()
        )
        if not wo:
            return None
        return {
            'id': wo.id,
            'slug': wo.slug,
            'work_order_number': wo.work_order_number,
            'approval_status': wo.approval_status,
        }

    class Meta:
        model = WorkRequest
        fields = '__all__'
        read_only_fields = [
            'id', 'slug', 'work_request_number', 'owner', 'requester',
            # Detail expansions
            'requester_detail', 'request_to_detail', 'approver_detail', 'reviewers_detail',
            'category_detail', 'subcategory_detail', 'department_detail',
            'facility_detail', 'zone_detail', 'subsystem_detail', 'asset_detail', 'resources_data',
            'vendor_detail', 'po_vendor_detail', 'derived_work_order',
            # Workflow state — managed exclusively by action endpoints
            'approval_status', 'is_locked', 'po_number', 'po_document', 'po_vendor', 'po_amount',
            'cp_reason', 'reviewer_reason', 'approver_reason',
            'digital_signature', 'fully_approved_at',
        ]

    def validate(self, data):
        facility = data.get('facility', getattr(self.instance, 'facility', None))
        zone = data.get('zone', getattr(self.instance, 'zone', None))
        subsystem = data.get('subsystem', getattr(self.instance, 'subsystem', None))
        asset = data.get('asset', getattr(self.instance, 'asset', None))
        category = data.get('category', getattr(self.instance, 'category', None))
        subcategory = data.get('subcategory', getattr(self.instance, 'subcategory', None))

        if zone and facility and zone.facility_id != facility.id:
            raise serializers.ValidationError(
                {'zone': 'Selected zone does not belong to the selected facility.'}
            )
        if subsystem and facility and subsystem.facility_id and subsystem.facility_id != facility.id:
            raise serializers.ValidationError(
                {'subsystem': 'Selected subzone does not belong to the selected facility.'}
            )
        if subsystem and zone and subsystem.zone_id and subsystem.zone_id != zone.id:
            raise serializers.ValidationError(
                {'subsystem': 'Selected subzone does not belong to the selected zone.'}
            )
        if subcategory and category and subcategory.asset_category_id != category.id:
            raise serializers.ValidationError(
                {'subcategory': 'Selected component does not belong to the selected system/category.'}
            )

        # Only flag a genuine contradiction — an asset whose own facility/zone/etc.
        # is simply unset (common on assets created before this rule existed)
        # is not treated as a mismatch.
        if asset:
            if asset.facility_id and facility and asset.facility_id != facility.id:
                raise serializers.ValidationError(
                    {'asset': 'Selected asset does not belong to the selected facility.'}
                )
            if asset.zone_id and zone and asset.zone_id != zone.id:
                raise serializers.ValidationError(
                    {'asset': 'Selected asset does not belong to the selected zone.'}
                )
            if asset.subsystem_id and subsystem and asset.subsystem_id != subsystem.id:
                raise serializers.ValidationError(
                    {'asset': 'Selected asset does not belong to the selected subzone.'}
                )
            if asset.category_id and category and asset.category_id != category.id:
                raise serializers.ValidationError(
                    {'asset': 'Selected asset does not belong to the selected system/category.'}
                )
            if asset.subcategory_id and subcategory and asset.subcategory_id != subcategory.id:
                raise serializers.ValidationError(
                    {'asset': 'Selected asset does not belong to the selected component.'}
                )

        request = self.context.get('request')
        if facility and request is not None:
            if not accessible_facilities(request.user).filter(pk=facility.pk).exists():
                raise serializers.ValidationError(
                    {'facility': 'You are not assigned to this facility.'}
                )

        return data

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
    requester_detail = SimpleUserSerializer(source='requester', read_only=True)
    request_to_detail = SimpleUserSerializer(source='request_to', read_only=True)
    approver_detail = SimpleUserSerializer(source='approver', read_only=True)
    reviewers_detail = SimpleUserSerializer(source='reviewers', many=True, read_only=True)
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
            # Closed/Pending/Rejected tracking — managed exclusively by the
            # set-status action (which also drives the auto Payment Requisition).
            'work_status',
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
    payee_personnel_detail = PersonnelSerializer(source='payee_personnel', read_only=True)
    payee_owner_detail = SimpleUserSerializer(source='payee_owner', read_only=True)
    request_to_detail = SimpleUserSerializer(source='request_to', many=True, read_only=True)
    work_orders_detail = WorkOrderSerializer(source='work_orders', many=True, read_only=True)
    items_detail = PaymentItemSerializer(source='items', many=True, read_only=True)
    attachment_data = FileAttachmentSerializer(source='attachment', many=True, read_only=True)

    class Meta:
        model = PaymentRequisition
        fields = '__all__'
        read_only_fields = ['id', 'requisition_number', 'attachment_data']

    def validate(self, attrs):
        # Only enforced when payee_type is explicitly set — existing clients that
        # never send payee_type (and just set pay_to directly) are unaffected.
        payee_type = attrs.get('payee_type', getattr(self.instance, 'payee_type', None))
        field_by_type = {'vendor': 'pay_to', 'personnel': 'payee_personnel', 'owner': 'payee_owner'}
        required_field = field_by_type.get(payee_type)
        if required_field:
            has_value = attrs.get(required_field, getattr(self.instance, required_field, None))
            if not has_value:
                raise serializers.ValidationError(
                    {required_field: f"Required when payee_type is '{payee_type}'."}
                )
        return attrs


class PPMSerializer(serializers.ModelSerializer):
    category_detail = AssetCategorySerializer(source='category', read_only=True)
    subcategory_detail = AssetSubCategorySerializer(source='subcategory', read_only=True)
    assets_detail = AssetSerializer(source='assets', many=True, read_only=True)
    facilities_detail = FacilitySerializer(source='facilities', many=True, read_only=True)
    items_detail = PaymentItemSerializer(source='items', many=True, read_only=True)
    approver_detail = SimpleUserSerializer(source='approver', read_only=True)

    class Meta:
        model = PPM
        fields = '__all__'
        read_only_fields = ['id', 'owner', 'approver_detail']


class WorkOrderCompletionSerializer(serializers.ModelSerializer):
    approver_detail = SimpleUserSerializer(source='approver', read_only=True)
    reviewers_detail = SimpleUserSerializer(source='reviewers', many=True, read_only=True)
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
    raised_by_detail = SimpleUserSerializer(source='raised_by', read_only=True)
    approver_detail = SimpleUserSerializer(source='approver', read_only=True)
    reviewers_detail = SimpleUserSerializer(source='reviewers', many=True, read_only=True)
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
