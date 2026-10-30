from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from work.models import (WorkRequest, WorkRequestQuotationItem, PaymentItem, Comment, PaymentRequisition,
                          PPM, WorkOrder, WorkOrderCompletion, Invoice, InvoiceLineItem,
                          RaisePaymentApprovalSettings)
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
from .client_view import is_client_request, mask_completion, mask_work_order, mask_work_request


class WorkRequestQuotationItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkRequestQuotationItem
        fields = ['id', 'description', 'quantity', 'unit_cost_estimate', 'unit_cost_vendor', 'unit_cost_client', 'add_vat']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        role = getattr(getattr(request, 'user', None), 'roles', None)
        # Requester sees what the client is charged (client cost + VAT), not
        # what Alphamead actually pays the vendor — estimate is the same
        # kind of internal-cost figure, so it's hidden alongside it.
        if role == 'REQUESTER':
            data.pop('unit_cost_vendor', None)
            data.pop('unit_cost_estimate', None)
        return data


class WorkRequestSerializer(serializers.ModelSerializer):
    # facility/category are explicitly required (the model itself allows
    # blank/null so existing historical rows created before this rule
    # aren't affected) — required on create, but DRF automatically skips
    # it for a partial (PATCH) update that doesn't touch these fields.
    #
    # zone/subsystem/asset are left optional (matching the model's own
    # null=True) because most facilities in production have no zones,
    # subsystems, or assets registered yet (checked directly against the
    # data: 80/85 facilities have zero zones/subsystems, 78/85 have zero
    # assets) — requiring them here made it impossible to create a work
    # request against any of those facilities at all.
    facility = serializers.PrimaryKeyRelatedField(queryset=Facility.objects.all())
    zone = serializers.PrimaryKeyRelatedField(queryset=Zone.objects.all(), required=False, allow_null=True)
    subsystem = serializers.PrimaryKeyRelatedField(queryset=Subsystem.objects.all(), required=False, allow_null=True)
    asset = serializers.PrimaryKeyRelatedField(queryset=Asset.objects.all(), required=False, allow_null=True)
    category = serializers.PrimaryKeyRelatedField(queryset=AssetCategory.objects.all())
    # Optional: the Requester may not know the exact component. When given, it must belong to the category.
    subcategory = serializers.PrimaryKeyRelatedField(queryset=AssetSubCategory.objects.all(), required=False, allow_null=True)

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
    technician_detail = SimpleUserSerializer(source='technician', read_only=True)

    # Upload fields
    resources = serializers.ListField(child=serializers.FileField(), write_only=True, required=False)
    resources_data = FileAttachmentSerializer(many=True, read_only=True, source='resources')

    # Work Order auto-created once the request is Fully Approved (see
    # WorkRequestViewSet._auto_create_work_order). Null until then.
    derived_work_order = serializers.SerializerMethodField()

    # Quotation lines entered by Procurement & Store on cp-approve, and the
    # totals/margin derived from them (see WorkRequest.total_cost_vendor/
    # total_cost_client/margin properties).
    quotation_items = WorkRequestQuotationItemSerializer(many=True, read_only=True)
    total_cost_vendor = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    total_cost_client = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    margin = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)

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
            'vendor_detail', 'po_vendor_detail', 'technician_detail', 'derived_work_order',
            'quotation_items', 'total_cost_vendor', 'total_cost_client', 'margin',
            # Workflow state — managed exclusively by action endpoints
            'approval_status', 'is_locked', 'po_number', 'po_document', 'po_vendor', 'po_amount',
            'cp_reason', 'reviewer_reason', 'approver_reason',
            'digital_signature', 'fully_approved_at', 'flow',
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        role = getattr(getattr(request, 'user', None), 'roles', None)
        # Requester sees client cost + margin, not what Alphamead pays the
        # vendor — see WorkRequestQuotationItemSerializer for the per-line
        # equivalent.
        if role == 'REQUESTER':
            data.pop('total_cost_vendor', None)
        if role == 'CLIENT':
            mask_work_request(data)
        return data

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

    # Closure fields — set exclusively via the `set-status` action (see
    # WorkOrderViewSet.set_status), never via the generic update endpoint.
    vendor_detail = VendorSerializer(source='vendor', read_only=True)
    technician_detail = SimpleUserSerializer(source='technician', read_only=True)
    # Raise Payment payee (type RAISE-PAYMENT).
    payee_detail = VendorSerializer(source='payee', read_only=True)

    # The WCC submitted against this Work Order (see WorkOrderCompletion),
    # and the Payment Requisition raised from it — both null until they
    # exist. Lets the Work Order page link straight to each one.
    latest_completion = serializers.SerializerMethodField()
    linked_payment_requisition = serializers.SerializerMethodField()

    # Raise Payment approver-first route: who acts next, and the second approver
    # for large bills (see RaisePaymentApprovalSettings).
    final_approver_detail = SimpleUserSerializer(source='final_approver', read_only=True)
    # Selected by the Requester on Raise Payment bills of ₦1,000,000 or more (checked in validate).
    final_approver = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.filter(is_active=True), required=False, allow_null=True,
    )
    next_step = serializers.SerializerMethodField()
    needs_second_approval = serializers.SerializerMethodField()
    # Raise Payment: who is meant to act at each step, who did, and when. Built only on a
    # bill's own page (not in lists), so list pages stay fast.
    approval_trail = serializers.SerializerMethodField()

    def get_approval_trail(self, obj):
        view = self.context.get('view')
        request = self.context.get('request')
        if not obj.is_approver_first or not getattr(view, 'detail', False):
            return None
        from work.models.raise_payment_trail import trail
        return trail(obj, getattr(request, 'user', None))

    NEXT_STEP = {'Awaiting Procurement': 'procurement', 'Procurement Returned': 'requester', 'Pending': 'approver',
                 'Approver Approved': 'reviewer', 'Awaiting Final Approval': 'final_approver'}

    def get_next_step(self, obj):
        return self.NEXT_STEP.get(obj.approval_status) if obj.is_approver_first else None

    def get_needs_second_approval(self, obj):
        if not obj.is_approver_first:
            return False
        if obj.final_approver_id:
            return True
        if '_raise_payment_settings' not in self.context:
            self.context['_raise_payment_settings'] = RaisePaymentApprovalSettings.current()
        return self.context['_raise_payment_settings'].needs_second_approval(obj.cost, obj.currency)

    def get_source_work_request_detail(self, obj):
        wr = obj.source_work_request
        if not wr:
            return None
        # The Work Order's own "Quotation" and "File attachments" sections
        # show the same quotation/PO/invoice/attachment data the source Work
        # Request itself does — it's never re-entered on the Work Order, so
        # without this it always reads empty there. Same Requester-facing
        # cost masking as WorkRequestSerializer/WorkRequestQuotationItemSerializer.
        request = self.context.get('request')
        role = getattr(getattr(request, 'user', None), 'roles', None)
        quotation_items = WorkRequestQuotationItemSerializer(
            wr.quotation_items.all(), many=True, context=self.context
        ).data
        return {
            'id': wr.id,
            'work_request_number': wr.work_request_number,
            'po_number': wr.po_number,
            'po_document': wr.po_document.url if wr.po_document and wr.po_document.name else None,
            'vendor_invoice': wr.vendor_invoice.url if wr.vendor_invoice and wr.vendor_invoice.name else None,
            'attachment': wr.attachment.url if wr.attachment and wr.attachment.name else None,
            'invoice_no': wr.invoice_no,
            'quotation_items': quotation_items,
            'total_cost_vendor': None if role == 'REQUESTER' else str(wr.total_cost_vendor),
            'total_cost_client': str(wr.total_cost_client),
            'margin': None if role == 'REQUESTER' else str(wr.margin),
        }

    def get_latest_completion(self, obj):
        completion = obj.completions.order_by('-id').first()
        if not completion:
            return None
        return {
            'id': completion.id,
            'wcc_number': completion.wcc_number,
            'approval_status': completion.approval_status,
        }

    def get_linked_payment_requisition(self, obj):
        requisition = obj.linked_payments.order_by('id').first()
        if not requisition:
            return None
        return {
            'id': requisition.id,
            'requisition_number': requisition.requisition_number,
            # 'request' | 'approve' | 'reject' — closing requires 'approve'
            # (see WorkOrderViewSet.set_status); surfaced so the frontend can
            # explain why the Close button is still blocked.
            'approval_status': requisition.approval_status,
            # Raise Payment work orders show their payment progress on the work order.
            'is_disbursed': requisition.is_disbursed,
            'disbursed_at': requisition.disbursed_at,
            'is_closed': requisition.is_closed,
        }

    class Meta:
        model = WorkOrder
        fields = '__all__'
        read_only_fields = [
            'id', 'slug', 'work_order_number', 'owner', 'requester',
            'requester_detail', 'request_to_detail', 'approver_detail', 'reviewers_detail',
            'category_detail', 'subcategory_detail', 'facility_detail', 'asset_detail',
            'resources_data', 'allow_resubmission', 'vendor_detail', 'technician_detail',
            'latest_completion', 'linked_payment_requisition', 'payee_detail',
            # Five-stage flow — set only through the Stage 2 actions.
            'flow', 'client_price', 'quotation_reference', 'po_number',
            'accepted_at', 'accepted_by', 'confirmed_start_date', 'contractor_technician',
            # Raise Payment approval route — set by the system, moved on only by the approval actions.
            'approval_route', 'final_approver_detail', 'final_approved_at',
            'final_approver_reason', 'next_step', 'needs_second_approval', 'approval_trail',
            'needs_procurement', 'quotation_file', 'quotation_amount', 'po_document',
            'procurement_by', 'procurement_at', 'procurement_reason',
            # Closed/Pending/Rejected tracking, and the closure fields it sets —
            # managed exclusively by the set-status action (which also drives
            # the auto Payment Requisition).
            'work_status', 'vendor', 'technician', 'rating', 'started_at', 'completed_at',
        ]

    REJECTED_STATUSES = {'Reviewer Rejected', 'Approver Rejected', 'Final Approver Rejected'}

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if is_client_request(self.context):
            mask_work_order(data, instance)
        return data

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

    def validate(self, attrs):
        """
        Raise Payment (known-cost bills: EKEDC, waste…) skips the work request,
        PO and WCC, so the work order itself must carry everything the payment
        needs — and the bill as evidence. Other work order types are untouched,
        and so are Raise Payment work orders created before this flow existed
        (no payee — see WorkOrder.uses_raise_payment_flow).
        """
        instance = self.instance
        current_type = getattr(instance, 'type', None)
        new_type = attrs.get('type', current_type)
        raise_payment = WorkOrder.RAISE_PAYMENT

        if instance is not None and instance.uses_raise_payment_flow and new_type != raise_payment:
            raise serializers.ValidationError(
                {'type': "A Raise Payment work order's type can't be changed."}
            )
        if new_type != raise_payment:
            attrs.pop('final_approver', None)  # only Raise Payment bills have one
            return attrs

        is_legacy_edit = (
            instance is not None and current_type == raise_payment
            and instance.payee_id is None and 'payee' not in attrs
        )
        if is_legacy_edit:
            attrs.pop('final_approver', None)
            return attrs

        if instance is not None and instance.uses_raise_payment_flow and instance.approval_status == 'Approved':
            raise serializers.ValidationError(
                "This Raise Payment work order is approved and its payment has been raised; it can no longer be edited."
            )
        # Mid-approval on the approver-first route: the amount the approvers signed off can't change.
        if instance is not None and instance.is_approver_first and instance.approval_status in (
                'Awaiting Procurement', 'Approver Approved', 'Awaiting Final Approval'):
            raise serializers.ValidationError(
                "This Raise Payment bill is being approved and can't be edited. Ask an approver to reject it "
                "if it needs changes."
            )
        # Procurement & Store confirmed the amount against the PO: it can't change without them.
        if (instance is not None and instance.is_approver_first and instance.procurement_at
                and instance.approval_status == 'Pending'
                and (('cost' in attrs and attrs['cost'] != instance.cost)
                     or ('currency' in attrs and attrs['currency'] != instance.currency))):
            raise serializers.ValidationError(
                {'cost': "Procurement & Store has confirmed this amount against the quotation. Ask them to return the bill "
                         "if the amount must change."}
            )

        def value(field):
            return attrs[field] if field in attrs else getattr(instance, field, None)

        errors = {}
        category = value('category')
        if not category:
            errors['category'] = "Select the bill category (e.g. PHCN/Power Payment)."
        elif not category.is_known_cost:
            errors['category'] = (
                f"'{category.name}' is not on the known-cost list. Raise Payment is only for "
                "categories an Admin has marked as known-cost; other jobs must start from a work request."
            )
        # The bill type (e.g. EKEDC) is optional; when given it must be an active subcategory of the category.
        subcategory = value('subcategory')
        if not subcategory:
            pass
        elif category and subcategory.asset_category_id != category.pk:
            errors['subcategory'] = f"'{subcategory.name}' is not under '{category.name}'."
        elif not subcategory.is_active:
            errors['subcategory'] = f"'{subcategory.name}' is inactive."
        if not value('facility'):
            errors['facility'] = "Select the facility this bill is for."
        if not value('payee'):
            errors['payee'] = "Select who is being paid (e.g. EKEDC)."
        elif not value('payee').has_bank_details:
            errors['payee'] = (
                f"'{value('payee').name}' has no bank details yet. Ask the Super Admin to add the "
                "account name, bank and account number before raising this payment."
            )
        cost = value('cost')
        if cost is None or cost <= 0:
            errors['cost'] = "Enter the bill amount."
        else:
            # Bills of ₦1,000,000 or more (or in another currency) need a second approval:
            # the Requester selects the configured final approver. Smaller bills have none.
            approval_settings = RaisePaymentApprovalSettings.current()
            if approval_settings.needs_second_approval(cost, value('currency')):
                expected = approval_settings.second_approver()
                selected = value('final_approver')
                limit = f"NGN {approval_settings.final_approval_threshold:,.0f}"
                if expected is None:
                    errors['final_approver'] = (
                        f"Bills of {limit} or more need a final approver, but no active AlphaCMMS user has the "
                        f"email {approval_settings.second_approver_email}. Ask the Super Admin."
                    )
                elif selected is None:
                    errors['final_approver'] = (
                        f"Select the final approver ({expected.name}). Bills of {limit} or more need a second approval."
                    )
                elif selected.pk != expected.pk:
                    errors['final_approver'] = f"The final approver for bills of {limit} or more must be {expected.name}."
            else:
                attrs['final_approver'] = None
        # A new bill goes to the location's Approver from the Approval Matrix; the Requester
        # chooses only where the location has none set yet. Bills already raised keep theirs.
        if instance is None:
            from work.models.approval_matrix import location_approver
            matrix_approver = location_approver(value('facility'))
            if matrix_approver is not None:
                attrs['approver'] = matrix_approver
        if value('source_work_request') or value('source_ppm'):
            errors['type'] = "A Raise Payment work order is raised directly, not from a work request or PPM."
        has_bill = bool(attrs.get('resources')) or (instance is not None and instance.resources.exists())
        if not has_bill:
            errors['resources'] = "Attach the bill. It is the evidence for this payment."

        # Duplicate-payment guard: the same bill (payee + bill number) can only
        # be raised once, unless the earlier one was rejected.
        bill_number = (value('invoice_no') or '').strip()
        payee = value('payee')
        if not bill_number:
            errors['invoice_no'] = "Enter the bill / invoice number."
        elif payee:
            duplicate = WorkOrder.objects.filter(
                type=raise_payment, payee=payee, invoice_no__iexact=bill_number,
            ).exclude(approval_status__in=self.REJECTED_STATUSES | {'Rejected'})
            if instance is not None:
                duplicate = duplicate.exclude(pk=instance.pk)
            duplicate = duplicate.first()
            if duplicate:
                errors['invoice_no'] = (
                    f"Bill {bill_number} for {payee.name} has already been raised on "
                    f"Work Order #{duplicate.work_order_number}."
                )
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def create(self, validated_data):
        resource_uploads = validated_data.pop('resources', [])
        reviewers = validated_data.pop('reviewers', [])
        # New Raise Payment bills go Approver → Reviewer; large bills start with Procurement & Store
        # and end with the second approver.
        if validated_data.get('type') == WorkOrder.RAISE_PAYMENT and validated_data.get('payee'):
            validated_data['approval_route'] = WorkOrder.APPROVER_FIRST
            if RaisePaymentApprovalSettings.current().needs_procurement(
                    validated_data.get('cost'), validated_data.get('currency')):
                validated_data['needs_procurement'] = True
                validated_data['approval_status'] = 'Awaiting Procurement'
        with transaction.atomic():
            instance = WorkOrder.objects.create(**validated_data)
            if reviewers:
                instance.reviewers.set(reviewers)
            self._attach_files(instance, resource_uploads, 'work_order_resources')
            request = self.context.get('request')
            if instance.is_approver_first and request is not None:
                from work.models.raise_payment_trail import stamp
                stamp(instance, 'raised', request.user)
        return instance

    def update(self, instance, validated_data):
        resource_uploads = validated_data.pop('resources', [])
        reviewers = validated_data.pop('reviewers', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        # A bill edited up to the large-bill amount before the Approver acts now needs Procurement & Store.
        if (instance.is_approver_first and instance.approval_status == 'Pending' and not instance.procurement_at
                and RaisePaymentApprovalSettings.current().needs_procurement(instance.cost, instance.currency)):
            instance.needs_procurement = True
            instance.approval_status = 'Awaiting Procurement'
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
    disbursed_by_detail = SimpleUserSerializer(source='disbursed_by', read_only=True)
    closed_by_detail = SimpleUserSerializer(source='closed_by', read_only=True)

    class Meta:
        model = PaymentRequisition
        fields = '__all__'
        read_only_fields = [
            'id', 'requisition_number', 'attachment_data',
            # Disbursement — managed exclusively by the `disburse` action.
            'is_disbursed', 'disbursed_at', 'disbursed_by', 'disbursed_by_detail',
            # Close-out — managed exclusively by the `close` action.
            'is_closed', 'closed_at', 'closed_by', 'closed_by_detail',
        ]

    def validate(self, attrs):
        # Once disbursed, the record is a closed financial event — no field
        # may change (including via a partial update), matching the
        # `disburse` action's own guard for the direct-write path.
        if self.instance is not None and self.instance.is_disbursed:
            raise serializers.ValidationError(
                "This payment requisition has already been disbursed and is permanently locked."
            )

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
    # Was referenced by the frontend but never actually declared here, so it
    # was always undefined — added so the WCC page can show real Work Order
    # info (and, via its own latest_completion/linked_payment_requisition,
    # let the WCC and Payment Requisition nest as nearby accordion sections).
    work_order_detail = WorkOrderSerializer(source='work_order', read_only=True)

    class Meta:
        model = WorkOrderCompletion
        fields = '__all__'
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at', 'approval_status', 'is_reviewed',
                            'reviewer_notes', 'approver_notes', 'approver_detail', 'reviewers_detail',
                            'resources_data', 'work_order_detail',
                            # Five-stage flow — set only through the Stage 3 actions.
                            'flow', 'started_at', 'finished_at', 'technician', 'vendor_rating',
                            'completion_notes', 'site_visit_date']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if is_client_request(self.context):
            mask_completion(data)
        return data

    def validate_work_order(self, value):
        if value is not None and value.uses_raise_payment_flow:
            raise serializers.ValidationError(
                "Raise Payment work orders don't need a WCC — the attached bill is the evidence."
            )
        ACTIVE_STATUSES = WorkOrderCompletion.ACTIVE_STATUSES
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
                f"(WCC-{existing.wcc_number or existing.pk}, status: {existing.approval_status}). "
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
            # Five-stage flow — set only through the Stage 4 actions.
            'flow', 'vendor', 'vendor_invoice_number', 'vat_charged', 'entered_for_vendor',
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
