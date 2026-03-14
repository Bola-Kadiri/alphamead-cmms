from rest_framework import serializers
from .service import TranslationService
from django.utils.translation import get_language
from django.conf import settings
from rest_framework.response import Response

class TranslatedSerializerMixin:
    """
    Mixin to add translation support to serializers
    """
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        
        # Get current language
        language = get_language()
        
        # Skip if it's the default language
        if language == settings.LANGUAGE_CODE:
            return data
        
        # Get translatable fields from Meta
        if hasattr(self.Meta, 'translatable_fields'):
            model_name = instance.__class__.__name__
            
            # Get translations for all fields at once (optimized)
            translations = TranslationService.get_translations_bulk(
                model_name,
                [instance.id],
                self.Meta.translatable_fields,
                language
            )
            
            # Apply translations
            for field in self.Meta.translatable_fields:
                key = (instance.id, field)
                if key in translations:
                    data[field] = translations[key]
        
        return data
    
    def to_internal_value(self, data):
        # Store the raw data for translation saving
        self._raw_data = data.copy()
        return super().to_internal_value(data)
    
    def create(self, validated_data):
        instance = super().create(validated_data)
        
        # Save translations if not default language
        language = get_language()
        if language != settings.LANGUAGE_CODE and hasattr(self, '_raw_data'):
            model_name = instance.__class__.__name__
            
            for field in getattr(self.Meta, 'translatable_fields', []):
                if field in self._raw_data:
                    TranslationService.set_translation(
                        model_name,
                        instance.id,
                        field,
                        language,
                        self._raw_data[field]
                    )
        
        return instance
    
    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        
        # Update translations
        language = get_language()
        if language != settings.LANGUAGE_CODE and hasattr(self, '_raw_data'):
            model_name = instance.__class__.__name__
            
            for field in getattr(self.Meta, 'translatable_fields', []):
                if field in self._raw_data:
                    TranslationService.set_translation(
                        model_name,
                        instance.id,
                        field,
                        language,
                        self._raw_data[field]
                    )
        
        return instance


class OptimizedTranslationMixin:
    """
    Optimized mixin for viewsets to handle bulk translations
    """
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            data = serializer.data
            
            # Bulk load translations
            language = get_language()
            if language != settings.LANGUAGE_CODE and hasattr(serializer.child.Meta, 'translatable_fields'):
                model_name = queryset.model.__name__
                object_ids = [item['id'] for item in data]
                fields = serializer.child.Meta.translatable_fields
                
                translations = TranslationService.get_translations_bulk(
                    model_name, object_ids, fields, language
                )
                
                # Apply translations to data
                for item in data:
                    for field in fields:
                        key = (item['id'], field)
                        if key in translations:
                            item[field] = translations[key]
            
            return self.get_paginated_response(data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)