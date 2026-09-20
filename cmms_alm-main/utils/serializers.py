from django.contrib.auth.signals import user_logged_in
from django.contrib.contenttypes.models import ContentType
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers

from .models import ImageAttachment, FileAttachment

# class ImageAttachmentSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = ImageAttachment
#         fields = ['content_type', 'object_id', 'file']

class ImageAttachmentSerializer(serializers.ModelSerializer):
    # Add content_type and object_id fields if you want to explicitly set these in your requests
    file = serializers.ImageField(max_length=None, use_url=True)

    content_type = serializers.SlugRelatedField(
        queryset=ContentType.objects.all(),
        slug_field='model'  # or 'app_label' depending on your needs
    )
    object_id = serializers.IntegerField()

    class Meta:
        model = ImageAttachment
        fields = ['id', 'content_type', 'object_id', 'file']

class FileAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileAttachment
        fields = ['content_type', 'object_id', 'file']

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims
        token['email'] = user.email
        token['name'] = f"{user.first_name} {user.last_name}"
        token['role'] = user.roles
        token['slug'] = user.slug
        # A JWT login is a login too — emit the same signal the session
        # based web login sends, so both paths feed report.signals'
        # single login-tracking receiver (used by the User Facility
        # Report's login count).
        user_logged_in.send(sender=user.__class__, request=None, user=user)
        return token
