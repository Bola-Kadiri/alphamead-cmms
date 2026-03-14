from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


def image_upload_location(instance, filename):
    # 'profile/images/{id}/{filename}'
    return f'profile/images/{instance.object_id}/{filename}'

class ImageAttachment(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    file = models.ImageField(
        'Image',
        upload_to=image_upload_location,
    )

    def to_json(self):
        """
        Serialize the instance for JSON.
        """
        return {
            "id": self.id,
            "content_type": self.content_type_id,  # You might want to use a string representation or similar
            "object_id": self.object_id,
            "file_url": self.file.url if self.file else None,
        }

    def __str__(self):
        return str(self.file)

def file_upload_location(instance, filename):
    # 'file-attachments/{id}/{filename}'
    return f'file-attachments/{instance.object_id}/{filename}'


class FileAttachment(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    file = models.FileField(upload_to=file_upload_location)

    def to_json(self):
        """
        Serialize the instance for JSON.
        """
        return {
            "id": self.id,
            "content_type": self.content_type_id,  # You might want to use a string representation or similar
            "object_id": self.object_id,
            "file_url": self.file.url if self.file else None,
        }

    def __str__(self):
        return str(self.file)
