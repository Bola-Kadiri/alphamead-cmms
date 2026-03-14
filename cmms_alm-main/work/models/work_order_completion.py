from django.db import models
from work.models.work_order import WorkOrder

from utils.models import OwnerPrivModel, Dated

class WorkOrderCompletion(OwnerPrivModel, Dated, models.Model):
    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE, related_name='completions')
    file = models.FileField(upload_to='work_order_completions/', blank=True, null=True)

    def __str__(self):
        return f"Completion for {self.work_order}" 