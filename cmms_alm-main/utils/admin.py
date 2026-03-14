from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from .models import ImageAttachment, FileAttachment

class ImageAttachmentInline(GenericTabularInline):
    model = ImageAttachment
    extra = 1

class FileAttachmentInline(GenericTabularInline):
    model = FileAttachment
    extra = 1

@admin.register(ImageAttachment)
class ImageAttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'content_type', 'object_id', 'file')
    list_filter = ('content_type',)
    search_fields = ('object_id',)
    readonly_fields = ('id',)

@admin.register(FileAttachment)
class FileAttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'content_type', 'object_id', 'file')
    list_filter = ('content_type',)
    search_fields = ('object_id',)
    readonly_fields = ('id',)
