
import random
import string
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from utils.models import UserPrivModel, Dated, Status, OwnerPrivModel


class ContactDetails(Status, models.Model):
    """
    Represents contact details for a vendor.
    """
    
    first_name = models.CharField(
      max_length=255, help_text=_("Contact's first name.")
    )
    
    last_name = models.CharField(
      max_length=255, help_text=_("Contact's last name.")
    )
    
    phone = models.CharField(
      max_length=15, help_text=_("Contact's phone number.")
    )
    
    email = models.EmailField(
      help_text=_("Contact's email address.")
    )

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Document(models.Model):
    """
    Represents a document related to a vendor.
    """
    def document_upload_location(instance, filename):
        file_path = f'document/{instance.id}/{filename}'
        return file_path
      
    file = models.FileField(
      upload_to=document_upload_location, 
      help_text=_("Document file.")
    )
    
    description = models.TextField(
      blank=True, null=True, help_text=_("Description of the document.")
    )

    def __str__(self):
        return f"Document {self.id}"


class Contract(models.Model):
    """
    Represents a contract associated with a vendor.
    """
    
    def contract_upload_location(instance, filename):
        file_path = f'contract/{instance.id}/{filename}'
        return file_path
      
      
    contract_number = models.CharField(
      max_length=50, help_text=_("Contract number.")
    )
    
    start_date = models.DateField(
      help_text=_("Start date of the contract.")
    )
    
    end_date = models.DateField(
      help_text=_("End date of the contract.")
    )
    
    access_to_all_facilities = models.BooleanField(
      default=False, help_text=_("Access to all facilities.")
    )
    
    attachment = models.FileField(
      upload_to=contract_upload_location, 
      blank=True, null=True, help_text=_("Attachment file.")
    )

    def __str__(self):
        return self.contract_number



class Vendor(OwnerPrivModel, Dated, Status, models.Model):
    """
    Represents a vendor with bank account details.
    """

    VENDOR_TYPE_CHOICES = [
        ('Individual', _('Individual')),
        ('Company', _('Company'))
    ]

    CURRENCY_CHOICES = [
        ('NGN', _('Nigerian Naira')),
        ('USD', _('US Dollar')),
        ('EUR', _('Euro')),
        ('GBP', _('British Pound')),
    ]

    # About Section
    name = models.CharField(max_length=255, help_text=_("Vendor's name."))
    type = models.CharField(max_length=50, choices=VENDOR_TYPE_CHOICES, help_text=_("Type of vendor."))
    slug = models.SlugField(unique=True, blank=True) 

    # Contact Details
    phone = models.CharField(max_length=15, help_text=_("Vendor's phone number."))
    email = models.EmailField(help_text=_("Vendor's email address."), null=True, blank=True)

    # Account Details
    account_name = models.CharField(max_length=255, help_text=_("Bank account name."))
    bank = models.CharField(max_length=255, help_text=_("Bank name."))
    account_number = models.CharField(max_length=20, unique=True, help_text=_("Bank account number."))
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, help_text=_("Account currency."))
    
    
    def save(self, *args, **kwargs):
        """
        Generate a unique slug before saving.
        """
        if not self.slug:  # Only generate slug if it's empty
            base_slug = slugify(self.name)
            slug = base_slug
            while Vendor.objects.filter(slug=slug).exists():
                random_chars = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
                slug = f"{base_slug}-{random_chars}"
            self.slug = slug

        super().save(*args, **kwargs)
        
    class Meta:
        ordering = ['-id']

    def __str__(self):
      return f"{self.name} ({self.account_name} - {self.bank})"
