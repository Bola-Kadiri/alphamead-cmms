"""
Attachment size limit for the whole application: any single uploaded file can be at most
15 MB. Checked while the upload streams in (so an oversized file is never fully read or
stored), on every screen and API, and answered with a clear JSON message.

The web server (NGINX) separately limits a whole save to 100 MB, so several files of up to
15 MB each can be sent together.
"""
from django.core.exceptions import RequestDataTooBig
from django.core.files.uploadhandler import FileUploadHandler
from django.http import JsonResponse

MAX_FILE_MB = 15
MAX_FILE_BYTES = MAX_FILE_MB * 1024 * 1024


class FileTooLarge(RequestDataTooBig):
    """One uploaded file is over the limit."""


class MaxFileSizeUploadHandler(FileUploadHandler):
    """First in the upload handler chain: counts each file's bytes and stops one over the limit.

    It passes every chunk on unchanged, so Django's own handlers still store the file as before.
    """

    def new_file(self, *args, **kwargs):
        super().new_file(*args, **kwargs)
        self.received = 0

    def receive_data_chunk(self, raw_data, start):
        self.received += len(raw_data)
        if self.received > MAX_FILE_BYTES:
            name = self.file_name or 'A file'
            raise FileTooLarge(f"{name} is too large. Each file can be at most {MAX_FILE_MB} MB.")
        return raw_data

    def file_complete(self, file_size):
        return None  # the next handler builds the file


class FileTooLargeMiddleware:
    """Turn an oversized file into a 400 with a message the screens can show."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if isinstance(exception, FileTooLarge):
            return JsonResponse({'error': str(exception)}, status=400)
        return None
