"""
Django settings for demo_app project.

Generated by 'django-admin startproject' using Django 3.1.5.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.1/ref/settings/
"""
import os
import sys
from pathlib import Path

from django_project_base import VERSION

# Build paths inside the project like this: BASE_DIR / 'subdir'.
from django_project_base.account.constants import ACCOUNT_APP_ID
from django_project_base.notifications import NOTIFICATIONS_APP_ID

try:
    from . import env
except:
    env = dict()


BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "w0o6y0rwef0zijgd7m91w0b!p-(#l1zpna1%c1vvr7f17)x&*-"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True
TESTING = len(sys.argv) > 1 and sys.argv[1] == "test"

ALLOWED_HOSTS = ["*"]

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "rest_registration",
    "django_project_base",
    "example.demo_django_base",
    "drf_spectacular",
    NOTIFICATIONS_APP_ID,
    "social_django",
    ACCOUNT_APP_ID,
    "dynamicforms",
]

if not getattr(env, "DEPLOY", True):
    INSTALLED_APPS.append("vue")

MIDDLEWARE = [
    "django_project_base.base.UrlVarsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # 'django.contrib.sessions.middleware.SessionMiddleware',
    "django_project_base.account.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_project_base.profiling.profile_middleware",
]

ROOT_URLCONF = "example.setup.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "example.setup.wsgi.application"

# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
    }
}

# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = "*Client ID*"
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = "*Client secret*"

SOCIAL_AUTH_GITHUB_KEY = "a1b2c3d4"
SOCIAL_AUTH_GITHUB_SECRET = "e5f6g7h8i9"

SOCIAL_AUTH_MICROSOFT_GRAPH_KEY = "..."
SOCIAL_AUTH_MICROSOFT_GRAPH_SECRET = "..."

# Internationalization
# https://docs.djangoproject.com/en/3.1/topics/i18n/

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = True

LOCALE_PATHS = [os.path.abspath(os.path.join(BASE_DIR, "../django_project_base/locale/"))]

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/


STATIC_URL = "/static/"
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, "static/"),
    str(BASE_DIR).replace("example", "") + "django_project_base/static/",
)

DJANGO_PROJECT_BASE_PROJECT_MODEL = "demo_django_base.Project"
DJANGO_PROJECT_BASE_PROFILE_MODEL = "demo_django_base.UserProfile"
DJANGO_PROJECT_BASE_PROJECTMEMBER_MODEL = "demo_django_base.ProjectMember"
DJANGO_PROJECT_BASE_MERGEUSERGROUP_MODEL = "demo_django_base.MergeUserGroup"

DEFAULT_FROM_EMAIL = "info@example.com"

REST_REGISTRATION = {
    "REGISTER_VERIFICATION_ENABLED": False,
    "REGISTER_EMAIL_VERIFICATION_ENABLED": False,
    "LOGIN_DEFAULT_SESSION_AUTHENTICATION_BACKEND": "django_project_base.base.auth_backends.UsersCachingBackend",
    "VERIFICATION_FROM_EMAIL": DEFAULT_FROM_EMAIL,
}

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
        "dynamicforms.renderers.ComponentDefRenderer",
    ),
    "DEFAULT_FILTER_BACKENDS": ("dynamicforms.filters.FilterBackend",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Django Project Base Example API",
    "DESCRIPTION": "This is API documentation for Django project base example project. API is showcase for all"
    'available api endpoint for "Django project base" project',
    "VERSION": VERSION,
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "defaultModelsExpandDepth": 10,
        "defaultModelExpandDepth": 10,
        "tryItOutEnabled": True,
    },
    "COMPONENT_SPLIT_REQUEST": True,
}

AUTHENTICATION_BACKENDS = (
    "django_project_base.base.auth_backends.UsersCachingBackend",  # cache users for auth to gain performance
)

PROFILER_LONG_RUNNING_TASK_THRESHOLD = 1000

# Settings for Mailhog
# https://github.com/mailhog/MailHog
# MailHog is an email testing tool for developers. Configure your application to use MailHog for SMTP delivery.
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "127.0.0.1"
EMAIL_PORT = 1025
EMAIL_USE_SSL = False
EMAIL_HOST_USER = ""
EMAIL_HOST_PASSWORD = ""
SERVER_EMAIL = ""

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

DYNAMICFORMS = {
    "allow_anonymous_user_to_preupload_files": True,
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "cache",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
