"""
HarakaCare Django Settings - Development Environment
"""

from .base import *



# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

# Development-specific apps
INSTALLED_APPS += [
    'debug_toolbar',
]

MIDDLEWARE += [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

# Debug Toolbar Configuration
INTERNAL_IPS = [
    '127.0.0.1',
    'localhost',
]

DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG,
}

# Database - Use local PostgreSQL for development
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.contrib.gis.db.backends.postgis',
#         'NAME': env('DB_NAME', default='harakacare_dev'),
#         'USER': env('DB_USER', default='harakacare_user'),
#         'PASSWORD': env('DB_PASSWORD', default='dev_password'),
#         'HOST': env('DB_HOST', default='localhost'),
#         'PORT': env('DB_PORT', default='5432'),
#     }
# }
# Database - Use SQLite for quick development
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Cache - Use Redis locally
# CACHES = {
#     'default': {
#         'BACKEND': 'django_redis.cache.RedisCache',
#         'LOCATION': 'redis://localhost:6379/0',
#         'OPTIONS': {
#             'CLIENT_CLASS': 'django_redis.client.DefaultClient',
#         },
#         'KEY_PREFIX': 'harakacare_dev',
#     }
# }


CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'triage-conversation-cache',
        'TIMEOUT': 1800,  # 30 minutes
    }
}

# Email - Use console backend in development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# CORS - Allow all origins in development
CORS_ALLOW_ALL_ORIGINS = True

# Celery - Use Redis as broker
CELERY_BROKER_URL = 'redis://localhost:6379/1'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/1'
CELERY_TASK_ALWAYS_EAGER = env.bool('CELERY_TASK_ALWAYS_EAGER', default=False)

# Disable throttling in development
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': '10000/hour',
    'user': '10000/hour'
}

# Enhanced logging for development
LOGGING['loggers']['apps']['level'] = 'DEBUG'
LOGGING['loggers']['django.db.backends'] = {
    'handlers': ['console'],
    'level': 'DEBUG',
    'propagate': False,
}

# Static files - Serve directly in development
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Security settings - relaxed for development
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_BROWSER_XSS_FILTER = False
SECURE_CONTENT_TYPE_NOSNIFF = False

# HarakaCare Development Overrides
HARAKACARE.update({
    'TRIAGE_SESSION_TIMEOUT': 600,  # 10 minutes for easier testing
    'USE_GPU': False,  # CPU-only for development
})

print("🚀 Running in DEVELOPMENT mode")