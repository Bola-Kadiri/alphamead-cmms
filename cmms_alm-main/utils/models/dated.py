import uuid

from django.db import models
from django.utils import timezone
from django.conf import settings


class Dated(models.Model):
  
    created_at = models.DateTimeField(
        null=True, blank=True,
        auto_now_add=True, editable=False,
    )
    updated_at = models.DateTimeField(
        null=True, blank=True,
        auto_now=True, db_index=True,
    )

    class Meta:
        abstract = True


class UniqueID(models.Model):
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True
    )

    class Meta:
        abstract = True