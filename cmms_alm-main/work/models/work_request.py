import random
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.contrib.contenttypes.fields import GenericRelation
from django.utils.translation import gettext_lazy as _

from utils.models import UserPrivModel, Dated, OwnerPrivModel, FileAttachment, Status




class WorkRequest(OwnerPrivModel, Dated, models.Model):
    
    """
    Represents a work request with details about the request, requester, and associated entities.
    """
    
    WORK_TYPES = [
        ("Planned", "Planned"),
        ("Unplanned", "Unplanned"),
    ]

    APPROVAL_STATUSES = [
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
    ]

    PRIORITY_LEVELS = [
        ("Low", "Low"),
        ("Medium", "Medium"),
        ("High", "High"),
    ]

    CURRENCY_CHOICES = [
        ("USD", "USD"),
        ("EUR", "EUR"),
        ("NGN", "NGN"),
    ]

    type = models.CharField(
        max_length=255, choices=[("Work", _("Work")), ("Procument", _("Procument"))],
        help_text=_("Type of the work request.")
    )
    
    category = models.ForeignKey(
        'asset_inventory.AssetCategory',
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='work_requests',
        help_text=_("Category of the work request.")
    )
    
    work_request_number = models.CharField(
        max_length=7,
        # unique=True,
        blank=True,
        help_text=_("Unique 7-digit work request number.")
    )
    
    slug = models.SlugField(
        max_length=300,
        unique=True,
        blank=True, 
        help_text=_("Auto-generated unique slug for the work request.")
    )
    
    subcategory = models.ForeignKey(
        'asset_inventory.AssetSubCategory',
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='work_requests',
        help_text=_("Subcategory of the work request.")
    )
    
    department = models.ForeignKey(
        'accounts.Department',
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='work_requests',
        help_text="Department associated with the work request."
    )
    
    require_mobilization_fee = models.BooleanField(
        default=False,
        help_text="Indicates if a Mobilization Fee is required for the request."
    )
    
    description = models.TextField(
        blank=True, null=True,
        help_text="Brief description of the work request."
    )
    
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_LEVELS,
        default="Medium",
        help_text="Priority level of the work request."
    )
    
    attachment = models.FileField(
        upload_to='work_requests/attachments/',
        blank=True, null=True,
        help_text="File attachment for the work request."
    )
    
    require_quotation = models.BooleanField(
        default=True
    )
    
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='work_requests',
        help_text="User who made the request."
    )
    
    request_to = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='work_request_to',
        help_text="Users who made the request."
    )
    
    facility = models.ForeignKey(
        'facility.Facility',
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='work_requests',
        help_text="Facility associated with the work request."
    )

    building = models.ForeignKey(
        'facility.Building',
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='work_requests_buildings',
        help_text="building associated with the work request."
    )
    
    asset = models.ForeignKey(
        'asset_inventory.Asset',
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='work_requests_assets',
        help_text="Asset associated with the work request."
    )
    
    approval_status = models.CharField(
        max_length=10,
        choices=APPROVAL_STATUSES,
        default="Pending",
        help_text="Approval status of the work request."
    )

    follow_up_notes = models.TextField(
        blank=True, null=True,
        help_text="Notes for follow-ups related to the work request."
    )

    payment_requisition = models.BooleanField(
        default=False,
        help_text="Indicates if a payment requisition should be created."
    )

    invoice_no = models.CharField(
        max_length=50,
        blank=True, null=True,
        help_text="Invoice number associated with the work request."
    )

    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default="USD",
        help_text="Currency for the work request."
    )
    
    cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True, null=True,
        help_text="Cost of the work request."
    )

    add_discount = models.BooleanField(
        default=False,
        help_text="Indicates if a discount should be applied."
    )

    exclude_management_fee = models.BooleanField(
        default=False,
        help_text="Indicates if the management fee should be excluded."
    )

    resources = GenericRelation(
        FileAttachment,
        related_query_name='work_request_resources',
        help_text="Resources attached to the work request."
    )

    files = GenericRelation(
        FileAttachment,
        related_query_name='work_request_files',
        help_text="Files attached to the work request."
    )

    def attach_file(self, file_instance):
        """
        Attach a file to the work request.
        """
        file_instance.content_object = self
        file_instance.save()

    def get_attached_files(self):
        """
        Retrieve all attached files.
        """
        return self.files.all()
    
    def prepopulate_slug(self):
        """Generate a unique slug from the work request type"""
        base_slug = slugify(self.type)
        unique_slug = base_slug
        num = 1
        while WorkRequest.objects.filter(slug=unique_slug).exists():
            unique_slug = f"{base_slug}-{num}"
            num += 1
        return unique_slug
    
    def generate_unique_work_request_number(self):
        """Generate a unique 7-digit work request number."""
        while True:
            number = str(random.randint(1000000, 9999999))  # Generate 7-digit number
            if not WorkRequest.objects.filter(work_request_number=number).exists():
                return number

    def save(self, *args, **kwargs):
        """Override save method to generate slug if not set"""
        if not self.slug:
            self.slug = self.prepopulate_slug()
            
        if not self.work_request_number:
            self.work_request_number = self.generate_unique_work_request_number()
            
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Work Request: {self.type} - {self.requester}"
