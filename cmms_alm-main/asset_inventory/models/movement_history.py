import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from accounts.models import User
from asset_inventory.models import Inventory, Store

class MovementHistory(models.Model):
    item_no = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    inventory = models.ForeignKey(Inventory, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Move By')
    model = models.CharField(max_length=100, null=True, blank=True)
    movement_date = models.DateTimeField(auto_now_add=True)
    from_store = models.ForeignKey(Store, on_delete=models.SET_NULL, null=True, blank=True, related_name='movement_from_store')
    to_store = models.ForeignKey(Store, on_delete=models.SET_NULL, null=True, blank=True, related_name='movement_to_store')
    transfer_quantity = models.IntegerField()
    transfer_unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    transfer_amount = models.DecimalField(max_digits=15, decimal_places=2)
    description = models.TextField(null=True, blank=True)

    def save(self, *args, **kwargs):
        # Auto-calculate transfer_amount if not set
        if not self.transfer_amount:
            self.transfer_amount = (self.transfer_quantity or 0) * (self.transfer_unit_price or 0)
        super().save(*args, **kwargs)

