from django.db import models
from django.conf import settings


class OwnerPrivModel(models.Model):
  
    class Meta:
        abstract = True

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='%(app_label)s_%(class)s_owner',
        help_text='e.g == %(app_label)s_%(class)s',
        null=True,
        blank=True
    )
