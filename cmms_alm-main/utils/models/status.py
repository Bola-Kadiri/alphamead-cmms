from django.db import models


class Status(models.Model):
  
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive')
    ]
  
    class Meta:
        abstract = True
        
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='Active',
        help_text="Status of the client."
    )
    