from django.urls import path
from apps.messaging import views

app_name = 'messaging'

urlpatterns = [
    # USSD endpoint
    path('ussd/callback/', views.USSDCallbackView.as_view(), name='ussd-callback'),
    
    # Other messaging endpoints (SMS, WhatsApp, etc.) will go here
]