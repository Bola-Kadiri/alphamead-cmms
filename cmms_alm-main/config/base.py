from pathlib import Path
import os
# from environs import Env
from decouple import config



# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    
    # third party apps
    'anymail',
    "sslserver",
    'jazzmin',
    'rest_framework',
    'rest_framework_simplejwt',
    'drf_yasg',
    'mail_templated',
    'django_filters',
    'modeltranslation',
    'django_o365mail',
    # user defined apps
    'accounts',
    'utils',
    'dashboard',
    'procurement',
    'work',
    'asset_inventory',
    'facility',
    'report',
    'reference',
    'ppm_calendar',
]   

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'cmms_instanta.urls'


SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header'
        }
    },
    'PERSIST_AUTH': True,
    'USE_SESSION_AUTH': False,
}

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                # 'dashboard.context.default',
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',
                'work.context_processors.notifications',
            ],
        },
    },
]

WSGI_APPLICATION = 'cmms_instanta.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}



# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': 'cmms_main',
#         'USER': 'postgres',
#         'PASSWORD': '151348',
#         'HOST': 'localhost',
#         'PORT': '5432',
#     }
# }

AUTH_USER_MODEL = 'accounts.User'


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


CORS_ALLOWED_ORIGINS = [
    
    "https://alpha-cmms.alphamead.com"
    
]


CORS_ALLOW_ALL_ORIGINS = True

# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

# Language settings
LANGUAGES = (
    ('en', 'English'),
    ('fr', 'French'),
    ('es', 'Spanish'),
)

MODELTRANSLATION_DEFAULT_LANGUAGE = 'en'
MODELTRANSLATION_LANGUAGES = ['en', 'fr', 'es']

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]
# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = '/static/'
MEDIA_URL = '/media/'

STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'static_cdn')
MEDIA_ROOT = os.path.join(BASE_DIR, 'media_cdn/')

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder'
)



# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Email configuration
EMAIL_BACKEND = config('EMAIL_BACKEND', default='anymail.backends.resend.EmailBackend')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='cmms@alphamead.com')

ANYMAIL = {
    'RESEND_API_KEY': config('RESEND_API_KEY', default=''),
}

BASE_URL = config('BASE_URL', default='https://alpha-cmms.alphamead.com')
FRONTEND_URL = config('FRONTEND_URL', default='https://alpha-cmms.alphamead.com')
# --- Microsoft Graph API Email Configuration ---
# --- Microsoft Graph API Email Configuration ---
# EMAIL_BACKEND = 'django_o365mail.EmailBackend'

# Use config() to pull the O365 specific keys from .env
# O365_MAIL_CLIENT_ID = config('O365_MAIL_CLIENT_ID')
# O365_MAIL_CLIENT_SECRET = config('O365_MAIL_CLIENT_SECRET')
# O365_MAIL_TENANT_ID = config('O365_MAIL_TENANT_ID')

# Explicitly define the SENDER so Django can see it in settings
# O365_MAIL_SENDER = config('O365_MAIL_SENDER', default='samson.omamuzo@alphamead.com')

# Set the standard Django 'From' address to match your work email
# DEFAULT_FROM_EMAIL = O365_MAIL_SENDER

# This ensures it sends even while you are developing (DEBUG=True)
# O365_ACTUALLY_SEND_IN_DEBUG = True
# O365_MAIL_MAILBOX_KWARGS = {'resource': 'samson.omamuzo@alphamead.com'}
