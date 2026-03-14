from django.db import models
from accounts.models import User
from datetime import timedelta
from django.utils import timezone

class Onboarding(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='onboarding')
    token = models.CharField(max_length=36, unique=True)
    is_onboarded = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Onboarding for {self.user.email}"
    
    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(days=7)