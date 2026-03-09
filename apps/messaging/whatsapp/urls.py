"""
apps/messaging/whatsapp/urls.py
URL routing for Meta WhatsApp Cloud API webhook.
Updated from 360dialog to Meta WhatsApp Cloud API.
"""

from django.urls import path
from apps.messaging.whatsapp.whatsapp_views import WhatsAppWebhookView

app_name = "whatsapp"

urlpatterns = [
    # Meta WhatsApp Cloud API webhook (main endpoint)
    path("webhook/", WhatsAppWebhookView.as_view(), name="webhook"),
    
    # Meta WhatsApp Cloud API webhook (without trailing slash for Meta compatibility)
    path("webhook", WhatsAppWebhookView.as_view(), name="webhook_noslash"),
    
    # Meta WhatsApp Cloud API webhook (alternative endpoint for Meta's URL format)
    path("meta/webhook/", WhatsAppWebhookView.as_view(), name="meta_webhook"),
    
    # Meta WhatsApp Cloud API webhook (without trailing slash)
    path("meta/webhook", WhatsAppWebhookView.as_view(), name="meta_webhook_noslash"),
]


# ============================================================================
# META WHATSAPP CLOUD API SETUP GUIDE
# ============================================================================
#
# 1. Add to your root urls.py:
#    ----------------------------------------------------------------
#    path("messaging/whatsapp/", include("apps.messaging.whatsapp.urls")),
#
#
# 2. Add to your Django settings (development.py / production.py):
#    ----------------------------------------------------------------
#    # Meta WhatsApp Cloud API credentials - get from Meta Developers Dashboard
#    META_WHATSAPP_ACCESS_TOKEN      = env("META_WHATSAPP_ACCESS_TOKEN")
#    META_WHATSAPP_PHONE_NUMBER_ID   = env("META_WHATSAPP_PHONE_NUMBER_ID")
#    META_WHATSAPP_WEBHOOK_VERIFY_TOKEN = env("META_WHATSAPP_WEBHOOK_VERIFY_TOKEN", default="harakacare_meta_verify")
#    META_WHATSAPP_APP_SECRET         = env("META_WHATSAPP_APP_SECRET")
#    META_WHATSAPP_BASE_URL          = "https://graph.facebook.com"  # production
#
#
# 3. Configure webhook in Meta Developers Dashboard:
#    ----------------------------------------------------------------
#    URL:    https://yourdomain.com/messaging/whatsapp/webhook/
#    Method: POST
#    Verify token: (match META_WHATSAPP_WEBHOOK_VERIFY_TOKEN above)
#    Fields: messages, message_status
#    App secret: (match META_WHATSAPP_APP_SECRET above)
#
#
# 4. Required environment variables (.env):
#    ----------------------------------------------------------------
#    META_WHATSAPP_ACCESS_TOKEN=your_access_token_from_meta_dashboard
#    META_WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id_from_meta
#    META_WHATSAPP_WEBHOOK_VERIFY_TOKEN=harakacare_meta_verify
#    META_WHATSAPP_APP_SECRET=your_app_secret_from_meta
#
#
# ============================================================================
# MESSAGE FLOW DIAGRAM (Meta WhatsApp Cloud)
# ============================================================================
#
#  User sends WhatsApp message
#         │
#         ▼
#  Meta WhatsApp Cloud API
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
#                         ├─ status=incomplete  ──► _format_menu_response() → interactive buttons
#                         └─ status=complete    ──► _send_complete()    → clear session
#                                                         │
#                                                         ▼
#                                               TriageOrchestrator.run()
#                                               (already called inside the agent)
#
#
# ============================================================================
# INTERACTIVE MESSAGE EXAMPLES
# ============================================================================
#
# Age/Sex Gate as Interactive Buttons:
# "First, I need to know who we're helping. Please select:"
# → Shows buttons: "1️⃣ Newborn Male", "1️⃣ Newborn Female", etc.
#
# Pregnancy Status as Interactive Buttons:
# "🤰 Is patient currently pregnant?"
# → Shows buttons: "1️⃣ Yes", "2️⃣ No", "3️⃣ Not sure"
#
# Location Request:
# "Please share your location for better facility matching."
# → Shows location request button
#
# ============================================================================
# TESTING
# ============================================================================
#
# Test webhook verification:
# curl -X GET "https://yourdomain.com/messaging/whatsapp/webhook/?hub.verify_token=harakacare_meta_verify"
#
# Should return the hub.challenge value if successful.
