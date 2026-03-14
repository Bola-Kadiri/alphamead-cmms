from django.db import models
from django.utils.translation import gettext_lazy as _
from utils.models import UserPrivModel, Dated

from utils.models import OwnerPrivModel, Dated, Status



class Category(OwnerPrivModel, Dated, Status, models.Model):
    """
    Represents a category with configurable settings and details.
    """
    
    WORK_REQUEST_CHOICES = [
        ('create_work_order', _('Create work order')),
        ('close_work_request', _('Close work request')),
    ]
    
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique code for the category."
    )
    
    title = models.CharField(
        max_length=255,
        blank=True, null=True
    )
    
    description = models.TextField(
        blank=True, null=True,
        help_text="Description of the category."
    )
    
    problem_type = models.TextField(
        blank=True, null=True,
        help_text="Defines the problem type associated with this category."
    )
    
    
    work_request_approved = models.CharField(
        max_length=50,
        choices=WORK_REQUEST_CHOICES,
        blank=True, null=True,
        help_text="Defines the action to be taken when a work request is approved."
    )
    
    exclude_costing_limit = models.BooleanField(
        default=False,
        help_text="Whether to exclude costing limit for this category."
    )
    
    power = models.BooleanField(
        default=False,
        help_text="Indicates if this category has power configurations."
    )
    
    create_payment_requisition = models.BooleanField(
        default=False,
        help_text="Determines if payment requisition is auto-created for this category."
    )
    
    class Meta:
        verbose_name = _('Category')
        verbose_name_plural = _('Categories')
    
    def __str__(self):
        return self.code


class Subcategory(OwnerPrivModel, Dated, Status, models.Model):
    """
    Represents a subcategory under a specific category.
    """
    
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE,
        help_text=_("Category to which the subcategory belongs.")
    )
    
    title = models.CharField(
        max_length=255,
        blank=True, null=True
    )
    
    description = models.TextField(
        blank=True, null=True,
        help_text=_("Description of the subcategory.")
    )
    
    exclude_costing_limit = models.BooleanField(
        default=False,
        help_text=_("Whether to exclude costing limit for this subcategory.")
    )
    
    status = models.CharField(
        max_length=50,
        choices=[('Active', _('Active')), ('Inactive', _('Inactive'))],
        blank=True, null=True,
        help_text=_("Status of the subcategory.")
    )
    
    class Meta:
        ordering = ['-id']
        verbose_name = _('SubCategory')
        verbose_name_plural = _('Sub Category')
    

    def __str__(self):
        return self.category.code
