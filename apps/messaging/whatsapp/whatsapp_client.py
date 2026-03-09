"""
Meta WhatsApp Cloud API Client
Handles all outbound messaging to WhatsApp via Meta's Cloud API.
Updated from 360dialog to Meta WhatsApp Cloud API.
"""

import logging
import json
import requests
from typing import Any, Dict, List, Optional
from django.conf import settings

logger = logging.getLogger(__name__)

# Meta WhatsApp Cloud API configuration
META_WHATSAPP_API_VERSION = "v18.0"
META_WHATSAPP_BASE_URL = getattr(settings, "META_WHATSAPP_BASE_URL", "https://graph.facebook.com")
META_WHATSAPP_PHONE_NUMBER_ID = getattr(settings, "META_WHATSAPP_PHONE_NUMBER_ID", "")
META_WHATSAPP_ACCESS_TOKEN = getattr(settings, "META_WHATSAPP_ACCESS_TOKEN", "")

# Timeout for outbound requests (seconds)
REQUEST_TIMEOUT = 30


class DialogClient:
    """
    Wrapper around Meta WhatsApp Cloud API.
    Updated from 360dialog to Meta WhatsApp Cloud API.
    
    All send_* methods return raw JSON response dict on success,
    or raise DialogAPIError on failure.
    """

    def __init__(self, 
                 access_token: str = META_WHATSAPP_ACCESS_TOKEN,
                 phone_number_id: str = META_WHATSAPP_PHONE_NUMBER_ID,
                 base_url: str = META_WHATSAPP_BASE_URL,
                 api_version: str = META_WHATSAPP_API_VERSION):
        if not access_token:
            raise ValueError(
                "Meta WhatsApp access token is not set. "
                "Add META_WHATSAPP_ACCESS_TOKEN to your Django settings."
            )
        if not phone_number_id:
            raise ValueError(
                "Meta WhatsApp phone number ID is not set. "
                "Add META_WHATSAPP_PHONE_NUMBER_ID to your Django settings."
            )
        
        self.base_url = base_url.rstrip("/")
        self.api_version = api_version
        self.phone_number_id = phone_number_id
        self.access_token = access_token
        
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        })

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to Meta API with error handling."""
        url = f"{self.base_url}/{self.api_version}/{endpoint}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                timeout=REQUEST_TIMEOUT,
                **kwargs
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Meta API {method} {endpoint}: {result}")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Meta API request failed: {e}")
            raise DialogAPIError(f"Request failed: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Meta API response decode failed: {e}")
            raise DialogAPIError(f"Invalid JSON response: {e}")

    # ------------------------------------------------------------------
    # Core sending methods
    # ------------------------------------------------------------------

    def send_message(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a message to WhatsApp user.
        Updated for Meta WhatsApp Cloud API format.
        """
        return self._make_request("POST", f"{self.phone_number_id}/messages", json=payload)

    def send_text(self, to: str, body: str, preview_url: bool = False) -> Dict[str, Any]:
        """Send a plain-text WhatsApp message."""
        return self.send_message({
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {
                "preview_url": preview_url,
                "body": body,
            },
        })

    def send_interactive_buttons(
        self,
        to: str,
        body_text: str,
        buttons: List[Dict[str, str]],
        header_text: Optional[str] = None,
        footer_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send an interactive message with quick-reply buttons.

        buttons: list of {"id": "btn_id", "title": "Button label"} (max 3)
        """
        msg: Dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body_text},
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {"id": b["id"], "title": b["title"][:20]},
                        }
                        for b in buttons[:3]
                    ]
                },
            },
        }
        if header_text:
            msg["interactive"]["header"] = {"type": "text", "text": header_text}
        if footer_text:
            msg["interactive"]["footer"] = {"text": footer_text}
        return self.send_message(msg)

    def send_interactive_list(
        self,
        to: str,
        body_text: str,
        button_label: str,
        sections: List[Dict[str, Any]],
        header_text: Optional[str] = None,
        footer_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a list-picker interactive message.

        sections: [{"title": "Section", "rows": [{"id": "r1", "title": "Row", "description": "..."}]}]
        """
        msg: Dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": body_text},
                "action": {
                    "button": button_label[:20],
                    "sections": sections,
                },
            },
        }
        if header_text:
            msg["interactive"]["header"] = {"type": "text", "text": header_text}
        if footer_text:
            msg["interactive"]["footer"] = {"text": footer_text}
        return self.send_message(msg)

    def send_template(
        self,
        to: str,
        template_name: str,
        language_code: str = "en",
        components: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """Send an approved WhatsApp template message."""
        payload: Dict[str, Any] = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
            },
        }
        if components:
            payload["template"]["components"] = components
        return self.send_message(payload)

    def mark_as_read(self, to: str, message_id: str) -> Dict[str, Any]:
        """Mark an incoming message as read (shows double blue tick)."""
        return self.send_message({
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        })

    def send_typing(self, to: str) -> None:
        """Best-effort: mark as read to show 'typing' indicator on some clients."""
        try:
            self.send_text(to, "⏳")  # Temporary — remove if you prefer silence
        except DialogAPIError:
            pass


class DialogAPIError(Exception):
    """Raised when the Meta WhatsApp API returns an error."""
    pass


# Singleton instance for reuse across the application
try:
    dialog_client = DialogClient()
except ValueError as e:
    print(f"⚠️  WhatsApp client not initialized: {e}")
    dialog_client = None
except Exception as e:
    print(f"⚠️  WhatsApp client initialization failed: {e}")
    dialog_client = None
