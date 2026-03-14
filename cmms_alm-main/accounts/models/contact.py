from utils.models import Dated, Status, OwnerPrivModel
from django.db import models
from django.utils.translation import gettext_lazy as _

class Contact(OwnerPrivModel, Dated, Status, models.Model):
    """
    Represents a contact person associated with a client.
    """

    first_name = models.CharField(
        max_length=100,
        help_text="First name of the contact person."
    )

    last_name = models.CharField(
        max_length=100,
        help_text="Last name of the contact person."
    )

    email = models.EmailField(
        max_length=60,
        help_text="Email address of the contact person."
    )

    phone = models.CharField(
        max_length=15,
        blank=True, null=True,
        help_text="Phone number of the contact person."
    )

    status = models.CharField(
        max_length=20,
        choices=[('Active', _('Active')), ('Inactive', _('Inactive'))],
        default='Active',
        help_text="Status of the contact."
    )
    
    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f"{self.first_name} {self.last_name} "
