from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from utils.models import UserPrivModel, Dated, Status, OwnerPrivModel

class ApartmentType(OwnerPrivModel, Dated, Status, models.Model):
    """
    Represents different types of apartment facilities.
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text=_("Name of the apartment type (e.g., Studio, 1-bedroom, 2-bedroom, etc.).")
    )
    
    slug = models.SlugField(
        max_length=120,
        unique=True,
        blank=True,
        help_text=_("Auto-generated slug for the apartment type.")
    )
    
    def save(self, *args, **kwargs):
        """
        Auto-generate slug from name if not provided.
        """
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name} - {self.status}"
