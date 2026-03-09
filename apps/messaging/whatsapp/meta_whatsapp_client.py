"""
Meta WhatsApp Cloud API Client
Handles all outbound messaging to WhatsApp via Meta's Cloud API.
Replaces 360dialog WhatsApp API client.
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
META_WHATSAPP_WEBHOOK_VERIFY_TOKEN = getattr(settings, "META_WHATSAPP_WEBHOOK_VERIFY_TOKEN", "")

# Timeout for outbound requests (seconds)
REQUEST_TIMEOUT = 15


class MetaWhatsAppClient:
    """
    Wrapper around Meta WhatsApp Cloud API.
    
    All send_* methods return raw JSON response dict on success,
    or raise MetaWhatsAppAPIError on failure.
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
            raise MetaWhatsAppAPIError(f"Request failed: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Meta API response decode failed: {e}")
            raise MetaWhatsAppAPIError(f"Invalid JSON response: {e}")

    # ------------------------------------------------------------------
    # Core sending methods
    # ------------------------------------------------------------------

    def send_message(self, to: str, message: str, message_type: str = "text") -> Dict[str, Any]:
        """
        Send a text message to a WhatsApp user.
        
        Args:
            to: WhatsApp phone number (with country code, no + or spaces)
            message: Message content
            message_type: Type of message (text, template, etc.)
            
        Returns:
            API response dict
        """
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": message_type,
            "text": {
                "body": message
            }
        }
        
        return self._make_request("POST", f"{self.phone_number_id}/messages", json=payload)

    def send_interactive_message(self, to: str, header_text: str, body_text: str, 
                            buttons: List[Dict[str, str]], footer_text: str = None) -> Dict[str, Any]:
        """
        Send an interactive message with buttons (for structured menus).
        
        Args:
            to: WhatsApp phone number
            header_text: Optional header text
            body_text: Main message content
            buttons: List of button dictionaries [{"id": "1", "title": "Option 1"}]
            footer_text: Optional footer text
            
        Returns:
            API response dict
        """
        interactive_content = {
            "type": "button",
            "body": {
                "text": body_text
            },
            "action": {
                "buttons": buttons
            }
        }
        
        if header_text:
            interactive_content["header"] = {
                "type": "text",
                "text": header_text
            }
        
        if footer_text:
            interactive_content["footer"] = {
                "text": footer_text
            }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "interactive",
            "interactive": interactive_content
        }
        
        return self._make_request("POST", f"{self.phone_number_id}/messages", json=payload)

    def send_list_message(self, to: str, header_text: str, body_text: str,
                       button_text: str, sections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Send an interactive list message (for multi-select menus).
        
        Args:
            to: WhatsApp phone number
            header_text: Optional header text
            body_text: Main message content
            button_text: Button text (e.g., "View Options")
            sections: List of section dictionaries with title and rows
            
        Returns:
            API response dict
        """
        interactive_content = {
            "type": "list",
            "body": {
                "text": body_text
            },
            "action": {
                "button": button_text,
                "sections": sections
            }
        }
        
        if header_text:
            interactive_content["header"] = {
                "type": "text",
                "text": header_text
            }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "interactive",
            "interactive": interactive_content
        }
        
        return self._make_request("POST", f"{self.phone_number_id}/messages", json=payload)

    def send_location_request(self, to: str, message: str) -> Dict[str, Any]:
        """
        Send a location request message.
        
        Args:
            to: WhatsApp phone number
            message: Message to accompany location request
            
        Returns:
            API response dict
        """
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "location_request_message",
                "body": {
                    "text": message
                },
                "action": {
                    "name": "send_location"
                }
            }
        }
        
        return self._make_request("POST", f"{self.phone_number_id}/messages", json=payload)

    def mark_message_as_read(self, message_id: str) -> Dict[str, Any]:
        """
        Mark a message as read.
        
        Args:
            message_id: WhatsApp message ID
            
        Returns:
            API response dict
        """
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
        
        return self._make_request("POST", "messages", json=payload)

    # ------------------------------------------------------------------
    # Template messages
    # ------------------------------------------------------------------

    def send_template_message(self, to: str, template_name: str, 
                         components: List[Dict[str, Any]] = None,
                         language_code: str = "en") -> Dict[str, Any]:
        """
        Send a WhatsApp template message.
        
        Args:
            to: WhatsApp phone number
            template_name: Template name
            components: Template components
            language_code: Language code
            
        Returns:
            API response dict
        """
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": language_code
                }
            }
        }
        
        if components:
            payload["template"]["components"] = components
        
        return self._make_request("POST", f"{self.phone_number_id}/messages", json=payload)

    # ------------------------------------------------------------------
    # Media messages
    # ------------------------------------------------------------------

    def upload_media(self, file_path: str, media_type: str) -> Dict[str, Any]:
        """
        Upload media to WhatsApp servers.
        
        Args:
            file_path: Path to media file
            media_type: Media type (image, audio, document, video)
            
        Returns:
            API response dict with media ID
        """
        with open(file_path, 'rb') as file:
            files = {
                'file': (file_path, file, f'{media_type}/*')
            }
            data = {
                'messaging_product': 'whatsapp',
                'type': media_type
            }
            
            return self._make_request("POST", "media", files=files, data=data)

    def send_media_message(self, to: str, media_id: str, 
                         caption: str = None, media_type: str = "image") -> Dict[str, Any]:
        """
        Send a media message.
        
        Args:
            to: WhatsApp phone number
            media_id: Media ID from upload
            caption: Optional caption
            media_type: Media type
            
        Returns:
            API response dict
        """
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": media_type,
            f"{media_type}": {
                "id": media_id
            }
        }
        
        if caption:
            payload[f"{media_type}"]["caption"] = caption
        
        return self._make_request("POST", f"{self.phone_number_id}/messages", json=payload)


class MetaWhatsAppAPIError(Exception):
    """Raised when Meta WhatsApp API returns an error."""
    pass


# Singleton instance for reuse across the application
meta_whatsapp_client = MetaWhatsAppClient()
