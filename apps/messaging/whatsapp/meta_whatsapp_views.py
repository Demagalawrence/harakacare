"""
Meta WhatsApp Cloud API Webhook View
Receives and validates inbound webhook events from Meta WhatsApp Cloud API,
then routes them to WhatsApp handler.
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

# Webhook verification token from Meta Developer Dashboard
WEBHOOK_VERIFY_TOKEN = getattr(settings, "META_WHATSAPP_WEBHOOK_VERIFY_TOKEN", "")
# App secret for webhook signature verification
APP_SECRET = getattr(settings, "META_WHATSAPP_APP_SECRET", "")

# Singleton handler (re-used across requests to reuse DB connections etc.)
_handler = WhatsAppHandler()


def _verify_webhook_signature(request) -> bool:
    """
    Verify X-Hub-Signature-256 header sent by Meta.
    Returns True if signature is valid OR if no secret is configured
    (development mode).
    """
    if not APP_SECRET:
        # No secret configured — skip verification (dev/sandbox only)
        logger.warning("META_WHATSAPP_APP_SECRET not set — skipping signature verification")
        return True

    signature_header = request.headers.get("X-Hub-Signature-256", "")
    if not signature_header.startswith("sha256="):
        logger.warning("Webhook received without valid signature header")
        return False

    expected_signature = hmac.new(
        APP_SECRET.encode(),
        request.body,
        hashlib.sha256
    ).hexdigest()

    received_signature = signature_header.split("sha256=")[1]
    is_valid = hmac.compare_digest(expected_signature, received_signature)
    
    if not is_valid:
        logger.warning(f"Webhook signature verification failed. Expected: {expected_signature}, Received: {received_signature}")
    
    return is_valid


@method_decorator(csrf_exempt, name='dispatch')
class MetaWhatsAppWebhookView(View):
    """
    Meta WhatsApp Cloud API webhook endpoint
    Handles incoming messages, status updates, and webhook verification
    """
    
    def get(self, request):
        """
        Handle webhook verification challenge from Meta.
        Called when webhook is first registered.
        """
        verify_token = request.GET.get('hub.verify_token', '')
        challenge = request.GET.get('hub.challenge', '')
        
        logger.info(f"Webhook verification attempt - Token: {verify_token}")
        
        if verify_token == WEBHOOK_VERIFY_TOKEN:
            logger.info("Webhook verification successful")
            return HttpResponse(challenge, content_type='text/plain')
        else:
            logger.warning(f"Webhook verification failed - Invalid token: {verify_token}")
            return HttpResponse("Verification failed", status=403)
    
    def post(self, request):
        """
        Handle incoming webhook events from Meta WhatsApp Cloud API.
        """
        try:
            # Verify webhook signature
            if not _verify_webhook_signature(request):
                return HttpResponse("Signature verification failed", status=403)
            
            # Parse webhook payload
            webhook_data = json.loads(request.body)
            logger.info(f"Meta WhatsApp webhook received: {json.dumps(webhook_data, indent=2)}")
            
            # Handle webhook entry
            if webhook_data.get('object') == 'whatsapp_business_account':
                for entry in webhook_data.get('entry', []):
                    changes = entry.get('changes', [])
                    
                    for change in changes:
                        # Handle messages
                        if change.get('field') == 'messages':
                            messages = change.get('value', {}).get('messages', [])
                            for message in messages:
                                self._handle_message(message)
                        
                        # Handle message status updates
                        elif change.get('field') == 'message_status':
                            status_updates = change.get('value', {}).get('statuses', [])
                            for status in status_updates:
                                self._handle_status_update(status)
            
            return HttpResponse("EVENT_RECEIVED", status=200)
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in webhook: {e}")
            return HttpResponse("Invalid JSON", status=400)
        except Exception as e:
            logger.error(f"Webhook processing error: {e}", exc_info=True)
            return HttpResponse("Processing error", status=500)
    
    def _handle_message(self, message: dict):
        """
        Process an incoming message from Meta WhatsApp Cloud API.
        """
        try:
            # Extract message details
            message_type = message.get('type', 'text')
            from_phone = message.get('from', '')
            message_id = message.get('id', '')
            timestamp = message.get('timestamp', 0)
            
            # Handle different message types
            if message_type == 'text':
                text_content = message.get('text', {}).get('body', '')
                logger.info(f"Text message from {from_phone}: {text_content[:100]}")
                
                # Route to handler
                response = _handler.handle_message(
                    phone=from_phone,
                    message=text_content,
                    message_id=message_id,
                    message_type='text',
                    metadata={
                        'timestamp': timestamp,
                        'message_id': message_id
                    }
                )
                
                # Send response via Meta WhatsApp client
                if response:
                    self._send_response(from_phone, response)
            
            elif message_type == 'interactive':
                # Handle button/list responses
                interactive_data = message.get('interactive', {})
                interactive_type = interactive_data.get('type', '')
                
                if interactive_type == 'button_reply':
                    button_reply = interactive_data.get('button_reply', {})
                    button_id = button_reply.get('id', '')
                    button_title = button_reply.get('title', '')
                    
                    logger.info(f"Button reply from {from_phone}: {button_id} - {button_title}")
                    
                    response = _handler.handle_message(
                        phone=from_phone,
                        message=button_id,  # Use button ID as message
                        message_id=message_id,
                        message_type='button',
                        metadata={
                            'timestamp': timestamp,
                            'button_id': button_id,
                            'button_title': button_title
                        }
                    )
                    
                    if response:
                        self._send_response(from_phone, response)
                
                elif interactive_type == 'list_reply':
                    list_reply = interactive_data.get('list_reply', {})
                    list_id = list_reply.get('id', '')
                    list_title = list_reply.get('title', '')
                    
                    logger.info(f"List reply from {from_phone}: {list_id} - {list_title}")
                    
                    response = _handler.handle_message(
                        phone=from_phone,
                        message=list_id,  # Use list item ID as message
                        message_id=message_id,
                        message_type='list',
                        metadata={
                            'timestamp': timestamp,
                            'list_id': list_id,
                            'list_title': list_title
                        }
                    )
                    
                    if response:
                        self._send_response(from_phone, response)
            
            elif message_type == 'location':
                # Handle location messages
                location_data = message.get('location', {})
                latitude = location_data.get('latitude', 0)
                longitude = location_data.get('longitude', 0)
                location_name = location_data.get('name', '')
                
                logger.info(f"Location from {from_phone}: {latitude}, {longitude} - {location_name}")
                
                response = _handler.handle_message(
                    phone=from_phone,
                    message=f"{latitude},{longitude}",  # Send coordinates as message
                    message_id=message_id,
                    message_type='location',
                    metadata={
                        'timestamp': timestamp,
                        'latitude': latitude,
                        'longitude': longitude,
                        'location_name': location_name
                    }
                )
                
                if response:
                    self._send_response(from_phone, response)
            
            else:
                logger.info(f"Unsupported message type from {from_phone}: {message_type}")
        
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
    
    def _handle_status_update(self, status: dict):
        """
        Handle message status updates (delivered, read, etc.).
        """
        try:
            message_id = status.get('id', '')
            status_type = status.get('status', '')
            timestamp = status.get('timestamp', 0)
            
            logger.info(f"Message {message_id} status: {status_type}")
            
            # Update message status in handler if needed
            _handler.handle_status_update(
                message_id=message_id,
                status=status_type,
                timestamp=timestamp
            )
            
        except Exception as e:
            logger.error(f"Error handling status update: {e}", exc_info=True)
    
    def _send_response(self, to_phone: str, response_data: dict):
        """
        Send response message via Meta WhatsApp client.
        """
        try:
            from apps.messaging.whatsapp.meta_whatsapp_client import meta_whatsapp_client
            
            message = response_data.get('message', '')
            message_type = response_data.get('type', 'text')
            
            if message_type == 'interactive_buttons':
                # Send interactive button message
                buttons = response_data.get('buttons', [])
                header = response_data.get('header', '')
                footer = response_data.get('footer', '')
                
                meta_whatsapp_client.send_interactive_message(
                    to=to_phone,
                    header_text=header,
                    body_text=message,
                    buttons=buttons,
                    footer_text=footer
                )
            
            elif message_type == 'interactive_list':
                # Send interactive list message
                sections = response_data.get('sections', [])
                button_text = response_data.get('button_text', 'View Options')
                header = response_data.get('header', '')
                
                meta_whatsapp_client.send_list_message(
                    to=to_phone,
                    header_text=header,
                    body_text=message,
                    button_text=button_text,
                    sections=sections
                )
            
            elif message_type == 'location_request':
                # Send location request
                meta_whatsapp_client.send_location_request(
                    to=to_phone,
                    message=message
                )
            
            else:
                # Send regular text message
                meta_whatsapp_client.send_message(
                    to=to_phone,
                    message=message,
                    message_type=message_type
                )
            
            # Mark original message as read
            message_id = response_data.get('reply_to_message_id')
            if message_id:
                meta_whatsapp_client.mark_message_as_read(message_id)
                
        except Exception as e:
            logger.error(f"Error sending response: {e}", exc_info=True)
