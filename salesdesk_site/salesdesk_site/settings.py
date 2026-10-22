"""
Django settings for salesdesk_site project.
"""

import os                                      # NEW
from pathlib import Path
from dotenv import load_dotenv                 # NEW

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')                 # NEW: reads local values from .env (Railway has no .env)

# CHANGED: read from the environment; the old key stays as the local fallback
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-uj&$a97#2#x2ht$(%7l$(gegoz&)+yy91gr8-lk&z=4^ro7(yy',
)

# CHANGED: True on your computer, False on Railway (you set DEBUG=False there)
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

# CHANGED
ALLOWED_HOSTS = ['*']

# NEW: needed for the /admin/ login behind Railway's HTTPS proxy
CSRF_TRUSTED_ORIGINS = ['https://*.up.railway.app']
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'salesdesk',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',      # NEW: serves css/js in production
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'salesdesk_site.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'salesdesk_site.wsgi.application'


# Database
# CHANGED: no password in the file any more. Values come from .env locally
# and from the Railway variables in production.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('PGDATABASE', 'salesdesk'),
        'USER': os.environ.get('PGUSER', 'postgres'),
        'PASSWORD': os.environ.get('PGPASSWORD', ''),
        'HOST': os.environ.get('PGHOST', 'localhost'),
        'PORT': os.environ.get('PGPORT', '5432'),
    }
}

# CHANGED: these three lines were repeated twice in your file; keep them once
AUTH_USER_MODEL = 'salesdesk.User'
TIME_ZONE = 'Asia/Dhaka'
USE_TZ = True

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# Internationalization
LANGUAGE_CODE = 'en-us'


# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'         # NEW: where collectstatic puts files for production


# Email (unchanged)
MAILERS = {
    'default': {
        'BACKEND': 'django.core.mail.backends.console.EmailBackend',
    },
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework.authentication.TokenAuthentication'],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_PAGINATION_CLASS': 'salesdesk.utils.Pagination',
    'DEFAULT_FILTER_BACKENDS': ['rest_framework.filters.SearchFilter'],
    'EXCEPTION_HANDLER': 'salesdesk.utils.api_exception_handler',
    'COERCE_DECIMAL_TO_STRING': False,
}