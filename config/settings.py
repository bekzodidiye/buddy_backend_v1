import os
import dj_database_url
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-*ycm=zr+q%89(3_wo^5iul3suc72%u*@$e20n39m%8=dt)22xi')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '*').split(',')

CSRF_TRUSTED_ORIGINS = [
    'https://*.railway.app',
    'https://*.vercel.app',
    'http://*.vercel.app',
    'http://*.railway.app',
    'https://*.onrender.com',
    'http://*.onrender.com',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:5173',
    'http://127.0.0.1:5173',
]

CORS_ALLOWED_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True # Cookies yoki Authorization headerlar uchun

# Render proxy settings
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# Production security settings
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

# Application definition

INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'drf_spectacular',
    'channels',
    'django_celery_results',
    'django_celery_beat',
    
    # Local apps
    'api',
    'apps.authentication',
]

# Production Channel Layer
REDIS_URL = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0')
if not REDIS_URL.startswith('redis'):
    REDIS_URL = f"redis://{REDIS_URL}"
# FIX: Removed startup print() — use logging instead (configured below)
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [REDIS_URL],
        },
    },
}

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware', # Birinchi bo'lib ishlashi shart
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Token muddati yaqin bo'lganda yangi token yuborish
    'apps.authentication.middleware.token_auto_refresh.TokenAutoRefreshMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'




# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv('DATABASE_URL', f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
        conn_max_age=600
    )
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'uz-uz'

TIME_ZONE = 'Asia/Tashkent'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'api.User'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        # Standart JWT o'rniga Redis blacklist tekshiruvchi custom class
        'apps.authentication.middleware.token_blacklist_auth.BlacklistCheckedJWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    # FIX: Added pagination — list endpoints were returning ALL records (memory bomb)
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    # FIX: Custom exception handler for consistent error responses
    'EXCEPTION_HANDLER': 'api.exception_handler.custom_exception_handler',
}

# ─── Redis Cache (Token Blacklist uchun) ──────────────────────────────────────
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'IGNORE_EXCEPTIONS': True,  # Redis yo'q bo'lsa ham server ishlayversin
        },
        'KEY_PREFIX': 'buddy_cache',
        'TIMEOUT': 86400,  # 24 soat default
    }
}

# ─── JWT Konfiguratsiyasi ─────────────────────────────────────────────────────
SIMPLE_JWT = {
    # FIX: Was 15 minutes — too short, caused frequent re-auth overhead.
    # 2 hours is practical for a monitoring dashboard. Refresh token rotation
    # (ROTATE_REFRESH_TOKENS below) keeps security intact.
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=2),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'AUTH_HEADER_TYPES': ('Bearer',),

    # Refresh Token Rotation — har refresh da yangi token
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,

    # Token tip klasslari
    'TOKEN_OBTAIN_SERIALIZER': 'rest_framework_simplejwt.serializers.TokenObtainPairSerializer',
    'TOKEN_REFRESH_SERIALIZER': 'rest_framework_simplejwt.serializers.TokenRefreshSerializer',

    # JTI (JWT ID) ni claim lardan chiqarish — blacklist uchun kerak
    'JTI_CLAIM': 'jti',

    # Algorithm
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
}

# FIX: Removed CORS_ALLOW_ALL_ORIGINS = True — that setting overrides
# CORS_ALLOWED_ORIGINS completely, making the whitelist pointless.
# For local development you can temporarily re-enable it.
CORSS_ALLOW_ALL_ORIGINS = DEBUG  # Only allow all in DEBUG mode
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]
# FIX: Was 1 second — caused browsers to send OPTIONS pre-flight before EVERY
# single API request, effectively doubling the request count to the server.
# 86400 = 24 hours is the standard recommended value.
CORS_PREFLIGHT_MAX_AGE = 86400

SPECTACULAR_SETTINGS = {
    'TITLE': 'Buddy Team API',
    'DESCRIPTION': 'Backend API for Buddy Team monitoring system',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# Celery Settings
CELERY_BROKER_URL = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND = 'django-db'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# ─── Logging ──────────────────────────────────────────────────────────────────
# FIX: Added proper logging configuration. All print() calls in the codebase
# have been replaced with logger.debug/info/warning/error calls.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose' if not DEBUG else 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'api': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        # Silence noisy third-party loggers in production
        'urllib3': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
