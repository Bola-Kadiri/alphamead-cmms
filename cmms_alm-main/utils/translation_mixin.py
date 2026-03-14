from django.conf import settings
from django.utils.translation import get_language
from rest_framework import serializers
import logging

logger = logging.getLogger(__name__)

class TranslatableFieldMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in getattr(self.Meta, 'translatable_fields', []):
            self.fields[field] = serializers.SerializerMethodField()

    def get_translatable_field(self, obj, field_name):
        lang = get_language()
        logger.debug(f"Retrieving {field_name} for language: {lang}")
        return getattr(obj, f'{field_name}_{lang}')

    def __getattribute__(self, name):
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
        current_language = get_language()

        logger.debug(f"Processing data: {data}")
        logger.debug(f"Current language: {current_language}, Translatable fields: {translatable_fields}")

        for field in translatable_fields:
            if field in data:
                field_data = data.get(field)
                provided_translations = {}
                logger.debug(f"Processing field: {field}, Data: {field_data}, Type: {type(field_data)}")

                if isinstance(field_data, dict):
                    # Handle dictionary input
                    translations = field_data
                    for lang, _ in settings.LANGUAGES:
                        lang_field = f'{field}_{lang}'
                        logger.debug(f"Checking field: {lang_field}, Exists: {any(f.name == lang_field for f in self.Meta.model._meta.get_fields())}")
                        if lang_field not in [f.name for f in self.Meta.model._meta.get_fields()]:
                            logger.warning(f"Field {lang_field} does not exist in model.")
                            continue

                        if lang in translations:
                            validated_data[lang_field] = translations[lang]
                            provided_translations[lang] = translations[lang]
                        elif lang in required_languages:
                            raise serializers.ValidationError({
                                field: f"Translation for {lang} is required."
                            })
                        else:
                            if default_language and default_language in provided_translations:
                                validated_data[lang_field] = provided_translations[default_language]
                            else:
                                validated_data[lang_field] = None
                elif isinstance(field_data, str):
                    # Handle string input
                    lang_field = f'{field}_{current_language}'
                    logger.debug(f"Checking field: {lang_field}, Exists: {any(f.name == lang_field for f in self.Meta.model._meta.get_fields())}")
                    if lang_field not in [f.name for f in self.Meta.model._meta.get_fields()]:
                        raise serializers.ValidationError({
                            field: f"Field {lang_field} does not exist in the model."
                        })
                    validated_data[lang_field] = field_data
                    provided_translations[current_language] = field_data

                    # Handle other languages
                    for lang, _ in settings.LANGUAGES:
                        if lang == current_language:
                            continue
                        lang_field = f'{field}_{lang}'
                        if lang_field not in [f.name for f in self.Meta.model._meta.get_fields()]:
                            logger.warning(f"Field {lang_field} does not exist in model.")
                            continue
                        if lang in required_languages:
                            raise serializers.ValidationError({
                                field: f"Translation for {lang} is required."
                            })
                        elif default_language and default_language in provided_translations:
                            validated_data[lang_field] = provided_translations[default_language]
                        else:
                            validated_data[lang_field] = None
                else:
                    # Handle unexpected input type
                    raise serializers.ValidationError({
                        field: f"Invalid input type for {field}. Expected string or dictionary, got {type(field_data)}."
                    })

        logger.debug(f"Validated data: {validated_data}")
        return validated_data

    def create(self, validated_data):
        logger.debug(f"Creating instance with validated data: {validated_data}")
        return self.Meta.model.objects.create(**validated_data)

    def update(self, instance, validated_data):
        logger.debug(f"Updating instance with validated data: {validated_data}")
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        return instance