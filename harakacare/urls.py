"""
URL configuration for harakacare project.

The `urlpatterns` list routes URLs to views.
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
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView


def api_info(request):
    """HarakaCare API Information"""
    return JsonResponse({
        "name": "HarakaCare API",
        "version": "2.0.0",
        "status": "active",
        "endpoints": {
            "auth": "/api/v1/auth/",
            "triage": "/api/v1/triage/",
            "facilities": "/api/v1/facilities/",
            "chat": "/api/v1/chat/",
            "referrals": "/api/v1/referrals/",
            "cases": "/api/v1/cases/",
            "notifications": "/api/v1/notifications/",
            "analytics": "/api/v1/analytics/",
            "schema": "/api/v1/schema/",
            "docs": "/api/v1/docs/",
            "admin": "/harakacare-admin/",
            "django_admin": "/admin/",
            "setup": "/setup-database/",
            "health": "/health-check/"
        },
        "description": "Healthcare triage and facility management platform for Uganda"
    })


urlpatterns = [
    path('', api_info, name='api_info'),
    path('admin/', admin.site.urls),
    path('harakacare-admin/', harakacare_admin.urls),
    path('setup-production/', setup_production_api, name='setup_production'),
    path('create-users/', create_users_quick, name='create_users'),
    path('setup-database/', setup_database, name='setup_database'),
    path('health-check/', health_check, name='health_check'),

    # API v1 - Versioned endpoints
    path('api/v1/auth/', include('apps.core.urls_auth')),  # Authentication
    path('api/v1/triage/', include('apps.triage.urls')),   # Triage
    path('api/v1/facilities/', include(('apps.facilities.urls', 'facilities_v1'))),  # Facilities
    path('api/v1/chat/', include('apps.messaging.api_urls')),  # Chat triage
    path('api/v1/referrals/', include(('apps.facilities.urls', 'referrals_v1'))),  # Referrals (shared)
    path('api/v1/cases/', include(('apps.facilities.urls', 'cases_v1'))),  # Case management
    path('api/v1/notifications/', include('apps.messaging.urls')),  # Notifications
    path('api/v1/analytics/', include('apps.analytics.urls')),  # Analytics

    # API Schema & Documentation
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/v1/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/v1/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # Legacy endpoints (backward compatibility)
    path('api/', include(('apps.messaging.api_urls', 'messaging_api'))),
    path('api/facilities/', include(('apps.facilities.urls', 'facilities_legacy'))),
    path('messaging/', include(('apps.messaging.urls', 'messaging_legacy'))),
    path("messaging/whatsapp/", include(('apps.messaging.whatsapp.urls', 'whatsapp_legacy'))),
]

# Add debug toolbar URLs in development (only if installed)
if settings.DEBUG:
    try:
        import debug_toolbar
        urlpatterns += [
            path('__debug__/', include(debug_toolbar.urls)),
        ]
    except ImportError:
        pass
