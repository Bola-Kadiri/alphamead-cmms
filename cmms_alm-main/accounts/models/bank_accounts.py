import random
import string

from django.db import models
from django.utils.text import slugify

from utils.models import UserPrivModel, Dated, Status, OwnerPrivModel


class BankAccount(OwnerPrivModel, Dated, Status,  models.Model):
    """
    Represents a bank account with associated details such as bank, account name, number, currency, and more.
    """
    
    CURRENCY_CHOICES = [
        ('NGN', 'Nigerian Naira'),
        ('USD', 'US Dollar'),
        ('EUR', 'Euro'),
        ('GBP', 'British Pound')
    ]
    
    bank = models.CharField(
        max_length=255,
        help_text="The bank associated with the account."
    )
    
    account_name = models.CharField(
        max_length=255,
        help_text="Name of the account holder."
    )
    
    slug = models.SlugField(
        max_length=255,
        unique=True,
        blank=True,
        help_text="Unique slugified identifier for the user."
    )
    
    account_number = models.CharField(
        max_length=20,
        unique=True,
        help_text="Account number for the bank account."
    )
    
    currency = models.CharField(
        max_length=50,
        choices=CURRENCY_CHOICES,
        help_text="Currency associated with the account."
    )
    
    address = models.TextField(
        blank=True, null=True,
        help_text="Address associated with the account."
    )
    
    details = models.TextField(
        blank=True, null=True,
        help_text="Additional details about the account."
    )
    
    def save(self, *args, **kwargs):
        # Generate a unique slug before saving
        if not self.slug:
            base_slug = slugify(self.account_name)  # Use the name property to generate the slug
            slug = base_slug
            counter = 0
            while BankAccount.objects.filter(slug=slug).exists():
                # Append random characters to make the slug unique
                counter += 1
                random_suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=4))
                slug = f"{base_slug}-{random_suffix}"

            self.slug = slug

        super().save(*args, **kwargs)
        
    class Meta:
        ordering = ['-id']
    
    def __str__(self):
        return f"{self.account_name} - {self.account_number}"
