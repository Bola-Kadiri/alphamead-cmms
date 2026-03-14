from django.db import models
from django.contrib.contenttypes.fields import GenericRelation
from django.utils.translation import gettext_lazy as _

from accounts.models import User, Category, Subcategory
# from asset_inventory.models import AssetCategory, AssetSubCategory
from .item import Item
from utils.models import UserPrivModel, Dated, Status, FileAttachment, ImageAttachment

class Transfer(UserPrivModel, Dated, models.Model):
    TRANSFER_TYPE_CHOICES = [
        ('transfer', _('Transfer')),
        ('return', _('Return')),
    ]

    # 1. Request From (store or warehouse)
    request_from = models.ForeignKey(
        'asset_inventory.Store',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transfer_requests_from',
        help_text=_("Store or warehouse initiating the request")
    )

    # 2. Required Date
    required_date = models.DateField(null=True, blank=True)

    # 3. Request By (facility staff)
    requested_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transfer_requested_by',
        help_text=_("Staff member making the request")
    )

    # 4. Transfer To Store
    transfer_to = models.ForeignKey(
        'asset_inventory.Store',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transfer_to_store',
        help_text=_("Destination store or warehouse")
    )

    # 5. Type
    type = models.CharField(
        max_length=20,
        choices=TRANSFER_TYPE_CHOICES,
        default='transfer',
        help_text=_("Transfer type (transfer or return)")
    )

    category = models.ForeignKey(
        'asset_inventory.AssetCategory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    subcategory = models.ForeignKey(
        'asset_inventory.AssetSubCategory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # 6. Category & Subcategory
    # category = models.ForeignKey(
    #     Category,
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True
    # )
    # subcategory = models.ForeignKey(
    #     Subcategory,
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True
    # )

    # 7. Show list of available items from selected store
    # This would be populated via logic in views/forms using the `request_from` store
    items = models.ManyToManyField(
        Item,
        blank=True,
        related_name='transfer_items'
    )

    # 8. Request Confirmation from requester (select users)
    confirmation_required_from = models.ManyToManyField(
        User,
        blank=True,
        related_name='transfer_confirmations',
        help_text=_("Users who need to confirm this transfer")
    )

    def __str__(self):
        return f"Transfer #{self.id} - {self.type}"