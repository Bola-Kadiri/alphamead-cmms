from django.db import models

  
class Translation(models.Model):
    """
    Generic translation model for any content
    """
    content_type = models.CharField(max_length=100)  # e.g., 'category', 'department'
    object_id = models.PositiveIntegerField()
    field_name = models.CharField(max_length=100)  # e.g., 'name', 'description'
    language = models.CharField(max_length=10)  # e.g., 'en', 'fr'
    translated_text = models.TextField()
    
    class Meta:
        unique_together = ['content_type', 'object_id', 'field_name', 'language']
        indexes = [
            models.Index(fields=['content_type', 'object_id', 'language']),
        ]
    
    def __str__(self):
        return f"{self.content_type}:{self.object_id}:{self.field_name}:{self.language}"
      
      
  