"""
URL configuration for harakacare project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# harakacare/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.http import JsonResponse
from apps.triage.admin import harakacare_admin
from apps.core.views import setup_production_api
from apps.core.quick_setup import create_users_quick
from apps.core.db_setup import setup_database
from apps.core.health_check import health_check

def api_info(request):
    """HarakaCare API Information"""
    return JsonResponse({
        "name": "HarakaCare API",
        "version": "1.0.0",
        "status": "active",
        "endpoints": {
            "chat": "/api/v1/chat/",
            "facilities": "/api/facilities/",
            "triage": "/api/v1/triage/",
            "admin": "/harakacare-admin/",
            "django_admin": "/admin/",
            "setup": "/setup-database/",
            "health": "/health-check/"
        },
        "description": "Healthcare triage and facility management system"
    })

urlpatterns = [
    path('', api_info, name='api_info'),  # API info at root
    path('admin/', admin.site.urls),  # Default Django admin
    path('harakacare-admin/', harakacare_admin.urls),  # Custom HarakaCare admin
    path('setup-production/', setup_production_api, name='setup_production'),  # Production setup endpoint
    path('create-users/', create_users_quick, name='create_users'),  # Quick user creation
    path('setup-database/', setup_database, name='setup_database'),  # Database and user setup
    path('health-check/', health_check, name='health_check'),  # Health check endpoint
    path('api/', include('apps.messaging.api_urls')),  # Chat API endpoints
    path('api/facilities/', include('apps.facilities.urls')),  # Facility API endpoints
    path('api/v1/triage/', include('apps.triage.urls')),  # Triage API endpoints
    # Re-enabled messaging endpoints with error handling for missing credentials
    path('messaging/', include('apps.messaging.urls')),  # Messaging endpoints
    path("messaging/whatsapp/", include("apps.messaging.whatsapp.urls")),  # WhatsApp endpoints
]

# Add debug toolbar URLs in development
if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]