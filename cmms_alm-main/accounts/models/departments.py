from django.db import models
from django.conf import settings

from utils.models import Dated, Status, OwnerPrivModel


class Department(OwnerPrivModel, Dated, Status, models.Model):
    """
    Represents a department with details such as code, name, status, emails, and phone numbers.
    """
    
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique code for the department."
    )
    
    name = models.CharField(
        max_length=255,
        help_text="Name of the department."
    )
    
    email = models.EmailField(
        max_length=60,
        unique=True,
        help_text="Email address of the user."
    )
    
    phone = models.CharField(
        max_length=15,
        blank=True, null=True,
        help_text="Phone number of the user."
    )
    
    class Meta:
        ordering = ['-id']
    
    def __str__(self):
        return self.name
