from .base import *
import dj_database_url
from decouple import config
import os

# --- Security ---
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=lambda v: [s.strip() for s in v.split(',')])
DEBUG = config('DEBUG', default=False, cast=bool)

# --- PostgreSQL Configuration ---
# Using config() ensures it pulls from your .env or environment variables consistently
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT', default=5432),
        'CONN_MAX_AGE': 600,
    }
}

# Use dj_database_url to safely merge settings
db_from_env = dj_database_url.config(conn_max_age=600, default=config('DATABASE_URL'))
if db_from_env:
    DATABASES['default'].update(db_from_env)
    # Ensure the engine is explicitly set if dj_database_url misses it
    DATABASES['default']['ENGINE'] = 'django.db.backends.postgresql'


# --- Static Files ---
WHITENOISE_ROOT = os.path.join(BASE_DIR, 'static_cdn', 'root')


# --- Email / Gmail Configuration ---
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True  # Required for Gmail SMTP
EMAIL_USE_SSL = False # Gmail uses TLS on 587, not SSL
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD') # Must be a 16-character App Password
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default=EMAIL_HOST_USER)


# --- API & Third Party Credentials ---
# MAIL_CLIENT_ID = config('MAIL_CLIENT_ID', default='')
# MAIL_CLIENT_SECRET = config('MAIL_CLIENT_SECRET', default='')
# APP_ID = config('APP_ID', default='')
# TENANT_ID = config('TENANT_ID', default='')

BASE_URL = "https://alpha-cmms.alphamead.com"

CORS_ALLOW_CREDENTIALS = True

# --- Recommended Production Security ---
CSRF_TRUSTED_ORIGINS = [
    "https://alpha-cmms.alphamead.com",
    "http://46.101.74.174"
]