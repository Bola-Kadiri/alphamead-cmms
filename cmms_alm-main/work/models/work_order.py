import random

from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.utils.text import slugify

from utils.models import UserPrivModel, Dated, Status, OwnerPrivModel, FileAttachment


class ItemCost(Dated, OwnerPrivModel, models.Model):
    """
    Represents the item or cost details in a work order.
    """
    invoice_no = models.CharField(
        max_length=100, 
        help_text="Invoice number for the cost item."
    )
    currency = models.CharField(
        max_length=3, 
        choices=[
            ('NGN', 'Nigerian Naira'),
            ('USD', 'US Dollar'),
            ('EUR', 'Euro'),
        ],
        help_text="Currency of the cost."
    )
    add_discount = models.BooleanField(
        default=False, 
        help_text="Whether a discount is added."
    )
    exclude_in_management_fee = models.BooleanField(
        default=False, 
        help_text="Exclude this cost in management fee calculations."
    )



class FollowUp(Dated, OwnerPrivModel, models.Model):
    """
    Represents a follow-up action on a request.
    """
    assign_escalate = models.BooleanField(
        default=False, 
        help_text="Indicates whether the follow-up involves assignment or escalation."
    )
    notify_requester = models.BooleanField(
        default=False, 
        help_text="Indicates whether the requester is notified."
    )
    cc = models.TextField(
        blank=True, 
        null=True, 
        help_text="Users or email addresses to CC."
    )
    message = models.TextField(
        help_text="Message content for the follow-up."
    )
    attachment = models.FileField(
        upload_to='followups/',
        blank=True, 
        null=True, 
        help_text="Attachment for the follow-up."
    )
    
    

class WorkOrder(OwnerPrivModel, Dated, Status, models.Model):
    """
    Represents a work order with details such as type, facility, requester, and associated resources.
    """
    TYPE_CHOICES = [
        ('Unplanned', 'Unplanned'),
        ('Planned', 'Planned'),
        ('FROM-PPM', 'From PPM'),
        ('FROM-WORK-REQUEST', 'From Work Request'),
        ('RAISE-PAYMENT', 'Raise Payment'),
    ]

    # Raise Payment — known-cost bills (EKEDC, waste…): raised directly as a
    # work order, with no work request, PO or WCC. Its payment details live on
    # the work order, and final approval creates the payment requisition
    # already approved. See `uses_raise_payment_flow`.
    RAISE_PAYMENT = 'RAISE-PAYMENT'

    PRIORITY_CHOICES = [
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
    ]

    PPM_TYPE_CHOICES = [
        ('Scheduled', 'Scheduled'),
        ('Unscheduled', 'Unscheduled'),
    ]

    APPROVAL_STATUSES = [
        ("Pending", "Pending"),
        ("Reviewed", "Reviewed"),
        ("Approved", "Approved"),
        ("Reviewer Rejected", "Reviewer Rejected"),
        ("Approver Rejected", "Approver Rejected"),
        ("Rejected", "Rejected"),
        # Raise Payment, approver-first route (see approval_route). Large bills start with
        # Procurement & Store adding the PO and quotation (see needs_procurement).
        ("Awaiting Procurement", "Awaiting Procurement"),
        ("Procurement Returned", "Procurement Returned"),
        ("Approver Approved", "Approver Approved"),
        ("Awaiting Final Approval", "Awaiting Final Approval"),
        ("Final Approver Rejected", "Final Approver Rejected"),
        # Five-stage flow (Stage 2): priced by Procurement & Store, reviewed, client approves the price.
        ("Pricing", "Pricing"),
        ("Awaiting Review", "Awaiting Review"),
        ("Sent Back", "Sent Back"),
        ("Awaiting Client", "Awaiting Client"),
        ("Client Rejected", "Client Rejected"),
    ]

    LEGACY = 'legacy'
    FIVE_STAGE = 'five_stage'
    FLOW_CHOICES = [
        (LEGACY, "Original flow"),
        (FIVE_STAGE, "Five-stage flow"),
    ]

    # Raise Payment bills raised from this release on: Approver → Reviewer →
    # (second approver, for large bills). Older work orders have no route and
    # keep Reviewer → Approver.
    APPROVER_FIRST = 'APPROVER_FIRST'
    APPROVAL_ROUTE_CHOICES = [(APPROVER_FIRST, 'Approver, then Reviewer (Raise Payment)')]

    CURRENCY_CHOICES = [
        ("USD", "USD"),
        ("EUR", "EUR"),
        ("NGN", "NGN"),
    ]

    type = models.CharField(
        max_length=50,
        choices=TYPE_CHOICES,
        blank=True,
        null=True,
        help_text="Type of the work order.",
    )

    source_work_request = models.ForeignKey(
        'work.WorkRequest',
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='derived_work_orders',
        help_text="Work request this order was created from.",
    )

    source_ppm = models.ForeignKey(
        'work.PPM',
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='derived_work_orders',
        help_text="PPM schedule this order was created from.",
    )
    
    work_order_number = models.CharField(
        max_length=7,
        # unique=True,
        blank=True,
        help_text="Unique 7-digit work request number."
    )
    
    sub_type = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Sub-type of the work order."
    )
    
    facility = models.ForeignKey(
        'facility.Facility',
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='work_orders_facility',
        help_text="Facility or location associated with the work order."
    )

    building = models.ForeignKey(
        'facility.Building',
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='work_orders_building',
        help_text="Building associated with the work order."
    )
    
    apartment = models.ForeignKey(
        'facility.Apartment',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='work_orders_apartment',
        help_text="Apartment/Room related to the work order."
    )
    
    category = models.ForeignKey(
        'asset_inventory.AssetCategory',
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='work_orders_category',
        help_text="Category of the work order."
    )

    subcategory = models.ForeignKey(
        'asset_inventory.AssetSubCategory',
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='work_orders_subcategory',
        help_text="Subcategory of the work order."
    )
    
    department = models.ForeignKey(
       'accounts.Department',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Department handling the work order."
    )
    
    priority = models.CharField(
        max_length=50,
        choices=PRIORITY_CHOICES,
        default='Medium',
        help_text="Priority level of the work order."
    )
    
    ppm_type = models.CharField(
        max_length=50,
        choices=PPM_TYPE_CHOICES,
        blank=True,
        null=True,
        help_text="Planned Preventive Maintenance type."
    )
    
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Detailed description of the work order."
    )
    
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='requested_work_orders',
        help_text="User who requested the work order."
    )
    
    work_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='owned_work_orders',
        help_text="User responsible for the work order."
    )
    
    expected_start_date = models.DateField(
        blank=True,
        null=True,
        help_text="Expected start date for the work."
    )
    
    expected_start_time = models.TimeField(
        blank=True,
        null=True,
        help_text="Expected start time for the work."
    )
    
    duration = models.DurationField(
        blank=True,
        null=True,
        help_text="Expected duration of the work."
    )
    
    approved = models.BooleanField(
        default=False,
        help_text="Indicates whether the work order is approved."
    )
    
    mobilization_fee_required = models.BooleanField(
        default=False,
        help_text="Indicates whether mobilization fee is required."
    )
    
    po_required = models.BooleanField(
        default=False,
        help_text="Indicates whether a purchase order is required."
    )
    
    request_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='work_orders_assigned_to',
        help_text="User to whom the approval request is sent.",
    )

    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='work_orders_to_approve',
        help_text="User assigned to approve this work order.",
    )

    reviewers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='work_orders_to_review',
        help_text="Users assigned to review this work order.",
    )

    cost = models.DecimalField(
        max_digits=10, decimal_places=2,
        blank=True, null=True,
        help_text="Estimated cost of the work order.",
    )
    
    is_reviewed = models.BooleanField(
        default=False,
        help_text="Indicates whether the work order has been reviewed."
    )

    is_approved = models.BooleanField(
        default=False,
        help_text="Indicates whether the request is approved."
    )

    reviewer_reason = models.TextField(
        blank=True, null=True,
        help_text="Reason provided when a reviewer rejects the work order."
    )

    approver_reason = models.TextField(
        blank=True, null=True,
        help_text="Reason provided when an approver rejects the work order."
    )

    digital_signature = models.CharField(
        max_length=255, blank=True, null=True,
        help_text="Approver's digital signature (full name) on final approval."
    )
    remark = models.TextField(
        blank=True, 
        null=True, 
        help_text="Remark for the approval."
    )
    
    item_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Cost of the item.")
    
    
    payment_requisition = models.BooleanField(
        default=False,
        help_text="Indicates if a payment requisition should be created."
    )

    
    # item_cost = models.ForeignKey(
    #     ItemCost, 
    #     on_delete=models.CASCADE, 
    #     blank=True, 
    #     null=True, 
    #     help_text="Item cost details."
    # )
    
    # payment_requisition = models.ForeignKey(
    #     PaymentRequisition, 
    #     on_delete=models.CASCADE, 
    #     blank=True, 
    #     null=True, 
    #     help_text="Payment requisition details."
    # )
    
    follow_up = models.ForeignKey(
        FollowUp, 
        on_delete=models.CASCADE, 
        blank=True, 
        null=True, 
        help_text="Follow-up details."
    )

    approval_status = models.CharField(
        max_length=30,
        choices=APPROVAL_STATUSES,
        default="Pending",
        help_text="Approval status of the work order."
    )

    # ── Five-stage flow (Stage 2) ────────────────────────────────────────────
    flow = models.CharField(
        max_length=20,
        choices=FLOW_CHOICES,
        default=LEGACY,
        help_text="Which approval flow this work order follows; set when it is created and never changed."
    )
    client_price = models.DecimalField(
        max_digits=18, decimal_places=2, blank=True, null=True,
        help_text="What the client is billed (sum of the client prices on the quote lines). `cost` is the vendor cost."
    )
    quotation_reference = models.CharField(max_length=100, blank=True, default='',
                                           help_text="The vendor's quotation reference.")
    po_number = models.CharField(max_length=100, blank=True, default='', help_text="Purchase Order number.")
    accepted_at = models.DateTimeField(blank=True, null=True, help_text="When the contractor accepted the job.")
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='+',
        help_text="The contractor's user who accepted the job."
    )
    confirmed_start_date = models.DateField(blank=True, null=True, help_text="Start date the contractor confirmed.")
    contractor_technician = models.CharField(max_length=255, blank=True, default='',
                                             help_text="Contractor's technician named when accepting.")

    WORK_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("closed", "Closed"),
        ("rejected", "Rejected"),
    ]

    work_status = models.CharField(
        max_length=20,
        choices=WORK_STATUS_CHOICES,
        default="pending",
        help_text="Closed/Pending/Rejected tracking of the physical work, separate from approval_status. Managed via the set-status action.",
    )

    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default="USD",
        help_text="Currency for the work order."
    )

    exclude_management_fee = models.BooleanField(
        default=False,
        help_text="Indicates if the management fee should be excluded."
    )

    allow_resubmission = models.BooleanField(
        default=False,
        help_text="Admin-controlled flag. When True, allows a new work order to be raised from the same source PPM or work request after rejection."
    )

    # files = models.ManyToManyField(
    #     FileAttachment,
    #     blank=True,
    #     related_name='work_orders_files',
    #     help_text="Files attached to the work order."
    # )

    resources = GenericRelation(
        FileAttachment,
        related_query_name='work_order_resources',
        help_text="Resources attached to the work request."
    )

    # attachment = GenericRelation(
    #     FileAttachment,
    #     related_query_name='work_order_attachment',
    #     help_text="Resources attached to the work request."
    # )

    add_discount = models.BooleanField(
        default=False,
        help_text="Indicates if a discount should be applied."
    )

    asset = models.ForeignKey(
        'asset_inventory.Asset',
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='work_orders_assets',
        help_text="Asset associated with the work order."
    )

    slug = models.SlugField(
        max_length=300,
        unique=True,
        blank=True,
        help_text="Auto-generated unique slug for the work order."
    )

    require_mobilization_fee = models.BooleanField(
        default=False,
        help_text="Indicates if a Mobilization Fee is required for the work order."
    )

    follow_up_notes = models.TextField(
        blank=True, null=True,
        help_text="Notes for follow-ups related to the work order."
    )

    invoice_no = models.CharField(
        max_length=50,
        blank=True, null=True,
        help_text="Invoice number associated with the work order."
    )

    # ── Closure fields — set via the `close` action, gated on an Approved
    # WorkOrderCompletion (WCC) existing for this work order ──────────────────

    vendor = models.ForeignKey(
        'accounts.Vendor',
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='work_orders',
        help_text="Vendor carrying out the work. Optional until closing, required to close.",
    )

    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='work_orders_as_technician',
        help_text="Technician carrying out the work. Optional until closing, required to close.",
    )

    rating = models.PositiveSmallIntegerField(
        blank=True, null=True,
        help_text="Star rating (1-5) given to the completed work order.",
    )

    started_at = models.DateTimeField(
        blank=True, null=True,
        help_text="When physical work actually started (set on closing).",
    )

    completed_at = models.DateTimeField(
        blank=True, null=True,
        help_text="When physical work actually completed (set on closing).",
    )

    # ── Raise Payment details — the amount is `cost`; these become the
    # payment requisition on approval. ───────────────────────────────────────

    payee = models.ForeignKey(
        'accounts.Vendor',
        on_delete=models.PROTECT,
        blank=True, null=True,
        related_name='raise_payment_work_orders',
        help_text="Raise Payment: who is paid (e.g. EKEDC).",
    )

    expected_payment_date = models.DateField(
        blank=True, null=True,
        help_text="Raise Payment: expected payment date.",
    )

    withholding_tax = models.CharField(
        max_length=50,
        blank=True, null=True,
        help_text="Raise Payment: selected withholding tax option.",
    )

    approval_route = models.CharField(
        max_length=20,
        choices=APPROVAL_ROUTE_CHOICES,
        blank=True, null=True,
        help_text="Raise Payment: approval order. Empty = Reviewer, then Approver.",
    )

    final_approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='final_approval_work_orders',
        help_text="Raise Payment: second (final) approver for large bills.",
    )

    final_approved_at = models.DateTimeField(blank=True, null=True)

    final_approver_reason = models.TextField(
        blank=True, null=True,
        help_text="Reason given when the second approver rejects.",
    )

    # Raise Payment, large bills: Procurement & Store adds the PO and the quotation
    # before the Approver sees the bill (see RaisePaymentApprovalSettings).
    needs_procurement = models.BooleanField(
        default=False,
        help_text="Raise Payment: Procurement & Store must add the PO and quotation before the Approver acts.",
    )
    quotation_file = models.FileField(upload_to='work_orders/quotations/', blank=True, null=True,
                                      help_text="Raise Payment: the quotation Procurement & Store attached.")
    po_amount = models.DecimalField(
        max_digits=18, decimal_places=2, blank=True, null=True,
        help_text="Raise Payment: the PO cost Procurement & Store entered. Must match the bill amount; it is what is paid.",
    )
    procurement_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='+',
        help_text="Procurement & Store user who added the PO and quotation.",
    )
    procurement_at = models.DateTimeField(blank=True, null=True)
    procurement_reason = models.TextField(blank=True, default='',
                                          help_text="Why Procurement & Store returned the bill to the Requester.")

    @property
    def is_approver_first(self):
        return self.approval_route == self.APPROVER_FIRST

    @property
    def uses_raise_payment_flow(self):
        """
        True for Raise Payment work orders on the known-cost flow (payment on
        approval, no WCC, auto-close on disbursement). Raise Payment work
        orders created before this flow existed have no payee and keep the
        original WO → WCC → PR behaviour.
        """
        return self.type == self.RAISE_PAYMENT and self.payee_id is not None

    def prepopulate_slug(self):
        base_slug = slugify(self.type or 'work-order')
        unique_slug = base_slug
        num = 1
        while WorkOrder.objects.filter(slug=unique_slug).exists():
            unique_slug = f"{base_slug}-{num}"
            num += 1
        return unique_slug
    
    def generate_unique_work_order_number(self):
        """Generate a unique 7-digit work request number."""
        while True:
            number = str(random.randint(1000000, 9999999))  # Generate 7-digit number
            if not WorkOrder.objects.filter(work_order_number=number).exists():
                return number

    def save(self, *args, **kwargs):
        """Override save method to generate slug if not set"""
        if not self.slug:
            self.slug = self.prepopulate_slug()
            
        if not self.work_order_number:
            self.work_order_number = self.generate_unique_work_order_number()
            
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Work Order: {self.type} - {self.work_order_number}"

    class Meta:
        verbose_name = "Work Order"
        verbose_name_plural = "Work Orders"


class WorkOrderQuoteLine(models.Model):
    """One priced line of a five-stage Work Order: what the vendor charges and what the client is billed."""

    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE, related_name='quote_lines')
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=1)
    unit_cost_vendor = models.DecimalField(max_digits=18, decimal_places=2)
    unit_cost_client = models.DecimalField(max_digits=18, decimal_places=2)

    class Meta:
        ordering = ['id']

    @property
    def total_vendor(self):
        return self.quantity * self.unit_cost_vendor

    @property
    def total_client(self):
        return self.quantity * self.unit_cost_client

    def __str__(self):
        return f"{self.description} × {self.quantity}"
