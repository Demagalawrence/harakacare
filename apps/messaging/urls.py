from django.urls import path, include
from apps.messaging import views

app_name = 'messaging'

urlpatterns = [
    # USSD endpoint
    path('ussd/callback/', views.USSDCallbackView.as_view(), name='ussd-callback'),
    
    # WhatsApp endpoints (Meta Cloud API + Legacy 360Dialog)
    path('whatsapp/', include("apps.messaging.whatsapp.urls")),
    
    # Other messaging endpoints (SMS, etc.) will go here
]