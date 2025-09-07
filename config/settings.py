# config/settings.py

# ----------------- بخش‌های اولیه (بدون تغییر) -----------------
from pathlib import Path
import os
import json
BASE_DIR = Path(__file__).resolve().parent.parent

# ----------------- بخش هوشمند: تشخیص محیط -----------------
# این خط چک می‌کند که آیا کد روی سرور PythonAnywhere اجرا می‌شود یا نه
ON_PA_SERVER = 'PYTHONANYWHERE_DOMAIN' in os.environ

if ON_PA_SERVER:
    # اگر روی سرور بودیم، این تنظیمات اعمال می‌شود
    DEBUG = False
    ALLOWED_HOSTS = ['amin01ak8.pythonanywhere.com']

    # برو و اطلاعات حساس را از "گاوصندوق" (فایل secrets.json) بخوان
    secrets_path = '/home/amin01ak8/secrets.json'
    with open(secrets_path) as f:
        secrets = json.load(f)
    SECRET_KEY = secrets['DJANGO_SECRET_KEY']
    EMAIL_HOST_USER = secrets['EMAIL_HOST_USER']
    EMAIL_HOST_PASSWORD = secrets['EMAIL_HOST_PASSWORD']

else:
    # اگر روی کامپیوتر شخصی بودیم، این تنظیمات اعمال می‌شود
    DEBUG = True
    ALLOWED_HOSTS = []

    # از مقادیر موقت و ناامن برای تست استفاده کن
    # این کد هرگز روی سرور اجرا نمی‌شود، پس مشکلی نیست
    secrets_path = 'secrets.json'
    with open(secrets_path) as f:
        secrets = json.load(f)
    SECRET_KEY = secrets['DJANGO_SECRET_KEY']
    EMAIL_HOST_USER = secrets['EMAIL_HOST_USER']
    EMAIL_HOST_PASSWORD = secrets['EMAIL_HOST_PASSWORD']

# ----------------- بقیه تنظیمات جنگو (کپی/پیست ساده) -----------------
INSTALLED_APPS = [
    'jalali_date',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core.apps.CoreConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
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

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    { 'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator', },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Tehran'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'core.User'
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')