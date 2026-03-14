from .base import *
import os

DEBUG = True

ALLOWED_HOSTS = ["*"]
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "0.0.0.0"]



DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]

# Allow common headers for the React frontend
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': os.environ.get('DB_NAME', 'clms'),
#         'USER': os.environ.get('DB_USER', 'postgres'),
#         'PASSWORD': os.environ.get('DB_PASSWORD', '1234'),
#         'HOST': os.environ.get('DB_HOST', 'localhost'),
#         'PORT': os.environ.get('DB_PORT', '5432'),
#         'CONN_MAX_AGE': 600,
#     }
# }


# Use console backend for development to avoid email configuration issues
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Comment out O365 email settings for development
# EMAIL_BACKEND = config('EMAIL_BACKEND')
# EMAIL_HOST = config('EMAIL_HOST')
# EMAIL_PORT = config('EMAIL_PORT', cast=int)
# EMAIL_USE_TLS = config('EMAIL_USE_TLS', cast=bool)
# EMAIL_USE_SSL = config('EMAIL_USE_SSL', cast=bool)
# EMAIL_HOST_USER = config('EMAIL_HOST_USER')
# EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')

# Microsoft Graph OAuth2 credentials
# MAIL_CLIENT_ID = config('MAIL_CLIENT_ID')
# MAIL_CLIENT_SECRET = config('MAIL_CLIENT_SECRET')
# APP_ID = config('APP_ID')
# TENANT_ID = config('TENANT_ID')

BASE_URL="http://localhost:8000"