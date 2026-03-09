"""
API URL patterns for Chat Interface
"""

from django.urls import path
from . import api_views

app_name = 'messaging_api'

urlpatterns = [
    # Chat API endpoints
    path('v1/chat/start/', api_views.ChatStartView.as_view(), name='chat_start'),
    path('v1/chat/continue/<str:patient_token>/', api_views.ChatContinueView.as_view(), name='chat_continue'),
    path('v1/chat/status/<str:patient_token>/', api_views.ChatStatusView.as_view(), name='chat_status'),
]
