import uuid
import random
import string
from django.utils.translation import gettext_lazy as _

from django.db import models
from django.utils.text import slugify

from utils.models import UserPrivModel, Dated, OwnerPrivModel, Status


class Client(OwnerPrivModel, Dated, Status, models.Model):
  
    """
    Represents a client record with fields for general information and contact details.
    """
    
    TYPE_CHOICES = [
        ('Individual',_('Individual')),
        ('Company',_('Company'))
    ]
    
    slug = models.SlugField(
        max_length=255,
        unique=True,
        help_text="Unique slug for the client."
    )
    
    type = models.CharField(
        max_length=50,
        choices=TYPE_CHOICES,
        help_text="Type of the client (Individual or Company)."
    )
    
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique code for the client."
    )
    
    name = models.CharField(
        max_length=255,
        help_text="Name of the client."
    )
    
    email = models.EmailField(
        blank=True, null=True,
        help_text="Email address of the client."
    )
    
    phone = models.CharField(
        max_length=15,
        blank=True, null=True,
        help_text="Contact phone number of the client."
    )
    
    group = models.CharField(
        max_length=255,
        blank=True, null=True,
        help_text="Group the client belongs to."
    )
    
    address = models.TextField(
        blank=True, null=True,
        help_text="Address of the client."
    )
    
    contacts = models.ManyToManyField(
        "accounts.Contact",
        related_name="clients",
        blank=True,
        help_text="Contacts associated with this client."
    )

    
    def save(self, *args, **kwargs):
      # Generate a unique slug before saving
        if not self.slug:
            base_slug = slugify(self.name)  # Use the name property to generate the slug
            slug = base_slug
            counter = 0
            while Client.objects.filter(slug=slug).exists():
                # Append random characters to make the slug unique
                counter += 1
                random_suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=4))
                slug = f"{base_slug}-{random_suffix}"

            self.slug = slug

        # Call the superclass save method to actually save the instance
        super().save(*args, **kwargs)
        
    class Meta:
        ordering = ['-id']


    def __str__(self):
      name = self.name if self.name else ''
      return name