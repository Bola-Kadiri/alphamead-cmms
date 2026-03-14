from django.conf import settings
from django.utils.translation import get_language
from rest_framework import serializers


class TranslatableFieldMixin:
    # Optional: Define required languages or default behavior in Meta
    # Example: Meta.required_languages = ['en'] or Meta.default_language = 'en'
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dynamically add SerializerMethodField for each translatable field
        for field in getattr(self.Meta, 'translatable_fields', []):
            self.fields[field] = serializers.SerializerMethodField()

    def get_translatable_field(self, obj, field_name):
        lang = get_language()
        return getattr(obj, f'{field_name}_{lang}')

    def __getattribute__(self, name):
        # Dynamically generate get_<field> methods for translatable fields
        if name.startswith('get_') and hasattr(self.Meta, 'translatable_fields'):
            field_name = name[4:]
            if field_name in self.Meta.translatable_fields:
                return lambda obj: self.get_translatable_field(obj, field_name)
        return super().__getattribute__(name)

    def to_internal_value(self, data):
        validated_data = super().to_internal_value(data)
        required_languages = getattr(self.Meta, 'required_languages', [])
        default_language = getattr(self.Meta, 'default_language', None)
        translatable_fields = getattr(self.Meta, 'translatable_fields', [])

        for field in translatable_fields:
            if field in data:
                translations = data.get(field, {})
                # Track provided translations to use for fallbacks
                provided_translations = {}
                for lang, _ in settings.LANGUAGES:
                    lang_field = f'{field}_{lang}'
                    if lang_field not in self.Meta.model._meta.get_fields():
                        continue  # Skip if model doesn't have this language field

                    if lang in translations:
                        # Store provided translation
                        validated_data[lang_field] = translations[lang]
                        provided_translations[lang] = translations[lang]
                    elif lang in required_languages:
                        # Raise error if language is required but missing
                        raise serializers.ValidationError(
                            f"Translation for {field} in language {lang} is required."
                        )
                    else:
                        # Handle missing translation
                        if default_language and default_language in provided_translations:
                            # Use default language's value as fallback
                            validated_data[lang_field] = provided_translations[default_language]
                        else:
                            # Default to None if no fallback is available
                            validated_data[lang_field] = None

        return validated_data

    def create(self, validated_data):
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        return instance



# class TranslatableFieldMixin:
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         # Dynamically add SerializerMethodField for each translatable field
#         for field in getattr(self.Meta, 'translatable_fields', []):
#             self.fields[field] = serializers.SerializerMethodField()

#     def get_translatable_field(self, obj, field_name):
#         lang = get_language()
#         return getattr(obj, f'{field_name}_{lang}')

#     def __getattribute__(self, name):
#         # Dynamically generate get_<field> methods for translatable fields
#         if name.startswith('get_') and hasattr(self.Meta, 'translatable_fields'):
#             field_name = name[4:]
#             if field_name in self.Meta.translatable_fields:
#                 return lambda obj: self.get_translatable_field(obj, field_name)
#         return super().__getattribute__(name)
    
#     def to_internal_value(self, data):
#         # Convert translatable fields from dict format to language-specific fields
#         validated_data = super().to_internal_value(data)
#         for field in getattr(self.Meta, 'translatable_fields', []):
#             if field in data:
#                 # Expecting data like {"title": {"en": "English Title", "fr": "French Title"}}
#                 translations = data.get(field, {})
#                 for lang, _ in settings.LANGUAGES:
#                     lang_field = f'{field}_{lang}'
#                     if lang in translations:
#                         validated_data[lang_field] = translations[lang]
#                     elif lang_field in self.Meta.model._meta.get_fields():
#                         # Ensure field exists in model to avoid errors
#                         validated_data[lang_field] = validated_data.get(lang_field, None)
#         return validated_data

#     def create(self, validated_data):
#         # Create instance with language-specific fields
#         return self.Meta.model.objects.create(**validated_data)

#     def update(self, instance, validated_data):
#         # Update instance with language-specific fields
#         for key, value in validated_data.items():
#             setattr(instance, key, value)
#         instance.save()
#         return instance