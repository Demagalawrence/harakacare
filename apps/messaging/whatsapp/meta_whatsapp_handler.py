"""
apps/messaging/whatsapp/meta_whatsapp_handler.py

Meta WhatsApp Cloud API ↔ HarakaCare bridge - Enhanced Hybrid State-Machine Edition.

Key features:
- Supports interactive buttons and lists from Meta WhatsApp Cloud API
- Handles location messages and location requests
- Passes message metadata to agent for rich context
- Emergency pre-screen unchanged
- Status / reset / help commands unchanged
- Optimized for Meta's interactive message formats
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Dict, Optional

from django.core.cache import cache

from apps.messaging.whatsapp.meta_whatsapp_client import meta_whatsapp_client, MetaWhatsAppAPIError
from apps.triage.ml_models import detect_emergency_in_text
from apps.triage.tools.conversational_intake_agent import ConversationalIntakeAgent

logger = logging.getLogger(__name__)

# ── Session ────────────────────────────────────────────────────────────────────
_SESSION_PREFIX  = "wa_session:"
_SESSION_TIMEOUT = 60 * 60   # 1 hour of inactivity

# ── Commands ───────────────────────────────────────────────────────────────────
_RESET_CMDS  = {"reset", "restart", "start over", "start again", "new"}
_STATUS_CMDS = {"status", "result", "results", "my result", "check"}
_HELP_CMDS   = {"help", "?", "menu"}


# ── Token / session helpers ────────────────────────────────────────────────────

def _patient_token(phone: str) -> str:
    clean = phone.replace("+", "").replace(" ", "").strip()
    return "PT-" + hashlib.sha256(clean.encode()).hexdigest()[:16].upper()


def _session_active(phone: str) -> bool:
    return cache.get(f"{_SESSION_PREFIX}{phone}") is not None


def _start_session(phone: str) -> None:
    cache.set(f"{_SESSION_PREFIX}{phone}", True, _SESSION_TIMEOUT)


def _clear_session(phone: str) -> None:
    cache.delete(f"{_SESSION_PREFIX}{phone}")


# ── Message formatting for Meta WhatsApp ─────────────────────────────────────

def _format_menu_response(message: str, menu_type: str = "text") -> Dict[str, Any]:
    """
    Format response for Meta WhatsApp Cloud API with interactive elements.
    """
    # Check if message contains structured menu indicators
    if "Reply with" in message and ("1️⃣" in message or "2️⃣" in message):
        return _format_as_interactive_buttons(message)
    elif "Reply with format:" in message and "[number][letter]" in message:
        return _format_as_interactive_buttons(message)
    elif "Reply with 1, 2, or 3" in message:
        return _format_as_interactive_buttons(message)
    
    return {"type": "text", "message": message}


def _format_as_interactive_buttons(message: str) -> Dict[str, Any]:
    """
    Convert numbered menu to interactive buttons for Meta WhatsApp.
    """
    lines = message.split('\n')
    buttons = []
    body_text = ""
    header_text = ""
    footer_text = ""
    
    for line in lines:
        line = line.strip()
        
        # Extract header
        if line.startswith("🤰") or line.startswith("First, I need") or line.startswith("How"):
            if not header_text:
                header_text = line
            else:
                body_text += line + "\n"
            continue
        
        # Extract footer
        if line.startswith("Reply with") and "format:" in line:
            footer_text = line
            continue
        
        # Extract buttons
        if line.startswith(("1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣")):
            # Extract button text
            button_text = line.split('. ', 1)[-1] if '. ' in line else line[2:]
            button_id = line[0]  # First character is the number
            
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": button_id,
                    "title": button_text.strip()
                }
            })
        elif line.startswith(("A.", "B.", "1.", "2.", "3.")):
            # Handle letter options (for age/sex gate)
            parts = line.split('. ', 1)
            if len(parts) == 2:
                button_id = parts[0]
                button_text = parts[1]
                buttons.append({
                    "type": "reply",
                    "reply": {
                        "id": button_id,
                        "title": button_text.strip()
                    }
                })
        elif body_text or header_text:
            body_text += line + "\n"
    
    if not body_text:
        body_text = header_text
        header_text = ""
    
    return {
        "type": "interactive_buttons",
        "message": body_text.strip(),
        "header": header_text.strip(),
        "footer": footer_text.strip(),
        "buttons": buttons
    }


def _format_location_request(message: str) -> Dict[str, Any]:
    """
    Format location request for Meta WhatsApp.
    """
    return {
        "type": "location_request",
        "message": message
    }


# ── Main Handler ─────────────────────────────────────────────────────────────

class MetaWhatsAppHandler:
    """
    Enhanced WhatsApp handler for Meta WhatsApp Cloud API.
    Supports interactive messages, location, and rich metadata.
    """

    def __init__(self):
        self.agent = ConversationalIntakeAgent()
        logger.info("✓ MetaWhatsAppHandler initialized (enhanced hybrid state-machine)")

    def handle_message(self, phone: str, message: str, message_id: str = None,
                    message_type: str = "text", metadata: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Handle incoming message from Meta WhatsApp Cloud API.
        """
        metadata = metadata or {}
        
        try:
            # Emergency pre-screen
            if detect_emergency_in_text(message):
                return self._emergency_response()

            # Command handling
            cmd = message.lower().strip()
            if cmd in _RESET_CMDS:
                _clear_session(phone)
                return self._welcome_response()
            if cmd in _STATUS_CMDS:
                return self._status_response(phone)
            if cmd in _HELP_CMDS:
                return self._help_response()

            # Start session if not active
            if not _session_active(phone):
                _start_session(phone)

            # Route to conversational agent
            result = self.agent.continue_conversation(
                token=_patient_token(phone),
                message=message
            )

            # Handle different response types from agent
            if result.get("status") == "complete":
                return self._completion_response(phone, result)

            # Format response based on agent action
            action = result.get("action", "answer_questions")
            agent_message = result.get("message", "Please continue.")

            if action == "answer_menu":
                # Format as interactive buttons for structured menus
                return _format_menu_response(agent_message, "interactive")
            elif "location" in agent_message.lower() and "share" in agent_message.lower():
                # Format as location request
                return _format_location_request(agent_message)
            else:
                # Regular text response
                return {"type": "text", "message": agent_message}

        except Exception as e:
            logger.error(f"MetaWhatsAppHandler error: {e}", exc_info=True)
            return {"type": "text", "message": "Sorry, I had an error. Please try again."}

    def handle_status_update(self, message_id: str, status: str, timestamp: int):
        """
        Handle message status updates (delivered, read, etc.).
        Currently just logs - could be used for delivery tracking.
        """
        logger.info(f"Message {message_id} status: {status} at {timestamp}")

    # ── Response builders ─────────────────────────────────────────────────────

    def _emergency_response(self) -> Dict[str, Any]:
        return {
            "type": "text",
            "message": (
                "🚨 EMERGENCY DETECTED!\n\n"
                "Please go to the NEAREST HOSPITAL IMMEDIATELY.\n"
                "Call 999 if you cannot travel safely.\n\n"
                "After seeking care, reply 'status' for your assessment."
            )
        }

    def _welcome_response(self) -> Dict[str, Any]:
        return {
            "type": "text",
            "message": (
                "🏥 Welcome to HarakaCare Medical Triage\n\n"
                "I'll ask some questions to assess your condition.\n"
                "This helps determine the right level of care.\n\n"
                "Please describe your main symptom..."
            )
        }

    def _status_response(self, phone: str) -> Dict[str, Any]:
        try:
            from apps.triage.models import TriageSession
            session = TriageSession.objects.filter(
                patient_token=_patient_token(phone)
            ).first()

            if not session:
                return {"type": "text", "message": "No assessment found. Please start over."}

            if session.forwarded_to_facility:
                return {
                    "type": "text", 
                    "message": "✅ Your case has been sent to a healthcare facility."
                }

            risk = session.risk_level or "unknown"
            priority = session.follow_up_priority or "unknown"
            
            return {
                "type": "text",
                "message": f"📋 Your assessment: {risk.title()} risk, {priority} priority."
            }

        except Exception as e:
            logger.error(f"Status response error: {e}")
            return {"type": "text", "message": "Error checking status. Please try again."}

    def _help_response(self) -> Dict[str, Any]:
        return {
            "type": "text",
            "message": (
                "🤖 HarakaCare Commands:\n\n"
                "• Describe your symptom to start assessment\n"
                "• 'status' - Check your assessment result\n"
                "• 'reset' - Start new assessment\n"
                "• 'help' - Show this message\n\n"
                "I'll guide you step by step!"
            )
        }

    def _completion_response(self, phone: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle completed triage with facility assignment.
        """
        try:
            triage_result = result.get("triage_result", {})
            structured_data = result.get("structured_data", {})

            if triage_result.get("error"):
                return {
                    "type": "text",
                    "message": "⚠️ Assessment error. Please try again or contact support."
                }

            risk_level = triage_result.get("risk_level", "unknown")
            facility_type = triage_result.get("facility_type", "clinic")
            recommended_action = triage_result.get("recommended_action", "seek_care")

            # Build completion message
            if risk_level == "high":
                urgency = "🚨 HIGH RISK"
                action = "Go to hospital IMMEDIATELY"
            elif risk_level == "medium":
                urgency = "⚠️ MEDIUM RISK"
                action = "Visit clinic today"
            else:
                urgency = "✅ LOW RISK"
                action = "Monitor at home, seek care if worsening"

            message = (
                f"{urgency}\n\n"
                f"Assessment Complete!\n\n"
                f"Recommended: {action}\n"
                f"Facility type: {facility_type.title()}\n\n"
                f"Reply 'status' for details or 'reset' for new assessment."
            )

            return {"type": "text", "message": message}

        except Exception as e:
            logger.error(f"Completion response error: {e}")
            return {"type": "text", "message": "Error processing results. Please try again."}


# Singleton handler instance
meta_whatsapp_handler = MetaWhatsAppHandler()
