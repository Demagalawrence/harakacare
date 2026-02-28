from apps.messaging.utils import generate_patient_token
from apps.triage.tools.conversational_intake_agent import process_conversational_intake
from apps.triage.tools.intake_validation import IntakeValidationTool
from apps.triage.services.triage_orchestrator import TriageOrchestrator
from apps.messaging.models import SMSState


# ENTRY POINT
def route_incoming_message(phone, text, channel):

    patient_token = generate_patient_token(phone)

    if channel == "whatsapp":
        return handle_whatsapp(patient_token, text)

    if channel == "sms":
        return handle_sms(patient_token, text)


# ---------------- WHATSAPP (AI) ----------------

def handle_whatsapp(patient_token, text):

    result = process_conversational_intake(
        patient_token=patient_token,
        message=text,
        channel="whatsapp"
    )

    if result.get("status") == "complete":
        return finalize_triage(patient_token, result["structured_data"])

    return result.get("message", "Please continue.")


# ---------------- SMS MENU ENGINE ----------------

def handle_sms(patient_token, text):

    state, _ = SMSState.objects.get_or_create(patient_token=patient_token)

    # STEP 1
    if state.step == "start":
        state.step = "age"
        state.save()

        return (
            "Welcome to HarakaCare.\n"
            "Select age group:\n"
            "1. Child (0-12)\n"
            "2. Adult (13+)"
        )

    # STEP 2 AGE
    if state.step == "age":
        if text == "1":
            state.age_group = "child"
        elif text == "2":
            state.age_group = "adult"
        else:
            return "Reply with 1 or 2."

        state.step = "complaint"
        state.save()

        return (
            "Main symptom:\n"
            "1. Fever\n"
            "2. Cough\n"
            "3. Diarrhea"
        )

    # STEP 3 SYMPTOM
    if state.step == "complaint":
        mapping = {"1": "fever", "2": "cough", "3": "diarrhea"}
        if text not in mapping:
            return "Reply 1-3."

        state.complaint_group = mapping[text]
        state.step = "duration"
        state.save()

        return "How many days? (Enter number)"

    # STEP 4 DURATION
    if state.step == "duration":
        state.duration = text
        state.step = "complete"
        state.save()

        structured = {
            "complaint_group": state.complaint_group,
            "age_group": state.age_group,
            "symptom_duration": text,
        }

        return finalize_triage(patient_token, structured)


# ---------------- FINAL TRIAGE ----------------

def finalize_triage(patient_token, structured):

    validator = IntakeValidationTool()
    valid, cleaned, errors = validator.validate(structured)

    if not valid:
        return "Information incomplete. Please start again."

    session, decision, red_flags = TriageOrchestrator.run(
        patient_token,
        cleaned
    )

    if red_flags.get("has_red_flags"):
        return "🚨 EMERGENCY! Go to nearest hospital immediately."

    risk = session.risk_level

    if risk == "high":
        return "Please go to hospital immediately."
    elif risk == "medium":
        return "Visit a clinic today."
    else:
        return "Monitor at home. Seek care if worsening."