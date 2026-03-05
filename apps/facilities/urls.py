from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views, views_facility_agent

# Create router for ViewSet URLs
router = DefaultRouter()
router.register(r'facilities', views.FacilityViewSet, basename='facility')
router.register(r'agent', views_facility_agent.FacilityAgentViewSet, basename='facility-agent')

app_name = 'facilities'

urlpatterns = [
    # API URLs using ViewSet router
    path('api/', include(router.urls)),
    # Facility dashboard auth
    path('auth/login/', views.facility_login),
    path('auth/logout/', views.facility_logout),
    path('auth/whoami/', views.facility_whoami),
    # Direct endpoints for cases and stats
    path('cases/', views.get_cases),
    path('cases/<str:case_id>/confirm/', views.confirm_case),
    path('cases/<str:case_id>/reject/', views.reject_case),
    path('cases/<str:case_id>/acknowledge/', views.acknowledge_case),
    path('cases/<str:case_id>/delete/', views.delete_case),
    path('stats/', views.get_stats),
]