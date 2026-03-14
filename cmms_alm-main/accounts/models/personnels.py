import uuid
import random
import string
from django.utils.translation import gettext_lazy as _
from django.db import models
from django.utils.text import slugify
from django.conf import settings  # To reference the User model

from utils.models import UserPrivModel, Dated, Status, FileAttachment, OwnerPrivModel

class Personnel(UserPrivModel, OwnerPrivModel, Dated, Status, models.Model):
    
    def avatar_upload_location(instance, filename):
        file_path = 'personnel/images/{id}/{filename}'.format(
        id=str(instance.id), filename=filename)
        return file_path
    
    """
    Represents a personnel record with details such as staff number, name, facility, and contact information.

    Attributes:
        staff_number: The unique identifier for the personnel.
        facility: The facility the personnel is assigned to.
        profile_picture: A profile picture of the personnel.
    """
    
    staff_number = models.CharField(
        max_length=50,
        unique=True,
        help_text=_("Unique identifier for the personnel.")
    )
    slug = models.SlugField(
        max_length=255,
        unique=True,
        blank=True,
        help_text=_("Unique slugified identifier for the user.")
    )
    facility = models.ForeignKey(
        'facility.Facility',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text=_("The facility the personnel is assigned to.")
    )
    email = models.EmailField(
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Email address of the personnel.")
    )
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        help_text=_("Contact phone number of the personnel.")
    )
    avatar = models.ImageField(
        upload_to=avatar_upload_location,
        default='avatar.png', 
        blank=True,
        null=True,
        help_text=_("Profile picture of the personnel.")
    )
    
    documents = models.ManyToManyField(FileAttachment, blank=True, related_name='personnel_documents')
    
    access_to_all_categories = models.BooleanField(
        default=False,
        help_text=_("Indicates if the user has access to all wos categories.")
    )
    
    categories = models.ManyToManyField(
        'accounts.Category',
        blank=True,
        related_name='personnel_categories',
        help_text=_("Work Order categories the user is assigned to.")
    )
    
    @property
    def first_name(self):
        """
        Returns the first name of the personnel.
        """
        return self.user.first_name
    
    @property
    def last_name(self):
        """
        Returns the last name of the personnel.
        """
        return self.user.last_name
    
    @property
    def avatar_url(self):
        """
        Returns the URL of the personnel's avatar.
        """
        if self.avatar:
            return self.avatar.url
        return None
    
    # @property
    # def email(self):
    #     """
    #     Returns the email address of the personnel.
    #     """
    #     return self.user.email
    
    # @property
    # def phone_number(self):
    #     """
    #     Returns the phone number of the personnel.
    #     """
    #     return self.user.phone
    
    def save(self, *args, **kwargs):
        # Generate a unique slug before saving
        if not self.slug:
            base_slug = slugify(self.user.name)  # Use the name property to generate the slug
            slug = base_slug
            counter = 0
            while Personnel.objects.filter(slug=slug).exists():
                # Append random characters to make the slug unique
                counter += 1
                random_suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=4))
                slug = f"{base_slug}-{random_suffix}"

            self.slug = slug

        super().save(*args, **kwargs)
        
    class Meta:
        ordering = ['-id']

    def __str__(self):
        """
        Returns a string representation of the personnel.
        """
        return f"{self.user.first_name} {self.user.last_name} ({self.staff_number})"
