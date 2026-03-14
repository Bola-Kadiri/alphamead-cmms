import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _

# from . import Store, InventoryReference
from accounts.models import User, Category, Subcategory, Department
from facility.models import Facility, Building 
class Item(models.Model):
    """Placeholder for your existing Item model"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    # Add your actual fields...
    
    def __str__(self):
        return self.name
    
class ItemRequest(models.Model):
    def upload_location(instance, filename):
        # Use instance.id if available, otherwise use UUID
        identifier = str(instance.id) if instance.id else str(uuid.uuid4())
        file_path = f'items/documents/{identifier}/{filename}'
        return file_path

    name = models.CharField(max_length=100, default="New Inventory Request")  # Default name for clarity
    description = models.TextField(blank=True, null=True)
    request_from = models.ForeignKey("asset_inventory.Store", on_delete=models.SET_NULL, null=True, blank=True)
    required_date = models.DateField(null=True, blank=True)
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='requested_items')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    type = models.CharField(max_length=20, default="for_use", choices=[
        ('for_use', 'For Use'),
        ('for_store', 'For Store')
    ])
    facility = models.ForeignKey(Facility, on_delete=models.SET_NULL, null=True, blank=True)
    building = models.ForeignKey(Building, on_delete=models.SET_NULL, null=True, blank=True)
    comment = models.TextField(blank=True, null=True)
    file = models.FileField(
        upload_to=upload_location,
        blank=True,
        null=True,
        help_text=_('Upload a document (e.g., PDF, DOCX, etc.)')
    )
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_items')
    items = models.ManyToManyField(Item, through='ItemRequestItem', blank=True)  # New field for multiple items
    status = models.CharField(max_length=20, default='Submitted', choices=[
        ('Submitted', 'Submitted'),
        ('Pending Approval', 'Pending Approval'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected')
    ])

    def __str__(self):
        return self.name
    
    def approve(self, user, status):
        """Approve or reject the item request."""
        if status not in dict(self._meta.get_field('status').choices):
            raise ValueError("Invalid status value")
        if status in ['Approved', 'Rejected'] and not self.status == 'Pending Approval':
            raise ValueError("Can only approve or reject from Pending Approval status")
        self.status = status
        if status in ['Approved', 'Rejected']:
            self.approved_by = user
        self.save()

class ItemRequestItem(models.Model):
    item_request = models.ForeignKey(ItemRequest, on_delete=models.CASCADE,)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey('asset_inventory.AssetCategory', on_delete=models.SET_NULL, null=True, blank=True)
    subcategory = models.ForeignKey('asset_inventory.AssetSubCategory', on_delete=models.SET_NULL, null=True, blank=True)
    model = models.ForeignKey('asset_inventory.ModelReference', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ('item_request', 'item')

