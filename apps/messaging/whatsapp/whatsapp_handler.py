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
from typing import Any, Dict, Optional

from django.core.cache import cache

from apps.messaging.whatsapp.whatsapp_client import DialogClient, DialogAPIError
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
        self.client = DialogClient()
        self.agent  = ConversationalIntakeAgent()

    # ── Entry point ────────────────────────────────────────────────────────────

    def handle(self, phone: str, message_text: str, message_id: str) -> None:
        logger.info(f"WA | phone={phone} msg={message_text[:80]!r}")

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
            # Both answer_menu and answer_questions deliver the message verbatim.
            # The menu prompt is already formatted by MenuResolver; no extra processing needed.
            if message:
                self._send(phone, message)

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
            "• *help* — Show this menu\n\n"
            "_Based on WHO clinical guidelines. Not a substitute for a doctor._"
        )

    # ── Delivery helper ────────────────────────────────────────────────────────

    def _send(self, phone: str, text: str) -> None:
        if len(text) > 4096:
            text = text[:4093] + "…"
        try:
            self.client.send_text(phone, text)
        except DialogAPIError as exc:
            logger.error(f"Failed to send to {phone}: {exc}")