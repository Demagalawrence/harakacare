"""
USSD Request Handlers
Handles the full triage flow, saves results, and returns patient token.
Users can re-enter to check status with their token.
"""

import hashlib
import logging
from typing import Dict, Any

from apps.messaging.ussd.menus import (
    MENU_TEXTS, COMPLAINT_MAPPING, AGE_MAPPING, SEX_MAPPING,
    SEVERITY_MAPPING, DURATION_MAPPING, PREGNANCY_MAPPING,
    EMERGENCY_COMPLAINTS, EMERGENCY_SEVERITIES, USSDMenu
)
from apps.messaging.ussd.session import SessionManager
from apps.triage.tools.intake_validation import IntakeValidationTool
from apps.triage.services.triage_orchestrator import TriageOrchestrator

logger = logging.getLogger(__name__)


def generate_patient_token(phone: str) -> str:
    """
    Generate a deterministic patient token from phone number.
    Same phone always gets the same token — essential for status lookup.
    """
    phone = phone.replace("+", "").strip()
    return "PT-" + hashlib.sha256(phone.encode()).hexdigest()[:16].upper()


class USSDHandler:
    """Handles USSD requests — full triage flow with status check support."""

    def __init__(self):
        self.intake_tool = IntakeValidationTool()
        logger.info("USSDHandler initialised")

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def handle(self, session_id: str, phone_number: str, text: str) -> Dict[str, Any]:
        current_input = self._get_current_input(text)

        logger.info(
            f"USSD | session={session_id} phone={phone_number} "
            f"full_text='{text}' current='{current_input}'"
        )

        session = SessionManager.get_session(session_id, phone_number)

        menu = session.current_menu

        if menu == USSDMenu.WELCOME.value:
            return self._handle_welcome(session, current_input)
        elif menu == USSDMenu.LANGUAGE.value:
            return self._handle_language(session, current_input)
        elif menu == USSDMenu.MAIN_MENU.value:
            return self._handle_main_menu(session, current_input)

        # ------ Status-check branch ------
        elif menu == USSDMenu.STATUS_TOKEN_INPUT.value:
            return self._handle_status_token_input(session, current_input)

        # ------ New triage branch ------
        elif menu == USSDMenu.COMPLAINT_SELECTION.value:
            return self._handle_complaint(session, current_input)
        elif menu == USSDMenu.AGE_SELECTION.value:
            return self._handle_age(session, current_input)
        elif menu == USSDMenu.SEX_SELECTION.value:
            return self._handle_sex(session, current_input)
        elif menu == USSDMenu.SEVERITY_SELECTION.value:
            return self._handle_severity(session, current_input)
        elif menu == USSDMenu.DURATION_SELECTION.value:
            return self._handle_duration(session, current_input)
        elif menu == USSDMenu.LOCATION_INPUT.value:
            return self._handle_location(session, current_input)
        elif menu == USSDMenu.PREGNANCY_CHECK.value:
            return self._handle_pregnancy(session, current_input)
        elif menu == USSDMenu.CONSENT.value:
            return self._handle_consent(session, current_input)
        elif menu == USSDMenu.PROCESSING.value:
            return self._handle_processing(session)

        # ------ Terminal screens ------
        elif menu == USSDMenu.EMERGENCY.value:
            return self._ussd_response(
                MENU_TEXTS[USSDMenu.EMERGENCY][session.language], end=True
            )
        elif menu == USSDMenu.COMPLETE.value:
            return self._ussd_response("Thank you for using HarakaCare. Stay healthy!", end=True)

        return self._ussd_response("Invalid option. Please try again.", end=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_current_input(self, text: str) -> str:
        """Africa's Talking sends the full accumulated path (e.g. '1*2*1').
        We only need the last segment for the current step."""
        if not text:
            return ""
        return text.split("*")[-1]

    def _ussd_response(self, message: str, end: bool = False) -> Dict[str, Any]:
        return {"message": message, "action": "end" if end else "request"}

    # ------------------------------------------------------------------
    # Menu handlers — navigation
    # ------------------------------------------------------------------

    def _handle_welcome(self, session, text: str) -> Dict[str, Any]:
        """First request always has empty text. Show language menu."""
        session.current_menu = USSDMenu.LANGUAGE.value
        SessionManager.save_session(session)
        return self._ussd_response(MENU_TEXTS[USSDMenu.WELCOME][session.language])

    def _handle_language(self, session, text: str) -> Dict[str, Any]:
        if text == "1":
            session.language = "en"
        elif text == "2":
            session.language = "luganda"
        else:
            return self._ussd_response("Please select 1 (English) or 2 (Luganda).")

        session.current_menu = USSDMenu.MAIN_MENU.value
        SessionManager.save_session(session)
        return self._ussd_response(MENU_TEXTS[USSDMenu.MAIN_MENU][session.language])

    def _handle_main_menu(self, session, text: str) -> Dict[str, Any]:
        if text == "1":  # Start new triage
            session.current_menu = USSDMenu.COMPLAINT_SELECTION.value
            SessionManager.save_session(session)
            return self._ussd_response(MENU_TEXTS[USSDMenu.COMPLAINT_SELECTION][session.language])
        elif text == "2":  # Check previous result
            session.current_menu = USSDMenu.STATUS_TOKEN_INPUT.value
            SessionManager.save_session(session)
            return self._ussd_response(
                "Enter your patient token (e.g. PT-ABC123):\n"
                "Or enter 0 to use your phone number automatically."
            )
        elif text == "3":  # Help
            return self._ussd_response(
                "HarakaCare: Free symptom assessment.\n"
                "Select 1 to start. You will get a token to track your case.\n"
                "Press 0 to go back.",
                end=False
            )
        else:
            return self._ussd_response(MENU_TEXTS[USSDMenu.MAIN_MENU][session.language])

    # ------------------------------------------------------------------
    # Status-check flow
    # ------------------------------------------------------------------

    def _handle_status_token_input(self, session, text: str) -> Dict[str, Any]:
        """
        Let the user enter a token or press 0 to auto-derive it from their phone.
        Then fetch and display the triage result.
        """
        if text == "0":
            # Derive token from phone number (same algorithm used at submission)
            token = generate_patient_token(session.phone_number)
        elif text and len(text) >= 6:
            token = text.strip().upper()
            if not token.startswith("PT-"):
                token = "PT-" + token
        else:
            return self._ussd_response(
                "Invalid token. Enter your token or 0 to use your phone number."
            )

        result = self._fetch_triage_result(token)
        SessionManager.delete_session(session.session_id)
        return self._ussd_response(result, end=True)

    def _fetch_triage_result(self, token: str) -> str:
        """Return a formatted status string for the given token."""
        try:
            from apps.triage.models import TriageSession, TriageDecision

            session = TriageSession.objects.get(patient_token=token)

            if session.session_status != TriageSession.SessionStatus.COMPLETED:
                return (
                    f"Token: {token}\n"
                    f"Status: Assessment in progress.\n"
                    f"Please try again shortly."
                )

            decision = TriageDecision.objects.get(triage_session=session)

            risk = (session.risk_level or "unknown").upper()
            priority = (session.follow_up_priority or "").upper()
            action = (decision.recommended_action or "")[:120]
            facility = decision.facility_type_recommendation or ""
            completed = (
                session.assessment_completed_at.strftime("%d %b %Y %H:%M")
                if session.assessment_completed_at else "N/A"
            )

            return (
                f"HarakaCare Result\n"
                f"Token: {token}\n"
                f"Risk: {risk}\n"
                f"Priority: {priority}\n"
                f"Facility: {facility}\n"
                f"Advice: {action}\n"
                f"Assessed: {completed}"
            )

        except TriageSession.DoesNotExist:
            return (
                f"No record found for token:\n{token}\n"
                f"Please check and try again."
            )
        except TriageDecision.DoesNotExist:
            return (
                f"Token: {token}\n"
                f"Assessment saved but decision pending.\n"
                f"Please try again in a few minutes."
            )
        except Exception as e:
            logger.error(f"Error fetching triage result for {token}: {e}", exc_info=True)
            return "Unable to retrieve result. Please try later."

    # ------------------------------------------------------------------
    # Triage intake flow
    # ------------------------------------------------------------------

    def _handle_complaint(self, session, text: str) -> Dict[str, Any]:
        if text not in COMPLAINT_MAPPING:
            return self._ussd_response(
                MENU_TEXTS[USSDMenu.COMPLAINT_SELECTION][session.language]
            )

        complaint = COMPLAINT_MAPPING[text]
        session.data["complaint_group"] = complaint

        if complaint in EMERGENCY_COMPLAINTS:
            session.data["emergency_detected"] = True
            session.current_menu = USSDMenu.EMERGENCY.value
            SessionManager.save_session(session)
            return self._ussd_response(
                MENU_TEXTS[USSDMenu.EMERGENCY][session.language], end=True
            )

        session.current_menu = USSDMenu.AGE_SELECTION.value
        SessionManager.save_session(session)
        return self._ussd_response(MENU_TEXTS[USSDMenu.AGE_SELECTION][session.language])

    def _handle_age(self, session, text: str) -> Dict[str, Any]:
        if text not in AGE_MAPPING:
            return self._ussd_response(MENU_TEXTS[USSDMenu.AGE_SELECTION][session.language])

        session.data["age_group"] = AGE_MAPPING[text]
        session.current_menu = USSDMenu.SEX_SELECTION.value
        SessionManager.save_session(session)
        return self._ussd_response(MENU_TEXTS[USSDMenu.SEX_SELECTION][session.language])

    def _handle_sex(self, session, text: str) -> Dict[str, Any]:
        if text not in SEX_MAPPING:
            return self._ussd_response(MENU_TEXTS[USSDMenu.SEX_SELECTION][session.language])

        session.data["sex"] = SEX_MAPPING[text]
        session.current_menu = USSDMenu.SEVERITY_SELECTION.value
        SessionManager.save_session(session)
        return self._ussd_response(MENU_TEXTS[USSDMenu.SEVERITY_SELECTION][session.language])

    def _handle_severity(self, session, text: str) -> Dict[str, Any]:
        if text not in SEVERITY_MAPPING:
            return self._ussd_response(MENU_TEXTS[USSDMenu.SEVERITY_SELECTION][session.language])

        severity = SEVERITY_MAPPING[text]
        session.data["symptom_severity"] = severity

        if severity in EMERGENCY_SEVERITIES:
            session.data["emergency_detected"] = True
            session.current_menu = USSDMenu.EMERGENCY.value
            SessionManager.save_session(session)
            return self._ussd_response(
                MENU_TEXTS[USSDMenu.EMERGENCY][session.language], end=True
            )

        session.current_menu = USSDMenu.DURATION_SELECTION.value
        SessionManager.save_session(session)
        return self._ussd_response(MENU_TEXTS[USSDMenu.DURATION_SELECTION][session.language])

    def _handle_duration(self, session, text: str) -> Dict[str, Any]:
        if text not in DURATION_MAPPING:
            return self._ussd_response(MENU_TEXTS[USSDMenu.DURATION_SELECTION][session.language])

        session.data["symptom_duration"] = DURATION_MAPPING[text]
        session.current_menu = USSDMenu.LOCATION_INPUT.value
        SessionManager.save_session(session)
        return self._ussd_response(MENU_TEXTS[USSDMenu.LOCATION_INPUT][session.language])

    def _handle_location(self, session, text: str) -> Dict[str, Any]:
        if not text or len(text.strip()) < 2:
            return self._ussd_response("Please enter your district name (e.g. Kampala).")

        session.data["district"] = text.strip().title()

        # Only ask about pregnancy for females of childbearing age
        if (
            session.data.get("sex") == "female"
            and session.data.get("age_group") in ["teen", "adult"]
        ):
            session.current_menu = USSDMenu.PREGNANCY_CHECK.value
            SessionManager.save_session(session)
            return self._ussd_response(MENU_TEXTS[USSDMenu.PREGNANCY_CHECK][session.language])

        session.current_menu = USSDMenu.CONSENT.value
        SessionManager.save_session(session)
        return self._ussd_response(MENU_TEXTS[USSDMenu.CONSENT][session.language])

    def _handle_pregnancy(self, session, text: str) -> Dict[str, Any]:
        if text not in PREGNANCY_MAPPING:
            return self._ussd_response(MENU_TEXTS[USSDMenu.PREGNANCY_CHECK][session.language])

        session.data["pregnancy_status"] = PREGNANCY_MAPPING[text]

        # Pregnancy emergency: confirmed pregnant + bleeding or abdominal + at least moderate severity
        is_pregnant = text == "1"
        risky_complaint = session.data.get("complaint_group") in ["bleeding", "abdominal"]
        severe = session.data.get("symptom_severity") in ["severe", "very_severe"]

        if is_pregnant and risky_complaint and severe:
            session.data["emergency_detected"] = True
            session.current_menu = USSDMenu.EMERGENCY.value
            SessionManager.save_session(session)
            return self._ussd_response(
                MENU_TEXTS[USSDMenu.EMERGENCY][session.language], end=True
            )

        session.current_menu = USSDMenu.CONSENT.value
        SessionManager.save_session(session)
        return self._ussd_response(MENU_TEXTS[USSDMenu.CONSENT][session.language])

    def _handle_consent(self, session, text: str) -> Dict[str, Any]:
        if text == "1":
            session.data["consent_given"] = True
            # Save consent then run processing immediately —
            # do NOT return CON here or AT will stall waiting for user input.
            SessionManager.save_session(session)
            return self._handle_processing(session)
        else:
            SessionManager.delete_session(session.session_id)
            return self._ussd_response(
                "Triage cancelled. Thank you for using HarakaCare.", end=True
            )

    # ------------------------------------------------------------------
    # Processing — save to DB and return token
    # ------------------------------------------------------------------

    def _handle_processing(self, session) -> Dict[str, Any]:
        """
        Run the full triage pipeline, persist to database, and return the
        patient token and risk result to the user.
        """
        logger.info(f"Processing triage for phone: {session.phone_number}")

        # Deterministic token so the user can always retrieve their result
        patient_token = generate_patient_token(session.phone_number)
        session.data["patient_token"] = patient_token

        triage_data = {
            # Required core fields
            "complaint_group": session.data["complaint_group"],
            "age_group": session.data["age_group"],
            "sex": session.data["sex"],
            "district": session.data["district"],
            # Consent — user agreed to all three via the single USSD consent screen
            "consent_medical_triage": True,
            "consent_data_sharing": True,
            "consent_follow_up": True,
            # Symptom fields
            "symptom_severity": session.data.get("symptom_severity"),
            "symptom_duration": session.data.get("symptom_duration"),
            # Optional
            "pregnancy_status": session.data.get("pregnancy_status", "not_applicable"),
            "channel": "ussd",
            "patient_relation": "self",
            "conversation_turns": 1,
            # Initialise JSON fields (required by IntakeValidationTool)
            "symptom_indicators": {},
            "red_flag_indicators": {},
            "risk_modifiers": {},
        }

        try:
            # Step 1: Clinical validation
            is_valid, cleaned_data, errors = self.intake_tool.validate(triage_data)

            if not is_valid:
                logger.error(f"Intake validation failed for {patient_token}: {errors}")
                SessionManager.delete_session(session.session_id)
                return self._ussd_response(
                    "Validation error. Please dial again and check your inputs.", end=True
                )

            # Step 2: Run the full triage orchestrator — this saves everything to DB
            session_obj, final_decision, red_flag_result = TriageOrchestrator.run(
                patient_token, cleaned_data
            )

            logger.info(
                f"Triage complete | token={patient_token} "
                f"risk={session_obj.risk_level} "
                f"priority={session_obj.follow_up_priority}"
            )

            # Step 3: Build a concise USSD result message
            message = self._build_result_message(
                patient_token, session_obj, final_decision, red_flag_result
            )

            SessionManager.delete_session(session.session_id)
            return self._ussd_response(message, end=True)

        except Exception as e:
            logger.error(
                f"Triage processing failed for {patient_token}: {e}", exc_info=True
            )
            SessionManager.delete_session(session.session_id)
            return self._ussd_response(
                "System error. Your data was NOT saved.\n"
                "Please dial again to retry.",
                end=True
            )

    # ------------------------------------------------------------------
    # Result formatting
    # ------------------------------------------------------------------

    def _build_result_message(
        self, patient_token: str, session_obj, final_decision: dict, red_flag_result: dict
    ) -> str:
        """
        Build the END message shown to the user after triage completes.

        USSD messages are typically capped at ~182 characters per screen,
        so we keep this tight and put the token prominently first.
        """
        risk = (session_obj.risk_level or "unknown").upper()
        priority = (session_obj.follow_up_priority or "routine").upper()
        action = (final_decision.get("recommended_action") or "")[:100]
        facility = final_decision.get("facility_type") or ""
        has_red_flags = red_flag_result.get("has_red_flags", False)

        emergency_line = "⚠️ DANGER SIGNS DETECTED\n" if has_red_flags else ""

        return (
            f"HarakaCare Result\n"
            f"{emergency_line}"
            f"Risk: {risk} | Priority: {priority}\n"
            f"Go to: {facility}\n"
            f"{action}\n\n"
            f"Save your token to check status later:\n"
            f"{patient_token}\n"
            f"Dial again > Option 2 to check status."
        )