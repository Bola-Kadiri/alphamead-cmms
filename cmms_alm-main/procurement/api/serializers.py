from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType

from accounts.api.serializers import VendorSerializer, SimpleUserSerializer
from facility.api.serializers import FacilitySerializer
from utils.serializers import FileAttachmentSerializer
from utils.models import FileAttachment
from procurement.models import (
    RequestForQuotation,
    PurchaseOrder,
    PurchaseOrderRequisition,
    GoodsReceivedNote,
    VendorContract
)
from utils.translation_mixin import TranslatableFieldMixin


class RequestForQuotationSerializer(TranslatableFieldMixin, serializers.ModelSerializer):
    facility_detail = FacilitySerializer(source='facility', read_only=True)
    vendors_detail = VendorSerializer(source='vendors', many=True, read_only=True)
    requester_detail = SimpleUserSerializer(source='requester', read_only=True)
    attachments = serializers.ListField(child=serializers.FileField(), write_only=True, required=False)
    attachments_data = serializers.SerializerMethodField()

    class Meta:
        model = RequestForQuotation
        fields = '__all__'
        read_only_fields = [
            'id', 'attachments_data', 'facility_detail', 'vendors_detail', 
            'requester_detail', 'created_at', 'updated_at'
        ]
        translatable_fields = ['title', 'terms']

    def get_attachments_data(self, obj):
        return FileAttachmentSerializer(obj.attachment.all(), many=True).data

    def create(self, validated_data):
        attachments = validated_data.pop('attachments', [])
        vendors = validated_data.pop('vendors', [])
        rfq = RequestForQuotation.objects.create(**validated_data)
        
        if vendors:
            rfq.vendors.set(vendors)

        # Handle attachments
        if attachments:
            content_type = ContentType.objects.get_for_model(RequestForQuotation)
            for file in attachments:
                FileAttachment.objects.create(
                    content_type=content_type,
                    object_id=rfq.id,
                    file=file
                )
        return rfq

    def update(self, instance, validated_data):
        attachments = validated_data.pop('attachments', [])
        vendors = validated_data.pop('vendors', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if vendors is not None:
            instance.vendors.set(vendors)

        if attachments:
            content_type = ContentType.objects.get_for_model(RequestForQuotation)
            for file in attachments:
                FileAttachment.objects.create(
                    content_type=content_type,
                    object_id=instance.id,
                    file=file
                )
        return instance


class PurchaseOrderSerializer(TranslatableFieldMixin, serializers.ModelSerializer):
    facility_detail = FacilitySerializer(source='facility', read_only=True)
    vendor_detail = VendorSerializer(source='vendor', read_only=True)
    requested_by_detail = SimpleUserSerializer(source='requested_by', read_only=True)
    attachments = serializers.ListField(child=serializers.FileField(), write_only=True, required=False)
    attachments_data = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOrder
        fields = '__all__'
        read_only_fields = [
            'id', 'attachments_data', 'facility_detail', 'vendor_detail',
            'requested_by_detail', 'created_at', 'updated_at'
        ]
        translatable_fields = ['type', 'terms_and_conditions']

    def get_attachments_data(self, obj):
        return FileAttachmentSerializer(obj.attachment.all(), many=True).data

    def create(self, validated_data):
        attachments = validated_data.pop('attachments', [])
        purchase_order = PurchaseOrder.objects.create(**validated_data)

        if attachments:
            content_type = ContentType.objects.get_for_model(PurchaseOrder)
            for file in attachments:
                FileAttachment.objects.create(
                    content_type=content_type,
                    object_id=purchase_order.id,
                    file=file
                )
        return purchase_order

    def update(self, instance, validated_data):
        attachments = validated_data.pop('attachments', [])
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if attachments:
            content_type = ContentType.objects.get_for_model(PurchaseOrder)
            for file in attachments:
                FileAttachment.objects.create(
                    content_type=content_type,
                    object_id=instance.id,
                    file=file
                )
        return instance


class PurchaseOrderRequisitionSerializer(TranslatableFieldMixin, serializers.ModelSerializer):
    vendor_detail = VendorSerializer(source='vendor', read_only=True)
    attachments = serializers.ListField(child=serializers.FileField(), write_only=True, required=False)
    attachments_data = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOrderRequisition
        fields = '__all__'
        read_only_fields = [
            'id', 'vendor_detail', 'attachments_data', 'invoice_number',
            'created_at', 'updated_at'
        ]
        translatable_fields = ['title', 'description']

    def get_attachments_data(self, obj):
        return FileAttachmentSerializer(obj.attachment.all(), many=True).data

    def create(self, validated_data):
        attachments = validated_data.pop('attachments', [])
        requisition = PurchaseOrderRequisition.objects.create(**validated_data)
        
        if attachments:
            content_type = ContentType.objects.get_for_model(PurchaseOrderRequisition)
            for file in attachments:
                FileAttachment.objects.create(
                    content_type=content_type,
                    object_id=requisition.id,
                    file=file
                )
        return requisition

    def update(self, instance, validated_data):
        attachments = validated_data.pop('attachments', [])
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if attachments:
            content_type = ContentType.objects.get_for_model(PurchaseOrderRequisition)
            for file in attachments:
                FileAttachment.objects.create(
                    content_type=content_type,
                    object_id=instance.id,
                    file=file
                )
        return instance


class GoodsReceivedNoteSerializer(TranslatableFieldMixin, serializers.ModelSerializer):
    facility_detail = FacilitySerializer(source='facility', read_only=True)
    vendor_detail = VendorSerializer(source='vendor', read_only=True)
    received_by_detail = SimpleUserSerializer(source='received_by', read_only=True)
    purchase_order_detail = PurchaseOrderSerializer(source='purchase_order', read_only=True)

    class Meta:
        model = GoodsReceivedNote
        fields = '__all__'
        read_only_fields = [
            'id', 'grn_number', 'facility_detail', 'vendor_detail',
            'received_by_detail', 'purchase_order_detail', 'created_at', 'updated_at'
        ]
        translatable_fields = []

    def create(self, validated_data):
        grn = GoodsReceivedNote.objects.create(**validated_data)
        return grn

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class VendorContractSerializer(TranslatableFieldMixin, serializers.ModelSerializer):
    vendor_detail = VendorSerializer(source='vendor', read_only=True)
    reviewer_detail = SimpleUserSerializer(source='reviewer', read_only=True)
    attachments = serializers.ListField(child=serializers.FileField(), write_only=True, required=False)
    attachments_data = serializers.SerializerMethodField()

    class Meta:
        model = VendorContract
        fields = '__all__'
        read_only_fields = [
            'id', 'vendor_detail', 'reviewer_detail', 'attachments_data',
            'created_at', 'updated_at'
        ]
        translatable_fields = ['contract_title']

    def get_attachments_data(self, obj):
        return FileAttachmentSerializer(obj.agreement.all(), many=True).data

    def create(self, validated_data):
        attachments = validated_data.pop('attachments', [])
        contract = VendorContract.objects.create(**validated_data)
        
        if attachments:
            content_type = ContentType.objects.get_for_model(VendorContract)
            for file in attachments:
                FileAttachment.objects.create(
                    content_type=content_type,
                    object_id=contract.id,
                    file=file
                )
        return contract

    def update(self, instance, validated_data):
        attachments = validated_data.pop('attachments', [])
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if attachments:
            content_type = ContentType.objects.get_for_model(VendorContract)
            for file in attachments:
                FileAttachment.objects.create(
                    content_type=content_type,
                    object_id=instance.id,
                    file=file
                )
        return instance
