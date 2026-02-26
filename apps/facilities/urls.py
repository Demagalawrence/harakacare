from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router for ViewSet URLs
router = DefaultRouter()
router.register(r'facilities', views.FacilityViewSet, basename='facility')

app_name = 'facilities'

urlpatterns = [
    # API URLs using ViewSet router
    path('api/', include(router.urls)),
]