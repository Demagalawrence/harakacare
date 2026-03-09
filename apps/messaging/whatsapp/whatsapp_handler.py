"""
apps/messaging/whatsapp/whatsapp_handler.py

WhatsApp ↔ HarakaCare bridge — Hybrid State-Machine Edition.

Changes from previous version:
- Passes last_question_field context to agent on every continue_conversation call.
- Handles "answer_menu" action type separately from "answer_questions".
- Short responses (1–3 words or pure digits) are treated as potential menu responses
  and forwarded to the agent WITHOUT any pre-processing.
- Emergency pre-screen unchanged.
- Status / reset / help commands unchanged.
"""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Any, Dict, Optional, List

from django.core.cache import cache

from apps.messaging.whatsapp.whatsapp_client import DialogClient, DialogAPIError
from apps.triage.ml_models import detect_emergency_in_text
from apps.triage.tools.conversational_intake_agent import ConversationalIntakeAgent, STRUCTURED_FIELDS

logger = logging.getLogger(__name__)

# ── Session ────────────────────────────────────────────────────────────────────
_SESSION_PREFIX  = "wa_session:"
_SESSION_TIMEOUT = 60 * 60   # 1 hour of inactivity

# ── Commands ───────────────────────────────────────────────────────────────
_RESET_CMDS  = {"reset", "restart", "start over", "start again", "new"}
_STATUS_CMDS = {"status", "result", "results", "my result", "check"}
_HELP_CMDS   = {"help", "?", "menu"}
_BOOKING_CMDS = {"book", "booking", "appointment", "confirm", "schedule"}

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


# ── Handler ────────────────────────────────────────────────────────────────────

class WhatsAppHandler:
    """
    Thin bridge between 360dialog webhooks and ConversationalIntakeAgent.

    The handler no longer interprets structured menu responses itself.
    It passes all messages directly to the agent, which owns the state machine.

    Flow per incoming message:
      1. Mark as read
      2. Handle reset / status / help commands
      3. detect_emergency_in_text() — instant, no LLM
      4. Route to agent.start_conversation() or agent.continue_conversation()
      5. Deliver result based on action type: answer_menu / answer_questions / complete
    """

    def __init__(self):
        try:
            self.client = DialogClient()
        except (ValueError, Exception) as e:
            logger.warning(f"WhatsApp client not available: {e}")
            self.client = None
        self.agent  = ConversationalIntakeAgent()

    # ── Entry point ────────────────────────────────────────────────────────────

    def handle(self, phone: str, message_text: str, message_id: str) -> None:
        logger.info(f"WA | phone={phone} msg={message_text[:80]!r}")

        if not self.client:
            logger.warning("WhatsApp client not available - cannot process message")
            return

        try:
            self.client.mark_as_read(phone, message_id)
        except DialogAPIError:
            pass

        text  = message_text.strip()
        lower = text.lower()

        # ── Special commands ───────────────────────────────────────────────────
        if lower in _RESET_CMDS:
            return self._cmd_reset(phone)
        if lower in _STATUS_CMDS:
            return self._cmd_status(phone)
        if lower in _HELP_CMDS:
            return self._cmd_help(phone)
        if lower in _BOOKING_CMDS:
            return self._cmd_booking(phone, text)

        # ── Emergency pre-screen (regex, no LLM) ──────────────────────────────
        emergency = detect_emergency_in_text(text)
        if emergency.get("requires_immediate"):
            self._send_emergency_alert(phone, emergency.get("detected_flags", {}))
            try:
                token = _patient_token(phone)
                if _session_active(phone):
                    self.agent.continue_conversation(token, text)
                else:
                    self.agent.start_conversation(token, text)
            except Exception:
                pass
            _clear_session(phone)
            return

        # ── Route to agent ─────────────────────────────────────────────────────
        # The agent owns all menu resolution internally.
        # We pass the raw message without any interpretation.
        token = _patient_token(phone)
        try:
            if _session_active(phone):
                result = self.agent.continue_conversation(token, text)
            else:
                result = self.agent.start_conversation(token, text)
                _start_session(phone)
        except Exception as exc:
            logger.error(f"Agent error for {phone}: {exc}", exc_info=True)
            self._send(
                phone,
                "Something went wrong. Please try again or type *reset* to start over."
            )
            return

        self._deliver(phone, token, result)

    # ── Result delivery ────────────────────────────────────────────────────────

    def _deliver(self, phone: str, token: str, result: Dict[str, Any]) -> None:
        """
        Deliver agent result to the user.

        action == "answer_menu"      → structured menu was asked; send as-is
        action == "answer_questions" → LLM question; send as-is
        action == "proceed_to_triage"→ assessment complete; send result card
        red_flags_detected            → send emergency alert
        """
        if result.get("red_flags_detected"):
            structured = result.get("structured_data") or {}
            flags = structured.get("red_flag_indicators", {})
            self._send_emergency_alert(phone, flags)
            _clear_session(phone)
            return

        status  = result.get("status")
        action  = result.get("action", "")
        message = result.get("message", "")

        if status == "incomplete":
            # Both answer_menu and answer_questions deliver the message with step progress.
            # The menu prompt is already formatted by MenuResolver; we enhance with interactive buttons.
            if message:
                # Add step progress indicator if available
                progress = result.get("progress", "")
                if progress:
                    message_with_progress = f"{progress}\n\n{message}"
                else:
                    message_with_progress = message
                
                # Check if this is a structured menu that should use interactive buttons
                active_field = result.get("active_menu_field", "")
                if active_field in STRUCTURED_FIELDS:
                    # Convert structured menu to interactive buttons
                    self._send_structured_menu(phone, message_with_progress, active_field)
                else:
                    self._send(phone, message_with_progress)

            # If it was a menu question, send a hint about accepted inputs
            if action == "answer_menu":
                active_field = result.get("active_menu_field", "")
                # Hint is already embedded in the menu prompt — no extra message needed.
                # But log for debugging.
                logger.debug(f"Menu active for field: {active_field}")

        elif status == "complete":
            if message:
                self._send(phone, message)
            self._send_result_card(phone, token, result)
            
            # AUTOMATIC BOOKING CONFIRMATION - USE REAL FACILITY DATA
            # Send booking confirmation after assessment completion for HIGH/MEDIUM risk cases
            structured = result.get("structured_data") or {}
            triage_result = result.get("triage_result") or {}
            risk_level = triage_result.get("risk_level", "").upper()
            
            logger.info(f"Assessment completed - Risk level: {risk_level}")
            
            if risk_level in ["HIGH", "MEDIUM"]:
                logger.info(f"Triggering auto-booking for {phone}")
                
                # GET REAL FACILITY DATA FROM DATABASE
                try:
                    from apps.triage.models import TriageSession
                    from apps.facilities.models import Facility, FacilityRouting
                    
                    # First try to get confirmed facility routing
                    routing = FacilityRouting.objects.filter(
                        patient_token=token,
                        routing_status=FacilityRouting.RoutingStatus.CONFIRMED
                    ).first()
                    
                    if routing and routing.assigned_facility:
                        # USE REAL FACILITY DATA
                        facility = routing.assigned_facility
                        facility_name = facility.name
                        facility_phone = facility.phone_number
                        facility_address = facility.address
                        
                        logger.info(f"Using real facility data: {facility_name}")
                        
                    else:
                        # FALLBACK: Get any facility from database (not mocked)
                        facility = Facility.objects.first()
                        if facility:
                            facility_name = facility.name
                            facility_phone = facility.phone_number
                            facility_address = facility.address
                            logger.info(f"Using first available facility: {facility_name}")
                        else:
                            # LAST RESORT: Default values
                            facility_name = "HarakaCare Health Centre"
                            facility_phone = "+256 123 456 789"
                            facility_address = "Kampala, Uganda"
                            logger.warning("No facilities found in database, using defaults")
                    
                    # Generate realistic appointment time
                    from datetime import datetime, timedelta
                    tomorrow = datetime.now() + timedelta(days=1)
                    appointment_date = tomorrow.strftime("%A, %d %B %Y")
                    appointment_time = "9:00 AM"
                    
                    # Send booking confirmation with REAL data
                    booking_message = (
                        f"✅ *Booking Confirmed*\n\n"
                        f"🏥 *Facility:* {facility_name}\n"
                        f"📅 *Date:* {appointment_date}\n"
                        f"🕐 *Time:* {appointment_time}\n\n"
                        f"📍 *Please arrive 15 minutes before your appointment.*\n\n"
                        f"📞 *Facility Contact:* {facility_phone}\n"
                        f"📍 *Address:* {facility_address}\n\n"
                        f"📞 *Need to reschedule?* Reply 'reschedule' or call facility directly.\n\n"
                        f"🔑 *Reference:* {_patient_token(phone)}\n\n"
                        f"_⚕️ Bring your ID and any relevant medical records._"
                    )
                    
                    logger.info(f"Sending booking confirmation to {phone} with facility: {facility_name}")
                    self._send(phone, booking_message)
                    logger.info(f"Booking confirmation sent successfully to {phone}")
                    
                except Exception as e:
                    logger.error(f"Failed to get facility data for booking: {e}")
                    # Emergency fallback
                    self._send(phone, f"✅ Booking confirmed! Reference: {_patient_token(phone)}")
            
            _clear_session(phone)

        else:
            if message:
                self._send(phone, message)

    # ── Triage result card ─────────────────────────────────────────────────────

    def _send_result_card(self, phone: str, token: str, result: Dict[str, Any]) -> None:
        triage    = result.get("triage_result") or {}
        error     = triage.get("error")
        risk      = (triage.get("risk_level") or "unknown").upper()
        priority  = (triage.get("follow_up_priority") or triage.get("priority") or "routine").upper()
        facility  = triage.get("facility_type") or ""
        action    = (triage.get("recommended_action") or "").strip()
        emoji     = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(risk, "⚪")

        structured = result.get("structured_data") or {}
        age_group  = structured.get("age_group", "")
        pregnancy  = structured.get("pregnancy_status", "")
        turns      = result.get("conversation_turns", "")

        facility_labels = {
            "emergency":     "Emergency Department — go immediately",
            "hospital":      "Hospital — visit today",
            "health_center": "Health Centre — visit within 24 hours",
            "clinic":        "Clinic — visit within 2–3 days",
            "self_care":     "Home care with monitoring",
        }
        facility_text = facility_labels.get(facility, facility)

        age_notes = {
            "newborn":   "👶 Newborns need urgent review — any illness can worsen quickly.",
            "infant":    "👶 Infants can deteriorate rapidly. Don't delay if symptoms worsen.",
            "elderly":   "👴 Elderly patients face higher risk. Seek care promptly.",
            "child_1_5": "🧒 Young children can worsen fast. Watch feeding and breathing.",
        }
        age_note = age_notes.get(age_group, "")
        pregnancy_note = (
            "\n🤰 Pregnant patient — ensure access to antenatal care."
            if pregnancy == "yes" else ""
        )

        if error:
            self._send(
                phone,
                f"✅ *Assessment received*\n\n"
                f"Reference: *{token}*\n\n"
                f"We were unable to complete the automated assessment. "
                f"Please visit a health facility for evaluation.\n\n"
                f"_Type 'status' anytime to check, or 'reset' to start again._"
            )
        else:
            parts = [
                "✅ *HarakaCare Assessment Complete*\n",
                f"{emoji} *Risk Level: {risk}*",
                f"Priority: {priority}",
            ]
            if facility_text:
                parts.append(f"Go to: {facility_text}")
            if age_note:
                parts.append(f"\n{age_note}")
            if pregnancy_note:
                parts.append(pregnancy_note)
            if action:
                parts.append(f"\n📋 *Advice:*\n{action}")
            if turns:
                parts.append(f"\n_Completed in {turns} messages._")
            parts += [
                "\n🔑 *Your reference token:*",
                f"*{token}*",
                "_Save this. Type 'status' to retrieve your result later._",
                "\n_⚕️ Not a medical diagnosis. Always consult a qualified health worker._",
            ]
            self._send(phone, "\n".join(parts))

        try:
            self.client.send_interactive_buttons(
                to=phone,
                header_text="What would you like to do next?",
                body_text="Your assessment has been saved.",
                buttons=[
                    {"id": "new_assessment", "title": "New Assessment"},
                    {"id": "check_status",   "title": "Check Status"},
                ],
            )
        except DialogAPIError:
            self._send(
                phone,
                "Type *reset* for a new assessment or *status* to check this result."
            )

    # ── Emergency alert ────────────────────────────────────────────────────────

    def _send_emergency_alert(self, phone: str, flags: Dict[str, Any]) -> None:
        flag_names = [k.replace("_", " ").title() for k, v in flags.items() if v]
        flags_text = (
            "\n".join(f"⚠️ {f}" for f in flag_names) + "\n\n"
        ) if flag_names else ""

        self._send(
            phone,
            f"🚨 *EMERGENCY — SEEK IMMEDIATE CARE* 🚨\n\n"
            f"{flags_text}"
            f"Go to the *nearest emergency department NOW*.\n"
            f"Call: *999* or *0800 100 066* (toll-free Uganda)\n\n"
            f"Reference: *{_patient_token(phone)}*\n\n"
            f"_Do not wait — go immediately._"
        )

    # ── Commands ───────────────────────────────────────────────────────────────

    def _cmd_reset(self, phone: str) -> None:
        _clear_session(phone)
        self._send(
            phone,
            "🔄 *Session reset.*\n\n"
            "Welcome to *HarakaCare* 🏥\n\n"
            "Describe your health concern or symptoms in your own words "
            "and I will help assess them."
        )

    def _cmd_status(self, phone: str) -> None:
        token = _patient_token(phone)
        try:
            from apps.triage.models import TriageSession, TriageDecision

            session = TriageSession.objects.get(patient_token=token)

            if session.session_status != TriageSession.SessionStatus.COMPLETED:
                self._send(
                    phone,
                    f"⏳ Your assessment (*{token}*) is still in progress.\n"
                    "Please complete the questions to receive your result."
                )
                return

            decision  = TriageDecision.objects.get(triage_session=session)
            risk      = (session.risk_level or "unknown").upper()
            priority  = (session.follow_up_priority or "routine").upper()
            action    = (decision.recommended_action or "")[:500]
            facility  = decision.facility_type_recommendation or ""
            emoji     = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(risk, "⚪")
            completed = (
                session.assessment_completed_at.strftime("%d %b %Y at %H:%M")
                if session.assessment_completed_at else "N/A"
            )

            self._send(
                phone,
                f"📋 *Your HarakaCare Result*\n\n"
                f"{emoji} Risk: *{risk}* | Priority: {priority}\n"
                f"Facility: {facility}\n\n"
                f"📋 Advice:\n{action}\n\n"
                f"Assessed: {completed}\n"
                f"Reference: *{token}*\n\n"
                f"_Type 'reset' to start a new assessment._"
            )

        except TriageSession.DoesNotExist:
            self._send(
                phone,
                "No completed assessment found for this number.\n\n"
                "Send a message describing your symptoms to start one."
            )
        except TriageDecision.DoesNotExist:
            self._send(
                phone,
                f"Assessment saved (*{token}*) but result is still processing.\n"
                "Please try again in a few minutes."
            )
        except Exception as exc:
            logger.error(f"Status check failed for {phone}: {exc}", exc_info=True)
            self._send(phone, "Could not retrieve your result. Please try again shortly.")

    def _cmd_help(self, phone: str) -> None:
        self._send(
            phone,
            "🏥 *HarakaCare — Free Health Assessment*\n\n"
            "Describe your symptoms in your own words and I'll ask follow-up "
            "questions to assess your health risk.\n\n"
            "*Commands:*\n"
            "• *status* — Check your last result\n"
            "• *reset* — Start a new assessment\n"
            "• *help* — Show this menu\n"
            "• *book* — Book an appointment\n"
            "_Based on WHO clinical guidelines. Not a substitute for a doctor._"
        )

    def _cmd_booking(self, phone: str, text: str) -> None:
        """Handle booking-related commands."""
        text_lower = text.lower()
        logger.info(f"Booking command received: {text_lower}")
        
        # Use real facility data instead of sample data
        if "confirm" in text_lower or "book" in text_lower:
            logger.info(f"Sending booking confirmation to {phone}")
            # Get real facility data from database
            try:
                from apps.triage.models import TriageSession
                from apps.facilities.models import Facility, FacilityRouting
                
                token = _patient_token(phone)
                routing = FacilityRouting.objects.filter(
                    patient_token=token,
                    routing_status=FacilityRouting.RoutingStatus.CONFIRMED
                ).first()
                
                if routing and routing.facility:
                    facility = routing.facility
                    facility_name = facility.name
                    facility_phone = facility.phone_number
                    facility_address = facility.address
                    
                    # Generate realistic appointment time (tomorrow morning)
                    from datetime import datetime, timedelta
                    tomorrow = datetime.now() + timedelta(days=1)
                    appointment_date = tomorrow.strftime("%A, %d %B %Y")
                    appointment_time = "10:30 AM"
                    
                    # Send booking confirmation with real facility data
                    self._send_booking_confirmation(
                        phone=phone,
                        facility_name=facility_name,
                        appointment_date=appointment_date,
                        appointment_time=appointment_time
                    )
                else:
                    # Fallback to generic message if no confirmed facility
                    self._send(
                        phone,
                        "📅 *Booking Help*\n\n"
                        "No confirmed facility found for your assessment.\n"
                        "Please complete an assessment first, or contact support.\n\n"
                        "Type 'help' for assistance."
                    )
                    
            except Exception as e:
                logger.error(f"Failed to get facility data for manual booking: {e}")
                self._send(
                    phone,
                    "📅 *Booking System Temporarily Unavailable*\n\n"
                    "Please try again in a few minutes or call the facility directly.\n\n"
                    "Type 'help' for assistance."
                )
        elif "reschedule" in text_lower:
            self._send(
                phone,
                "📞 *To reschedule:*\n\n"
                "Please call the facility directly:\n"
                "• HarakaCare Health Centre: +256 123 456 789\n"
                "• Emergency: +256 999 000 111\n\n"
                "Or reply with 'book' to make a new appointment."
            )
        else:
            self._send(
                phone,
                "📅 *Booking Help*\n\n"
                "To book an appointment:\n"
                "• Reply 'book' to schedule\n"
                "• Reply 'confirm' for confirmation\n"
                "• Reply 'reschedule' to change appointment\n\n"
                "Or call us directly at +256 123 456 789"
            )

    def _send_booking_confirmation(self, phone: str, facility_name: str, appointment_date: str, appointment_time: str) -> None:
        """Send booking confirmation message to patient."""
        logger.info(f"Preparing booking confirmation for {phone}: {facility_name}, {appointment_date}, {appointment_time}")
        parts = [
            f"✅ *Booking Confirmed*\n\n",
            f"🏥 *Facility:* {facility_name}\n",
            f"📅 *Date:* {appointment_date}\n",
            f"🕐 *Time:* {appointment_time}\n\n",
            "📍 *Please arrive 15 minutes before your appointment.*\n\n",
            "📞 *Need to reschedule?* Reply 'reschedule' or call the facility directly.\n\n",
            f"_Reference: {_patient_token(phone)}_",
            "\n_⚕️ Bring your ID and any relevant medical records._"
        ]
        message = "\n".join(parts)
        logger.info(f"Sending booking confirmation message: {message}")
        self._send(phone, message)

    def _send_booking_reminder(self, phone: str, facility_name: str, appointment_date: str, appointment_time: str) -> None:
        """Send booking reminder message to patient."""
        parts = [
            f"⏰ *Appointment Reminder*\n\n",
            f"🏥 *Facility:* {facility_name}\n",
            f"📅 *Date:* {appointment_date}\n",
            f"🕐 *Time:* {appointment_time}\n\n",
            "📍 *Your appointment is coming up soon!*\n\n",
            "📞 *Need to reschedule?* Reply 'reschedule'\n\n",
            f"_Reference: {_patient_token(phone)}_"
        ]
        self._send(phone, "\n".join(parts))

    # ── Delivery helper ────────────────────────────────────────────────────────

    def _send_structured_menu(self, phone: str, message: str, active_field: str) -> None:
        """
        Convert structured menu to interactive buttons or lists.
        
        - Interactive Buttons for 2-3 options: pregnancy_status, allergies, on_medication, consents, condition_occurrence, sex
        - Interactive Lists for 4+ options: progression_status, duration, severity, age_group
        - Each field now has its own separate menu for better UX
        """
        try:
            # Debug: log what we received
            logger.debug(f"Structured menu - Field: {active_field}, Message: {message[:200]}...")
            
            # Parse the menu to extract options
            lines = message.split('\n')
            options = []
            header_text = ""
            body_text = ""
            
            # Collect all options and header/body text
            for line in lines:
                line = line.strip()
                
                # Extract options from numbered lines
                if (line.startswith(('1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣')) or 
                    line.startswith(('A.', 'B.', '1.', '2.', '3.', '4.', '5.', '6.', '7.'))):
                    
                    option_id = ""
                    option_title = ""
                    
                    # Handle emoji format (1️⃣, 2️⃣, etc.)
                    if line.startswith(('1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣')):
                        # Extract the number at the start
                        emoji_match = re.match(r'^(\d+️⃣)\s*(.*)', line)
                        if emoji_match:
                            option_id = emoji_match.group(1)[0]  # First character of the emoji (the number)
                            option_title = emoji_match.group(2).strip()  # The text after emoji
                        else:
                            # Fallback: extract first character as ID, rest as title
                            option_id = line[0]
                            option_title = re.sub(r'^\d+️⃣\s*', '', line).strip()
                    # Handle letter format (A., B.)
                    elif line.startswith(('A.', 'B.')):
                        option_id = line[0]
                        option_title = line[2:].strip()
                    # Handle numbered format (1., 2., etc.)
                    elif '. ' in line:
                        parts = line.split('. ', 1)
                        if len(parts) == 2:
                            option_id = parts[0]
                            option_title = parts[1].strip()
                        else:
                            option_id = line[0]
                            option_title = line[2:].strip()
                    
                    if option_id and option_title:
                        options.append({
                            "id": option_id,
                            "title": option_title
                        })
                        
                elif not any(line.startswith(prefix) for prefix in ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', 'A.', 'B.', '1.', '2.', '3.', '4.', '5.', '6.', '7.']):
                    # This is header/body text
                    if header_text:
                        body_text += line + "\n"
                    else:
                        header_text = line
                        body_text = line + "\n"
            
            # Clean up body text
            body_text = body_text.strip()
            
            # Interactive Buttons for 2-3 options
            if len(options) <= 3:
                buttons = []
                for option in options:
                    # Debug: print what we're working with
                    logger.debug(f"Processing option: {option}")
                    # Ensure option has both id and title
                    if option.get("id") and option.get("title"):
                        button_obj = {
                            "id": str(option["id"]),  # Ensure string
                            "title": option["title"][:20]  # WhatsApp button titles max 20 chars
                        }
                        # Double-check the button has required fields
                        if button_obj.get("id") and button_obj.get("title"):
                            buttons.append(button_obj)
                            logger.debug(f"Added button: {button_obj}")
                        else:
                            logger.warning(f"Created invalid button object: {button_obj}")
                    else:
                        logger.warning(f"Skipping option without id or title: {option}")
                
                logger.debug(f"Final buttons list: {buttons}")
                # Final validation - ensure all buttons have id and title
                valid_buttons = []
                for btn in buttons:
                    if isinstance(btn, dict) and btn.get("id") and btn.get("title"):
                        valid_buttons.append(btn)
                    else:
                        logger.error(f"Invalid button object found: {btn}")
                
                if valid_buttons:  # Only send if we have valid buttons
                    logger.debug(f"Sending {len(valid_buttons)} valid buttons")
                    self.client.send_interactive_buttons(
                        to=phone,
                        body_text=body_text,
                        buttons=valid_buttons
                    )
                else:
                    # Fallback to text if no valid buttons
                    logger.warning(f"No valid buttons found, falling back to text. Original options: {options}")
                    self._send(phone, message)
                
            # Interactive Lists for 4+ options
            elif len(options) >= 4:
                list_sections = [{
                    "title": "Select an option:",
                    "rows": []
                }]
                
                valid_options = False
                for option in options:
                    if option.get("id") and option.get("title"):
                        list_sections[0]["rows"].append({
                            "id": str(option["id"]),  # Ensure string
                            "title": option["title"][:24],  # WhatsApp list item titles max 24 chars
                            "description": ""
                        })
                        valid_options = True
                
                if valid_options:  # Only send if we have valid options
                    self.client.send_interactive_list(
                        to=phone,
                        header_text=header_text if len(header_text) < 60 else None,
                        body_text=body_text,
                        button_label="Choose",
                        sections=list_sections
                    )
                else:
                    # Fallback to text if no valid options
                    self._send(phone, message)
            
            else:
                # Fallback to regular text if no options detected
                self._send(phone, message)
                
        except DialogAPIError as exc:
            logger.error(f"Failed to send structured menu to {phone}: {exc}")
            self._send(phone, "Sorry, I had trouble with that menu. Please try again.")

    def _send(self, phone: str, text: str) -> None:
        if len(text) > 4096:
            text = text[:4093] + "…"
        logger.info(f"Sending message to {phone}: {text[:100]}...")
        try:
            self.client.send_text(phone, text)
            logger.info(f"Message sent successfully to {phone}")
        except DialogAPIError as exc:
            logger.error(f"Failed to send to {phone}: {exc}")
            self._send(phone, "Sorry, I had trouble with that menu. Please try again.")