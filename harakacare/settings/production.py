import os
from pathlib import Path

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-default-key-for-render')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',') if os.environ.get('ALLOWED_HOSTS') else ['.onrender.com', 'localhost', '127.0.0.1']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'rest_framework.authtoken',
    'apps.patients',
    'apps.triage',
    'apps.facilities',
    'apps.channels',
    'apps.adherence',
    'apps.analytics',
    'apps.core',
    'apps.conversations',
    'apps.messaging',
]

# CORS for production - Allow all Vercel subdomains
CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',') if os.environ.get('CORS_ALLOWED_ORIGINS') else [
    'https://harakacare-front.vercel.app',
    'https://harakacare-frontend.vercel.app',
    'https://localhost:3000',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'https://127.0.0.1:3000',
]

# Allow all Vercel subdomains using pattern matching
CORS_ALLOWED_ORIGIN_REGEXES = [
    r'^https://.*-demagalawrences-projects\.vercel\.app$',
    r'^https://harakacare-frontend-.*\.vercel\.app$',
    r'^https://.*\.vercel\.app$',  # Allow all Vercel subdomains
]

# Allow all origins for development
CORS_ALLOW_ALL_ORIGINS = DEBUG  # Allow all origins when DEBUG=True
CORS_ALLOW_CREDENTIALS = True

# Allow all Vercel subdomains dynamically
class VercelCorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.headers.get('origin')
        if origin and ('vercel.app' in origin or 'localhost' in origin):
            response = self.get_response(request)
            response['Access-Control-Allow-Origin'] = origin
            response['Access-Control-Allow-Credentials'] = 'true'
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            return response
        return self.get_response(request)

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'apps.core.middleware.EnsureTablesMiddleware',  # Auto-create missing tables
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.core.middleware.VercelCorsMiddleware',  # Dynamic CORS for Vercel
]

# Core Django settings - ensure these are always set
ROOT_URLCONF = 'harakacare.urls'
WSGI_APPLICATION = 'harakacare.wsgi.application'

# Database - Use SQLite for now to avoid PostgreSQL dependency issues
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Use PostgreSQL Database URL if available (and working)
if os.environ.get('DATABASE_URL') and os.environ.get('USE_POSTGRESQL', 'False') == 'True':
    try:
        import dj_database_url
        DATABASES['default'] = dj_database_url.parse(os.environ.get('DATABASE_URL'))
    except ImportError:
        pass  # Fall back to SQLite

# Password validation
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
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Templates
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

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
MEDIA_URL = '/media/'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    }
}

# CORS for production
CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',') if os.environ.get('CORS_ALLOWED_ORIGINS') else [
    'https://harakacare-front.vercel.app',
    'https://harakacare-frontend.vercel.app',
    'https://harakacare-front-gk39rhq75-demagalawrences-projects.vercel.app',
    'https://localhost:3000',
    'http://localhost:3000',
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False

# Session/CSRF settings for production
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = 'None'
SESSION_COOKIE_DOMAIN = None
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = 'None'

# Static files - Use S3 in production
USE_S3 = os.environ.get('USE_S3', 'False') == 'True'
if USE_S3:
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'us-east-1')
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    
    STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
    
    STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
else:
    STATIC_URL = '/static/'
    MEDIA_URL = '/media/'

# Email (for production)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'harakacare.log',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
}

# Auto-setup production data on EVERY app start (bulletproof)
def setup_production_data():
    """Automatically create production facilities and users on every start"""
    try:
        from django.contrib.auth.models import User
        from apps.facilities.models import Facility
        from apps.core.models import UserProfile
        from django.core.management import call_command
        
        # ALWAYS run migrations first
        call_command('migrate', verbosity=0, interactive=False, run_syncdb=True)
        
        # ALWAYS create facilities (idempotent)
        facilities_data = [
            {
                'name': 'Kampala Referral Hospital',
                'facility_type': 'referral_hospital',
                'address': 'Kampala, Uganda (Serves: Kampala, Wakiso, Mpigi)',
                'district': 'Kampala',
                'phone_number': '+256414123456',
                'total_beds': 500,
                'available_beds': 150,
                'staff_count': 200,
                'ambulance_available': True,
                'services_offered': ['emergency', 'general_medicine', 'surgery', 'obstetrics', 'maternal_health'],
            },
            {
                'name': 'Mulago National Hospital',
                'facility_type': 'national_referral',
                'address': 'Mulago, Kampala (Serves: Kampala, Mukono, Buikwe)',
                'district': 'Kampala',
                'phone_number': '+256414789012',
                'total_beds': 800,
                'available_beds': 200,
                'staff_count': 350,
                'ambulance_available': True,
                'services_offered': ['emergency', 'general_medicine', 'surgery', 'pediatrics', 'obstetrics'],
            },
            {
                'name': 'Luwero General Hospital',
                'facility_type': 'general_hospital',
                'address': 'Luwero Town (Serves: Luwero, Nakasongola, Kayunga)',
                'district': 'Luwero',
                'phone_number': '+256414555666',
                'total_beds': 100,
                'available_beds': 50,
                'staff_count': 75,
                'ambulance_available': True,
                'services_offered': ['emergency', 'general_medicine', 'obstetrics', 'maternal_health'],
            }
        ]
        
        for facility_data in facilities_data:
            facility, created = Facility.objects.get_or_create(
                name=facility_data['name'],
                defaults=facility_data
            )
        
        # ALWAYS create users (idempotent)
        users_data = [
            {
                'username': 'kampala_staff',
                'password': 'kampala123',
                'email': 'staff@kampalareferral.ug',
                'first_name': 'John',
                'last_name': 'Ochieng',
                'facility_name': 'Kampala Referral Hospital',
                'role': 'medical_officer',
                'department': 'Emergency',
            },
            {
                'username': 'mulago_staff',
                'password': 'mulago123',
                'email': 'staff@mulago.go.ug',
                'first_name': 'Sarah',
                'last_name': 'Nakato',
                'facility_name': 'Mulago National Hospital',
                'role': 'nurse',
                'department': 'Emergency',
            },
            {
                'username': 'luwero_staff',
                'password': 'luwero123',
                'email': 'staff@luwerohospital.ug',
                'first_name': 'Grace',
                'last_name': 'Nakintu',
                'facility_name': 'Luwero General Hospital',
                'role': 'nurse_midwife',
                'department': 'Maternity',
            }
        ]
        
        for user_data in users_data:
            user, user_created = User.objects.get_or_create(
                username=user_data['username'],
                defaults={
                    'email': user_data['email'],
                    'first_name': user_data['first_name'],
                    'last_name': user_data['last_name'],
                    'is_staff': True,
                }
            )
            
            # ALWAYS update password (fresh every time)
            user.set_password(user_data['password'])
            user.save()
            
            # Create/update profile
            facility = Facility.objects.get(name=user_data['facility_name'])
            profile, profile_created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'facility': facility,
                    'role': user_data['role'],
                    'department': user_data['department'],
                    'phone_number': '+256700000000',
                    'is_active_staff': True,
                    'can_view_all_facilities': False,
                }
            )
            
            # Update profile facility assignment
            if not profile_created:
                profile.facility = facility
                profile.role = user_data['role']
                profile.department = user_data['department']
                profile.is_active_staff = True
                profile.save()
        
        # ALWAYS create/update admin user
        admin_user, admin_created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@harakacare.ug',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        
        # ALWAYS update admin password
        admin_user.set_password('admin123')
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()
                
    except Exception as e:
        # Log error but don't crash
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Setup error (but app continues): {str(e)}")
        pass

# Run setup when Django starts
setup_production_data()
