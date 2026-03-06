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
    
    # Direct auth endpoints
    path('auth/login/', views.facility_login),
    path('auth/logout/', views.facility_logout),
    path('auth/whoami/', views.facility_whoami),
    
    # Direct case management endpoints
    path('cases/', views.get_cases),
    path('cases/<str:case_id>/confirm/', views.confirm_case),
    path('cases/<str:case_id>/reject/', views.reject_case),
    path('cases/<str:case_id>/acknowledge/', views.acknowledge_case),
    path('cases/<str:case_id>/delete/', views.delete_case),
    path('stats/', views.get_stats),
]