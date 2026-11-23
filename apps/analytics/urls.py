"""
Analytics URL configuration for HarakaCare API v1.
"""
from django.urls import path
from apps.analytics import views

urlpatterns = [
    path('', views.analytics_overview, name='analytics-overview'),
]
