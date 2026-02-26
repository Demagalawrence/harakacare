"""
360dialog WhatsApp Webhook View
Receives and validates inbound webhook events from 360dialog,
then routes them to the WhatsApp handler.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from apps.messaging.whatsapp.whatsapp_handler import WhatsAppHandler

logger = logging.getLogger(__name__)

# Shared secret set in 360dialog dashboard → used to verify webhook signatures
WEBHOOK_SECRET = getattr(settings, "THREESIXTY_DIALOG_WEBHOOK_SECRET", "")

# Singleton handler (re-used across requests to reuse DB connections etc.)
_handler = WhatsAppHandler()


def _verify_signature(request) -> bool:
    """
    Verify the X-Hub-Signature-256 header sent by 360dialog.
    Returns True if the signature is valid OR if no secret is configured
    (development mode).
    """
    if not WEBHOOK_SECRET:
        # No secret configured — skip verification (dev/sandbox only)
        logger.warning("THREESIXTY_DIALOG_WEBHOOK_SECRET not set — skipping signature check")
        return True

    signature_header = request.headers.get("X-Hub-Signature-256", "")
    if not signature_header.startswith("sha256="):
        logger.warning("Webhook received without valid signature header")
        return False

    expected = hmac.new(
        WEBHOOK_SECRET.encode(),
        request.body,
        hashlib.sha256,
    ).hexdigest()

    received = signature_header[len("sha256="):]
    return hmac.compare_digest(expected, received)


def _extract_messages(payload: dict) -> list[dict]:
    """
    Pull the list of message objects out of the 360dialog webhook payload.
    360dialog uses the standard WhatsApp Cloud API envelope format.
    """
    messages = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for msg in value.get("messages", []):
                # Attach contact info if present
                contacts = value.get("contacts", [])
                if contacts:
                    msg["_contact"] = contacts[0]
                messages.append(msg)
    return messages


@method_decorator(csrf_exempt, name="dispatch")
class WhatsAppWebhookView(View):
    """
    Handles inbound 360dialog webhook requests.

    GET  — Webhook verification challenge (360dialog sends this once during setup)
    POST — Inbound message events
    """

    # ---- Webhook verification ----

    def get(self, request):
        """
        360dialog sends a GET with hub.challenge when you first register
        the webhook URL. Echo the challenge back to confirm ownership.
        """
        mode      = request.GET.get("hub.mode")
        challenge = request.GET.get("hub.challenge")
        token     = request.GET.get("hub.verify_token")

        verify_token = getattr(settings, "THREESIXTY_DIALOG_VERIFY_TOKEN", "harakacare_verify")

        if mode == "subscribe" and token == verify_token:
            logger.info("WhatsApp webhook verified successfully")
            return HttpResponse(challenge, content_type="text/plain", status=200)

        logger.warning(f"Webhook verification failed — mode={mode} token={token!r}")
        return HttpResponse("Forbidden", status=403)

    # ---- Inbound messages ----

    def post(self, request):
        """
        Receive and process inbound WhatsApp messages from 360dialog.
        Always returns 200 quickly — heavy work is done synchronously here
        but can be moved to a Celery task if latency becomes an issue.
        """
        # 1. Verify signature
        if not _verify_signature(request):
            return HttpResponse("Invalid signature", status=403)

        # 2. Parse body
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            logger.error("Webhook body is not valid JSON")
            return HttpResponse("Bad Request", status=400)

        logger.debug(f"Webhook payload: {json.dumps(payload)[:500]}")

        # 3. Extract messages
        messages = _extract_messages(payload)
        if not messages:
            # Status update or other event — acknowledge and ignore
            return JsonResponse({"status": "ok"}, status=200)

        # 4. Deduplicate + process.
        # 360dialog retries the webhook if it doesn't get a fast 200, which causes
        # the same message to be processed multiple times. We guard against this by
        # caching the message_id for 10 minutes (well beyond any retry window).
        from django.core.cache import cache as _cache
        for msg in messages:
            message_id = msg.get("id", "")
            if message_id:
                dedup_key = f"wa_msg_seen:{message_id}"
                if _cache.get(dedup_key):
                    logger.info(f"Skipping duplicate webhook delivery for msg {message_id}")
                    continue
                _cache.set(dedup_key, True, 60 * 10)

            try:
                self._process_message(msg)
            except Exception as exc:
                logger.error(f"Error processing message: {exc}", exc_info=True)

        return JsonResponse({"status": "ok"}, status=200)

    def _process_message(self, msg: dict) -> None:
        """Route a single message object to the WhatsApp handler."""
        msg_type   = msg.get("type")
        message_id = msg.get("id", "")
        phone      = msg.get("from", "")

        if not phone:
            logger.warning("Message missing 'from' field — skipping")
            return

        # ---- Text messages ----
        if msg_type == "text":
            text = msg.get("text", {}).get("body", "").strip()
            if text:
                _handler.handle(phone=phone, message_text=text, message_id=message_id)
            return

        # ---- Button reply (interactive quick-reply) ----
        if msg_type == "interactive":
            interactive = msg.get("interactive", {})
            itype = interactive.get("type")

            if itype == "button_reply":
                btn_id    = interactive["button_reply"]["id"]
                btn_title = interactive["button_reply"]["title"]

                # Map button IDs to natural-language commands
                command_map = {
                    "new_assessment": "reset",
                    "check_status":   "status",
                }
                text = command_map.get(btn_id, btn_title)
                _handler.handle(phone=phone, message_text=text, message_id=message_id)

            elif itype == "list_reply":
                text = interactive["list_reply"].get("title", "")
                _handler.handle(phone=phone, message_text=text, message_id=message_id)
            return

        # ---- Unsupported message types ----
        unsupported = {
            "image":    "images",
            "audio":    "audio/voice messages",
            "video":    "video",
            "document": "documents",
            "location": "location pins",
            "sticker":  "stickers",
            "reaction": None,  # Silently ignore reactions
        }

        label = unsupported.get(msg_type)
        if label:
            logger.info(f"Unsupported message type '{msg_type}' from {phone}")
            _handler.client.send_text(
                phone,
                f"Sorry, I can't process {label} yet. "
                "Please describe your symptoms in text."
            )