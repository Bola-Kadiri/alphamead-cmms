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
    ]

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
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
    ]

    CURRENCY_CHOICES = [
        ("USD", "USD"),
        ("EUR", "EUR"),
        ("NGN", "NGN"),
    ]

    type = models.CharField(
        max_length=50,
        choices=TYPE_CHOICES,
        help_text="Type of the work order.",
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
        on_delete=models.CASCADE,
        related_name='work_orders_facility',
        help_text="Facility or location associated with the work order."
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
        'accounts.Category',
        on_delete=models.CASCADE,
        help_text="Category of the work order."
    )
    
    subcategory = models.ForeignKey(
        'accounts.Subcategory',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='work_orders_subcategory',
        help_text="Subcategory of the work order."
    )
    
    department = models.ForeignKey(
       'accounts.Department',
        on_delete=models.CASCADE,
        null=True,
        help_text="Department handling the work order."
    )
    
    priority = models.CharField(
        max_length=50,
        choices=PRIORITY_CHOICES,
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
        on_delete=models.CASCADE, 
        help_text="User to whom the approval request is sent.",
    )
    
    is_approved = models.BooleanField(
        default=False, 
        help_text="Indicates whether the request is approved."
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
        max_length=10,
        choices=APPROVAL_STATUSES,
        default="Pending",
        help_text="Approval status of the work order."
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
    
    def prepopulate_slug(self):
        """Generate a unique slug from the work request type"""
        base_slug = slugify(self.type)
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
        return f"Work Order: {self.type} - {self.requester}"

    class Meta:
        verbose_name = "Work Order"
        verbose_name_plural = "Work Orders"

    def __str__(self):
        return self.title
