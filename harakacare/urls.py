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
from apps.triage.admin import harakacare_admin

urlpatterns = [
    path('admin/', admin.site.urls),  # Default Django admin
    path('harakacare-admin/', harakacare_admin.urls),  # Custom HarakaCare admin
    path('api/', include('apps.messaging.api_urls')),  # Chat API endpoints
    path('api/facilities/', include('apps.facilities.urls')),  # Facility API endpoints
    path('api/v1/triage/', include('apps.triage.urls')),  # Triage API endpoints
    # Temporarily disabled WhatsApp endpoints - need META_WHATSAPP_ACCESS_TOKEN
    # path('messaging/', include('apps.messaging.urls')),  # Messaging endpoints
    # path("messaging/whatsapp/", include("apps.messaging.whatsapp.urls")),  # WhatsApp endpoints
]

# Add debug toolbar URLs in development
if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]