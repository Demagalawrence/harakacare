"""
Triage URL Configuration
URL routing for triage API endpoints
"""

from django.urls import path
from apps.triage import conversational_views, views

app_name = 'triage'

urlpatterns = [
    # Start new triage session
    path('start/', views.StartTriageView.as_view(), name='start'),
    path('conversational/', conversational_views.ConversationalTriageView.as_view()),


    
    # Check session status
    path('<str:patient_token>/status/', views.TriageStatusView.as_view(), name='status'),

    # Submit triage data
    path('<str:patient_token>/submit/', views.SubmitTriageView.as_view(), name='submit'),
    

    # Get triage results
    path('<str:patient_token>/', views.TriageResultView.as_view(), name='result'),

    

]