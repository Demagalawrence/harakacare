"""
apps/messaging/whatsapp/urls.py
URL routing for the 360dialog WhatsApp webhook.
"""

from django.urls import path
from apps.messaging.whatsapp.whatsapp_views import WhatsAppWebhookView

app_name = "whatsapp"

urlpatterns = [
    path("webhook/", WhatsAppWebhookView.as_view(), name="webhook"),
]


# ============================================================================
# SETUP GUIDE
# ============================================================================
#
# 1. Add to your root urls.py:
#    ----------------------------------------------------------------
#    path("messaging/whatsapp/", include("apps.messaging.whatsapp.urls")),
#
#
# 2. Add to your Django settings (development.py / production.py):
#    ----------------------------------------------------------------
#    # 360dialog credentials — get these from your 360dialog dashboard
#    THREESIXTY_DIALOG_API_KEY       = env("THREESIXTY_DIALOG_API_KEY")
#    THREESIXTY_DIALOG_BASE_URL      = "https://waba.360dialog.io"       # production
#    # THREESIXTY_DIALOG_BASE_URL    = "https://waba-sandbox.360dialog.io"  # sandbox
#    THREESIXTY_DIALOG_WEBHOOK_SECRET = env("THREESIXTY_DIALOG_WEBHOOK_SECRET")
#    THREESIXTY_DIALOG_VERIFY_TOKEN  = env("THREESIXTY_DIALOG_VERIFY_TOKEN", default="harakacare_verify")
#
#
# 3. Register the webhook in the 360dialog dashboard:
#    ----------------------------------------------------------------
#    URL:    https://yourdomain.com/messaging/whatsapp/webhook/
#    Method: POST
#    Events: messages
#    Verify token: (match THREESIXTY_DIALOG_VERIFY_TOKEN above)
#
#
# 4. Required environment variables (.env):
#    ----------------------------------------------------------------
#    THREESIXTY_DIALOG_API_KEY=your_api_key_from_360dialog_dashboard
#    THREESIXTY_DIALOG_WEBHOOK_SECRET=your_shared_secret_from_dashboard
#    THREESIXTY_DIALOG_VERIFY_TOKEN=harakacare_verify
#
#
# ============================================================================
# MESSAGE FLOW DIAGRAM
# ============================================================================
#
#  User sends WhatsApp message
#         │
#         ▼
#  360dialog platform
#         │  POST /messaging/whatsapp/webhook/
#         ▼
#  WhatsAppWebhookView.post()
#         │  Verify signature → Extract message → _process_message()
#         ▼
#  WhatsAppHandler.handle()
#         │
#         ├─ Special command? ──► _handle_reset / _handle_status / _handle_help
#         │
#         └─ Triage message?
#                 │
#                 ├─ New conversation ──► ConversationalIntakeAgent.start_conversation()
#                 └─ Existing session ──► ConversationalIntakeAgent.continue_conversation()
#                         │
#                         ▼
#                  Result from agent
#                         │
#                         ├─ red_flags_detected ──► _send_emergency()  → clear session
#                         ├─ status=incomplete  ──► _send() follow-up question
#                         └─ status=complete    ──► _send_complete()    → clear session
#                                                         │
#                                                         ▼
#                                               TriageOrchestrator.run()
#                                               (already called inside the agent)
#
#
# ============================================================================
# CONVERSATION EXAMPLE
# ============================================================================
#
#  User:  "I have a severe headache and I've been vomiting"
#  Bot:   "I want to help assess your symptoms. How old is the patient?
#          Are you describing your own symptoms or someone else's?"
#
#  User:  "It's me, I'm 32 years old"
#  Bot:   "Have you had any vision changes, neck stiffness, or sensitivity to light?
#          (3/7 fields collected)"
#
#  User:  "Yes my neck is stiff and I can't look at bright light"
#  Bot:   "⚠️ This sounds urgent. How long have these symptoms lasted?"
#
#  User:  "About 6 hours. I'm in Kampala"
#  Bot:   "Do you consent to HarakaCare processing your symptoms for assessment?"
#
#  User:  "Yes I agree"
#  Bot:   "✅ HarakaCare Assessment Complete
#
#          🔴 Risk Level: HIGH
#          Priority: URGENT
#          Recommended facility: hospital
#
#          Seek care at Mulago National Referral Hospital or nearest emergency dept.
#          These symptoms may indicate meningitis or another serious condition.
#
#          Your reference token: PT-ABC123DEFGH456
#          This is not a medical diagnosis..."
#
# ============================================================================
# CELERY ASYNC OPTION (for production scaling)
# ============================================================================
#
# If processing time is too long (>5s), move the handler call to a Celery task:
#
#   # tasks.py
#   from celery import shared_task
#   from apps.messaging.whatsapp.handler import WhatsAppHandler
#
#   @shared_task(bind=True, max_retries=3, default_retry_delay=5)
#   def process_whatsapp_message(self, phone, text, message_id):
#       handler = WhatsAppHandler()
#       try:
#           handler.handle(phone=phone, message_text=text, message_id=message_id)
#       except Exception as exc:
#           raise self.retry(exc=exc)
#
#   # In views.py _process_message(), replace the direct call with:
#   process_whatsapp_message.delay(phone, text, message_id)
#