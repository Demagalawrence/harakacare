"""
360dialog WhatsApp API Client
Handles all outbound messaging to WhatsApp via 360dialog's WABA API.
"""

import logging
from typing import Any, Dict, List, Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# 360dialog base URL — use sandbox URL in development
WABA_BASE_URL = getattr(settings, "THREESIXTY_DIALOG_BASE_URL", "https://waba.360dialog.io")
WABA_API_KEY  = getattr(settings, "THREESIXTY_DIALOG_API_KEY", "")

# Timeout for outbound requests (seconds)
REQUEST_TIMEOUT = 15


class DialogClient:
    """
    Thin wrapper around the 360dialog WABA REST API.

    All send_* methods return the raw JSON response dict on success,
    or raise DialogAPIError on failure.
    """

    def __init__(self, api_key: str = WABA_API_KEY, base_url: str = WABA_BASE_URL):
        if not api_key:
            raise ValueError(
                "360dialog API key is not set. "
                "Add THREESIXTY_DIALOG_API_KEY to your Django settings."
            )
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "D360-API-KEY": api_key,
            "Content-Type": "application/json",
        })

    # ------------------------------------------------------------------
    # Core sending
    # ------------------------------------------------------------------

    def send_message(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        POST /v1/messages with an arbitrary payload.
        Returns the API response dict.
        """
        url = f"{self.base_url}/v1/messages"
        try:
            resp = self.session.post(url, json=payload, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            logger.debug(f"360dialog response: {data}")
            return data
        except requests.exceptions.HTTPError as exc:
            body = exc.response.text if exc.response else "(no body)"
            logger.error(f"360dialog HTTP error: {exc.response.status_code} — {body}")
            raise DialogAPIError(f"HTTP {exc.response.status_code}: {body}") from exc
        except requests.exceptions.RequestException as exc:
            logger.error(f"360dialog request failed: {exc}")
            raise DialogAPIError(str(exc)) from exc

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

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
    """Raised when the 360dialog API returns an error."""