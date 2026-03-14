from django.db import models
from django.conf import settings


class UserPrivModel(models.Model):
  
    class Meta:
        abstract = True

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='%(app_label)s_%(class)s',
        help_text='e.g == %(app_label)s_%(class)s',
    )
