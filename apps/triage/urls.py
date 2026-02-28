"""
Triage URL Configuration
URL routing for triage API endpoints
UPDATED FOR COMPLAINT-BASED, AGE-ADAPTIVE TRIAGE
"""

from django.urls import path
from apps.triage import conversational_views, views

app_name = 'triage'

urlpatterns = [

    # ---- Conversational ----
    path('conversational/', conversational_views.ConversationalTriageView.as_view(), name='conversational-triage'),
    path('conversational/<str:patient_token>/status/', conversational_views.ConversationalStatusView.as_view(), name='conversational-status'),
    path('conversational/<str:patient_token>/history/', conversational_views.ConversationalHistoryView.as_view(), name='conversational-history'),
    path('conversational/<str:patient_token>/reset/', conversational_views.ConversationalResetView.as_view(), name='conversational-reset'),
    path('conversational/<str:patient_token>/next-question/', views.GetNextQuestionView.as_view(), name='conversational-next'),

    # ---- Structured ----
    path('start/', views.StartTriageView.as_view(), name='start'),
    path('<str:patient_token>/status/', views.TriageStatusView.as_view(), name='status'),
    path('<str:patient_token>/submit/', views.SubmitTriageView.as_view(), name='submit'),

    # ---- Adaptive ----
    path('adaptive/start/', views.StartConversationView.as_view(), name='adaptive-start'),
    path('adaptive/<str:patient_token>/update/', views.UpdateSymptomsView.as_view(), name='adaptive-update'),
    path('adaptive/<str:patient_token>/next/', views.GetNextQuestionView.as_view(), name='adaptive-next'),

    # ---- Hybrid ----
    path('hybrid/<str:patient_token>/', conversational_views.HybridTriageView.as_view(), name='hybrid-triage'),

    # ---- Utility ----
    path('health/', views.TriageHealthCheckView.as_view(), name='health'),
    path('options/', views.TriageOptionsView.as_view(), name='options'),

    # ⚠️ ALWAYS LAST
    path('<str:patient_token>/', views.TriageResultView.as_view(), name='result'),
]

# ============================================================================
# URL PATTERNS SUMMARY
# ============================================================================

"""
COMPLETE URL PATTERNS FOR TRIAGE API:

┌─────────────────────────────────┬─────────────────────────────────────┐
│ URL                              │ Purpose                             │
├─────────────────────────────────┼─────────────────────────────────────┤
│ LEGACY (Structured)              │                                     │
├─────────────────────────────────┼─────────────────────────────────────┤
│ POST   /triage/start/            │ Generate new patient token          │
│ GET    /triage/<token>/status/   │ Check session status                │
│ POST   /triage/<token>/submit/   │ Submit complete structured data     │
│ GET    /triage/<token>/          │ Get triage results                  │
├─────────────────────────────────┼─────────────────────────────────────┤
│ CONVERSATIONAL (WhatsApp-style)  │                                     │
├─────────────────────────────────┼─────────────────────────────────────┤
│ POST   /triage/conversational/   │ Start/continue conversation         │
│ GET    /triage/conversational/<token>/status/   │ Get conversation status │
│ GET    /triage/conversational/<token>/history/  │ Get full history       │
│ POST   /triage/conversational/<token>/reset/    │ Reset conversation     │
│ GET    /triage/conversational/<token>/next-question/ │ Get next question  │
├─────────────────────────────────┼─────────────────────────────────────┤
│ ADAPTIVE (Structured conversation) │                                   │
├─────────────────────────────────┼─────────────────────────────────────┤
│ POST   /triage/adaptive/start/   │ Start adaptive conversation         │
│ POST   /triage/adaptive/<token>/update/ │ Update symptoms              │
│ GET    /triage/adaptive/<token>/next/   │ Get next question            │
├─────────────────────────────────┼─────────────────────────────────────┤
│ HYBRID                           │                                     │
├─────────────────────────────────┼─────────────────────────────────────┤
│ POST   /triage/hybrid/<token>/   │ Accept structured OR conversational │
├─────────────────────────────────┼─────────────────────────────────────┤
│ UTILITY                          │                                     │
├─────────────────────────────────┼─────────────────────────────────────┤
│ GET    /triage/health/           │ Health check                        │
│ GET    /triage/options/          │ Get available form options          │
└─────────────────────────────────┴─────────────────────────────────────┘


EXAMPLE USAGE:

1. Start a new conversation:
   POST /api/v1/triage/conversational/
   {
       "message": "I have fever and headache"
   }

2. Continue conversation:
   POST /api/v1/triage/conversational/
   {
       "message": "I'm 25 years old",
       "conversation_id": "PT-ABC123"
   }

3. Check conversation status:
   GET /api/v1/triage/conversational/PT-ABC123/status/

4. Get conversation history:
   GET /api/v1/triage/conversational/PT-ABC123/history/

5. Submit structured data directly:
   POST /api/v1/triage/PT-ABC123/submit/
   {
       "complaint_group": "fever",
       "age_group": "adult",
       "symptom_severity": "moderate",
       ...
   }

6. Use hybrid endpoint (auto-detects input type):
   POST /api/v1/triage/hybrid/PT-ABC123/
   {
       "message": "I have fever"  ← conversational mode
   }
   OR
   {
       "complaint_group": "fever",  ← structured mode
       "age_group": "adult"
   }
"""