from django.utils.translation import get_language
from django.conf import settings
from utils.models import Translation
from django.core.cache import cache

class TranslationService:
    @staticmethod
    def get_translation(model_name, object_id, field_name, language=None):
        """
        Get translation for a specific field
        """
        if language is None:
            language = get_language()
        
        # Cache key
        cache_key = f"translation:{model_name}:{object_id}:{field_name}:{language}"
        
        # Check cache first
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        
        try:
            translation = Translation.objects.get(
                content_type=model_name.lower(),
                object_id=object_id,
                field_name=field_name,
                language=language
            )
            cache.set(cache_key, translation.translated_text, 3600)  # Cache for 1 hour
            return translation.translated_text
        except Translation.DoesNotExist:
            return None
    
    @staticmethod
    def set_translation(model_name, object_id, field_name, language, text):
        """
        Set or update translation
        """
        translation, created = Translation.objects.update_or_create(
            content_type=model_name.lower(),
            object_id=object_id,
            field_name=field_name,
            language=language,
            defaults={'translated_text': text}
        )
        
        # Clear cache
        cache_key = f"translation:{model_name}:{object_id}:{field_name}:{language}"
        cache.delete(cache_key)
        
        return translation
    
    @staticmethod
    def get_translations_bulk(model_name, object_ids, field_names, language=None):
        """
        Get translations for multiple objects at once (optimized)
        """
        if language is None:
            language = get_language()
        
        translations = Translation.objects.filter(
            content_type=model_name.lower(),
            object_id__in=object_ids,
            field_name__in=field_names,
            language=language
        )
        
        # Create a dictionary for quick lookup
        trans_dict = {}
        for trans in translations:
            key = (trans.object_id, trans.field_name)
            trans_dict[key] = trans.translated_text
        
        return trans_dict
