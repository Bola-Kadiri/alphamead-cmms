# APPROACH 1: Using Django's Built-in Translation System (gettext)
# This is the most common approach for static translations

# 1. First, update your models to use translation markers
# models.py

from django.db import models
from django.utils.translation import gettext_lazy as _

class Category(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    owner = models.ForeignKey('User', on_delete=models.CASCADE)
    
    class Meta:
        verbose_name = _('Category')
        verbose_name_plural = _('Categories')
    
    def __str__(self):
        return self.name

class Department(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    owner = models.ForeignKey('User', on_delete=models.CASCADE)
    
    class Meta:
        verbose_name = _('Department')
        verbose_name_plural = _('Departments')


from utils.mixin import TranslatedSerializerMixin

class CategorySerializer(TranslatedSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'created_at', 'updated_at']
        translatable_fields = ['name', 'description']

class DepartmentSerializer(TranslatedSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'code', 'name', 'created_at', 'updated_at']
        translatable_fields = ['name']

