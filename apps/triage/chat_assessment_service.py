"""
Chat Assessment Service - Ada Health-inspired adaptive conversational triage.

Drives a deterministic, clinician-reviewed adaptive state machine over the existing
HarakaCare tools (NLP extraction, red-flag detection, safety engine, risk classification,
adaptive questioning, triage orchestrator). Persists conversation state in the
Conversation/Message models so assessments are isolated, resumable and auditable.

LLM (OpenAI) is used ONLY to interpret free-text and phrase approved questions.
It never invents clinical protocols; deterministic pathways have final authority.
"""
import uuid
import json
import logging
from typing import Dict, Any, List, Optional

from django.utils import timezone

from apps.conversations.models import Conversation, Message
from apps.triage.tools.adaptive_questioning import AdaptiveQuestioningTool
from apps.triage.tools.red_flag_detection import RedFlagDetectionTool
from apps.triage.clinical_safety_engine import safety_engine, SafetyLevel
from apps.triage.services.triage_orchestrator import TriageOrchestrator
from apps.triage.openai_nlp import openai_extractor
from apps.triage.openai_chat import chat_ai

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Deterministic keyword-based symptom extraction (works without OpenAI)
# ---------------------------------------------------------------------------
COMPLAINT_KEYWORDS = {
    "fever": ["fever", "hot", "temperature", "chills", "shivering"],
    "breathing": ["cough", "breathing", "breath", "wheeze", "wheezing", "shortness of breath", "chest tight"],
    "chest_pain": ["chest pain", "chest ache", "chest pressure", "heart pain"],
    "abdominal": ["stomach", "abdominal", "belly", "vomit", "diarrhea", "nausea", "tummy"],
    "headache": ["headache", "head ache", "migraine", "head pain"],
    "injury": ["injury", "wound", "cut", "burn", "fracture", "accident", "fall"],
    "bleeding": ["bleeding", "blood", "hemorrhage"],
    "pregnancy": ["pregnant", "pregnancy", "labour", "labor", "contraction"],
    "skin": ["rash", "skin", "itch", "blister", "swelling"],
    "feeding": ["feeding", "not eating", "weak", "weakness", "lethargic"],
    "mental_health": ["sad", "depressed", "anxious", "suicide", "self harm", "panic"],
}

DURATION_KEYWORDS = {
    "less_than_1_hour": ["just now", "minutes", "an hour", "less than an hour"],
    "1_6_hours": ["few hours", "2 hours", "3 hours", "4 hours", "5 hours", "6 hours"],
    "6_24_hours": ["today", "since morning", "since yesterday", "overnight", "last night"],
    "1_3_days": ["2 days", "3 days", "couple of days", "few days", "yesterday"],
    "4_7_days": ["4 days", "5 days", "6 days", "7 days", "a week"],
    "more_than_1_week": ["week", "weeks", "fortnight"],
    "more_than_1_month": ["month", "months"],
}

SEVERITY_KEYWORDS = {
    "very_severe": ["unbearable", "worst", "cannot move", "cannot function", "emergency"],
    "severe": ["severe", "very bad", "terrible", "extreme", "intense"],
    "moderate": ["moderate", "medium", "some difficulty", "uncomfortable"],
    "mild": ["mild", "slight", "little", "minor", "small"],
}

AGE_BANDS = [
    ("newborn", "Newborn (0-2 months)"),
    ("infant", "Infant (2-12 months)"),
    ("child_1_5", "Child (1-5 years)"),
    ("child_6_12", "Child (6-12 years)"),
    ("teen", "Teen (13-17 years)"),
    ("adult", "Adult (18-64 years)"),
    ("elderly", "Elderly (65+ years)"),
]

SEX_OPTIONS = [("male", "Male"), ("female", "Female"), ("other", "Other / Prefer not to say")]

CONSENT_TEXT = (
    "Before we continue, please note:\n"
    "- I am an AI assistant, NOT a doctor. I cannot diagnose diseases or prescribe medication.\n"
    "- Your symptom information may be processed by an AI service to help extract details.\n"
    "- For emergencies (severe chest pain, difficulty breathing, unconsciousness, severe bleeding), "
    "go to the nearest hospital immediately.\n\n"
    "Do you consent to proceed with this assessment?"
)

WELCOME_TEXT = (
    "🏥 Welcome to HarakaCare Medical Triage!\n\n"
    "I'm here to help you assess your health concerns in about 2-3 minutes.\n\n"
    "⚠️ I am an AI assistant, NOT a doctor. I cannot diagnose diseases or prescribe medicine. "
    "For emergencies, go to the nearest hospital immediately.\n\n"
    "Please describe your main symptoms or health issue to begin."
)


class ChatAssessmentService:
    def __init__(self):
        self.adaptive = AdaptiveQuestioningTool()
        self.red_flags = RedFlagDetectionTool()
        self.orchestrator = TriageOrchestrator()

    # ------------------------------------------------------------------ helpers
    def _get_or_create_conversation(self, conversation_id: Optional[str]) -> Conversation:
        if conversation_id:
            try:
                return Conversation.objects.get(patient_token=conversation_id)
            except Conversation.DoesNotExist:
                pass
        token = conversation_id or f"PT-{uuid.uuid4().hex[:8].upper()}"
        return Conversation.objects.create(patient_token=token, intent="triage", extracted_state={})

    @staticmethod
    def _state(conv: Conversation) -> Dict[str, Any]:
        return conv.extracted_state or {}

    @staticmethod
    def _save_state(conv: Conversation, state: Dict[str, Any]):
        conv.extracted_state = state
        conv.save(update_fields=["extracted_state", "updated_at"])

    @staticmethod
    def _add_message(conv: Conversation, role: str, content: str):
        turn = (conv.turn_number or 0) + 1
        Message.objects.create(conversation=conv, role=role, content=content, turn=turn)
        conv.turn_number = turn
        conv.save(update_fields=["turn_number", "updated_at"])

    @staticmethod
    def _progress(stage: str, state: Dict[str, Any]) -> int:
        pd = state.get("patient_data", {}) or {}
        if stage == "welcome":
            return 5
        if stage == "consent":
            return 10
        if stage == "symptoms":
            return 15
        if stage == "demographics":
            return 25
        if stage == "adaptive":
            indicators = pd.get("symptom_indicators", {}) or {}
            # rough: 40 + up to 40 based on number of indicators collected
            return min(80, 40 + len(indicators) * 8)
        if stage in ("risk", "completed"):
            return 100
        if stage == "emergency":
            return 100
        return 10

    def _build_response(self, conv, state, message, suggested=None, progress=None,
                        assessment=None, safety=None) -> Dict[str, Any]:
        return {
            "message": message,
            "stage": state.get("stage", "welcome"),
            "patient_data": state.get("patient_data", {}) or {},
            "conversation_id": conv.patient_token,
            "suggested_answers": suggested or [],
            "progress": progress if progress is not None else self._progress(state.get("stage", "welcome"), state),
            "assessment": assessment,
            "safety": safety,
            "needs_consent": not bool(state.get("consent_given", False)),
        }

    # ------------------------------------------------------------------ extraction
    def _detect_red_flags_text(self, text: str) -> Dict[str, bool]:
        # reuse the view's keyword map logic via RedFlagDetectionTool's complaint-text check
        # Build a minimal triage_data and call detect on a throwaway session-less path.
        lowered = (text or "").lower()
        red_flags = {key: False for key in [
            "airway_obstruction", "unable_to_drink", "severe_breathing_difficulty",
            "chest_indrawing", "fast_breathing", "severe_bleeding", "signs_of_shock",
            "unconscious", "convulsions", "confusion", "stroke_symptoms",
            "lethargic_floppy", "vomits_everything", "pregnancy_emergency", "severe_pain",
        ]}
        keyword_map = {
            "airway_obstruction": ["choking", "airway obstruction", "cannot breathe", "can't breathe", "cant breathe", "stridor", "unable to breathe", "cannot speak", "cannot swallow"],
            "unable_to_drink": ["unable to drink", "cannot drink", "cant drink", "cannot keep fluids", "not drinking", "will not drink"],
            "severe_breathing_difficulty": ["severe breathing", "difficulty breathing", "hard to breathe", "breathing difficulty", "gasping", "blue lips", "blue fingers", "blue toe", "respiratory distress", "not breathing", "stop breathing", "choking"],
            "chest_indrawing": ["chest indrawing"],
            "fast_breathing": ["fast breathing", "rapid breathing"],
            "severe_bleeding": ["severe bleeding", "heavy bleeding", "uncontrolled bleeding", "massive bleeding", "hemorrhage", "bleeding"],
            "signs_of_shock": ["shock", "pale", "cold extremities", "weak pulse", "shocky"],
            "unconscious": ["unconscious", "unresponsive", "not responding", "cannot wake", "cannot be woken", "not awake"],
            "convulsions": ["convulsion", "seizure", "seizures", "fitting"],
            "confusion": ["confusion", "disorientation", "altered mental"],
            "stroke_symptoms": ["stroke", "facial droop", "face droop", "arm weakness", "speech difficulty", "slurred speech", "sudden weakness", "facial weakness"],
            "lethargic_floppy": ["lethargic", "floppy"],
            "vomits_everything": ["vomits everything", "vomiting everything", "vomit everything", "cannot keep fluids", "unable to keep fluids", "cannot keep anything down"],
            "pregnancy_emergency": ["pregnancy emergency", "bleeding during pregnancy", "pregnancy bleeding", "pregnancy complication", "pregnancy hemorrhage"],
            "severe_pain": ["severe pain", "worst pain", "unbearable pain", "extreme pain", "severe abdominal pain", "worst ever"],
        }
        for key, kws in keyword_map.items():
            if any(kw in lowered for kw in kws):
                red_flags[key] = True
        return red_flags

    def _extract_symptoms_deterministic(self, text: str) -> Dict[str, Any]:
        lowered = (text or "").lower()
        complaint_group = "other"
        for group, kws in COMPLAINT_KEYWORDS.items():
            if any(kw in lowered for kw in kws):
                complaint_group = group
                break
        duration = None
        for dur, kws in DURATION_KEYWORDS.items():
            if any(kw in lowered for kw in kws):
                duration = dur
                break
        severity = None
        for sev, kws in SEVERITY_KEYWORDS.items():
            if any(kw in lowered for kw in kws):
                severity = sev
                break
        return {
            "complaint_group": complaint_group,
            "primary_symptom": text.strip()[:120],
            "duration": duration,
            "severity": severity or "moderate",
            "red_flags": [k for k, v in self._detect_red_flags_text(text).items() if v],
        }

    def _extract_symptoms(self, text: str, consent_given: bool) -> Dict[str, Any]:
        # Try OpenAI NLP if consented & available
        if consent_given and openai_extractor.enabled:
            try:
                res = openai_extractor.extract_symptoms(text, consent_given=True)
                if res and not res.get("error") and res.get("complaint_group"):
                    # merge deterministic red flags
                    rf = self._detect_red_flags_text(text)
                    res["red_flags"] = list(set((res.get("red_flags") or []) + [k for k, v in rf.items() if v]))
                    return res
            except Exception as e:
                logger.warning(f"OpenAI NLP failed, falling back to deterministic: {e}")
        # Deterministic fallback
        det = self._extract_symptoms_deterministic(text)
        det["source"] = "deterministic"
        return det

    def _run_safety(self, patient_data: Dict[str, Any], user_text: str) -> Dict[str, Any]:
        red_flags = self._detect_red_flags_text(user_text)
        # merge any red flags already in patient_data
        existing_rf = patient_data.get("red_flag_indicators") or {}
        if isinstance(existing_rf, dict):
            for k, v in existing_rf.items():
                if v:
                    red_flags[k] = True
        pd_rf = patient_data.get("red_flags")
        if isinstance(pd_rf, list):
            for k in pd_rf:
                if k in red_flags:
                    red_flags[k] = True
        triage_data = {
            "red_flag_indicators": red_flags,
            "age_group": patient_data.get("age_group") or "adult",
            "sex": patient_data.get("sex") or "other",
            "pregnancy_status": patient_data.get("pregnancy_status") or "",
            "has_chronic_conditions": bool(patient_data.get("has_chronic_conditions")),
            "on_medication": bool(patient_data.get("on_medication")),
            "symptom_severity": patient_data.get("symptom_severity") or "moderate",
            "complaint_group": patient_data.get("complaint_group"),
        }
        try:
            safety_result = safety_engine.evaluate(triage_data=triage_data, ml_risk_level=None, ml_confidence=None)
        except Exception as e:
            logger.error(f"Safety engine error: {e}")
            return {"safety_level": "safe", "requires_human_review": False, "reasoning": "Safety engine unavailable", "recommended_action": "Please seek medical care."}
        return {
            "safety_level": safety_result.safety_level.value if safety_result else "safe",
            "requires_human_review": bool(safety_result.requires_human_review) if safety_result else False,
            "reasoning": safety_result.reasoning if safety_result else "Safety engine unavailable",
            "recommended_action": safety_result.recommended_action if safety_result else "Please seek medical care.",
        }

    def _is_emergency_safety(self, safety: Dict[str, Any]) -> bool:
        return safety.get("safety_level") == "emergency"

    # ------------------------------------------------------------------ public
    def start(self) -> Dict[str, Any]:
        conv = self._get_or_create_conversation(None)
        state = {
            "stage": "consent",
            "patient_data": {},
            "asked_questions": [],
            "consent_given": False,
            "safety": None,
            "assessment": None,
            "case_reference": None,
            "complaint_text": "",
        }
        self._save_state(conv, state)
        msg = WELCOME_TEXT + "\\n\\n" + CONSENT_TEXT
        self._add_message(conv, "agent", msg)
        return self._build_response(conv, state, msg,
                                   suggested=["Yes, I consent", "No, I do not consent"],
                                   progress=10)

    def process(self, conversation_id: Optional[str], user_input: str) -> Dict[str, Any]:
        conv = self._get_or_create_conversation(conversation_id)
        state = self._state(conv)
        if not state:
            state = {
                "stage": "welcome", "patient_data": {}, "asked_questions": [],
                "consent_given": False, "safety": None, "assessment": None,
                "case_reference": None, "complaint_text": "",
            }
        if user_input and user_input.strip():
            self._add_message(conv, "patient", user_input)

        stage = state.get("stage", "welcome")
        patient_data = state.get("patient_data", {}) or {}
        text = (user_input or "").strip()

        # ---- welcome -> consent ----
        if stage == "welcome":
            state["stage"] = "consent"
            state["patient_data"] = patient_data
            self._save_state(conv, state)
            self._add_message(conv, "agent", CONSENT_TEXT)
            return self._build_response(conv, state, CONSENT_TEXT,
                                       suggested=["Yes, I consent", "No, I do not consent"],
                                       progress=10, safety=state.get("safety"))

        # ---- consent ----
        if stage == "consent":
            lowered = text.lower()
            if any(w in lowered for w in ["yes", "consent", "agree", "ok", "okay", "i consent"]):
                state["consent_given"] = True
                state["stage"] = "symptoms"
                self._save_state(conv, state)
                msg = "Thank you. Please describe your symptoms in your own words."
                self._add_message(conv, "agent", msg)
                return self._build_response(conv, state, msg,
                                           suggested=["I have a fever and headache", "I have been coughing for 4 days", "My stomach hurts since morning"],
                                           progress=15)
            else:
                state["stage"] = "consent"
                self._save_state(conv, state)
                msg = "I need your consent to proceed. " + CONSENT_TEXT
                self._add_message(conv, "agent", msg)
                return self._build_response(conv, state, msg,
                                           suggested=["Yes, I consent", "No, I do not consent"],
                                           progress=10)

        # ---- symptoms (initial complaint) ----
        if stage == "symptoms":
            if not text:
                msg = "Please describe your symptoms."
                self._add_message(conv, "agent", msg)
                return self._build_response(conv, state, msg, progress=15)
            # safety check on the complaint text
            safety = self._run_safety(patient_data, text)
            state["safety"] = safety
            if self._is_emergency_safety(safety):
                state["stage"] = "emergency"
                state["patient_data"] = patient_data
                self._save_state(conv, state)
                emerg_msg = (
                    "🚨 EMERGENCY: Danger signs detected. Seek immediate medical attention. "
                    "Do not wait - go to the nearest hospital or call emergency services immediately."
                )
                self._add_message(conv, "agent", emerg_msg)
                return self._build_response(conv, state, emerg_msg,
                                           suggested=[], progress=100, safety=safety)

            extracted = self._extract_symptoms(text, state.get("consent_given", False))
            # merge into patient_data
            patient_data["complaint_text"] = text
            if extracted.get("complaint_group"):
                patient_data["complaint_group"] = extracted["complaint_group"]
            if extracted.get("duration"):
                patient_data["symptom_duration"] = extracted["duration"]
            if extracted.get("severity"):
                patient_data["symptom_severity"] = extracted["severity"]
            if extracted.get("red_flags"):
                patient_data["red_flags"] = extracted["red_flags"]
                rfi = patient_data.get("red_flag_indicators") or {}
                for rf in extracted["red_flags"]:
                    rfi[rf] = True
                patient_data["red_flag_indicators"] = rfi
            patient_data.setdefault("symptom_indicators", {})
            # store secondary symptoms
            if extracted.get("secondary_symptoms"):
                patient_data["secondary_symptoms"] = extracted["secondary_symptoms"]

            # decide next: demographics if missing age/sex
            if not patient_data.get("age_group") or not patient_data.get("sex"):
                state["stage"] = "demographics"
            else:
                state["stage"] = "adaptive"
            state["patient_data"] = patient_data
            self._save_state(conv, state)

            # Build a friendly extraction confirmation
            cg = patient_data.get("complaint_group", "other")
            msg = (
                f"Thank you. I noted your symptoms ({cg.replace('_', ' ')}). "
                "To continue, I need a few details."
            )
            if state["stage"] == "demographics":
                msg = (
                    f"Thank you. I noted: {cg.replace('_', ' ')}.\n\n"
                    "To tailor the assessment, please tell me the patient's age group and sex."
                )
            self._add_message(conv, "agent", msg)
            suggested = []
            if state["stage"] == "demographics":
                suggested = [label for _, label in AGE_BANDS[:3]] + ["Adult (18-64 years)", "Male", "Female"]
            return self._build_response(conv, state, msg, suggested=suggested, progress=self._progress(state["stage"], state), safety=safety)

        # ---- demographics ----
        if stage == "demographics":
            # parse age group / sex from free text or suggested button
            lowered = text.lower()
            age_set = False
            for code, label in AGE_BANDS:
                if code in lowered or label.lower() in lowered:
                    patient_data["age_group"] = code
                    age_set = True
                    break
            # handle common phrasings
            if not age_set:
                if "newborn" in lowered or "baby" in lowered or "infant" in lowered:
                    patient_data["age_group"] = "infant"
                    age_set = True
                elif "child" in lowered:
                    patient_data["age_group"] = "child_1_5"
                    age_set = True
                elif "teen" in lowered or "adolescent" in lowered:
                    patient_data["age_group"] = "teen"
                    age_set = True
                elif "elderly" in lowered or "senior" in lowered or "old" in lowered:
                    patient_data["age_group"] = "elderly"
                    age_set = True
                elif "adult" in lowered:
                    patient_data["age_group"] = "adult"
                    age_set = True
            if "male" in lowered or "man" in lowered or "boy" in lowered:
                patient_data["sex"] = "male"
            elif "female" in lowered or "woman" in lowered or "girl" in lowered:
                patient_data["sex"] = "female"

            if patient_data.get("age_group") and patient_data.get("sex"):
                state["stage"] = "adaptive"
            else:
                state["stage"] = "demographics"
            state["patient_data"] = patient_data
            self._save_state(conv, state)

            if state["stage"] == "adaptive":
                msg = "Thank you. Now let me ask a few follow-up questions."
                self._add_message(conv, "agent", msg)
                # immediately ask first adaptive question
                return self._ask_adaptive(conv, state, msg_prefix=msg)
            else:
                missing = []
                if not patient_data.get("age_group"):
                    missing.append("age group")
                if not patient_data.get("sex"):
                    missing.append("sex")
                msg = "I still need: " + ", ".join(missing) + ". Please select or type."
                self._add_message(conv, "agent", msg)
                suggested = [label for _, label in AGE_BANDS] + ["Male", "Female", "Other / Prefer not to say"]
                return self._build_response(conv, state, msg, suggested=suggested, progress=25)

        # ---- adaptive questioning loop ----
        if stage == "adaptive":
            # record previous answer into symptom_indicators if an adaptive question was pending
            pending_q = state.get("pending_question")
            if pending_q and text:
                mapping = pending_q.get("mapping")
                indicators = patient_data.setdefault("symptom_indicators", {})
                qtype = pending_q.get("question_type", "open_ended")
                lowered = text.lower()
                if mapping:
                    if qtype in ("yes_no",):
                        if any(w in lowered for w in ["yes", "y", "true"]):
                            indicators[mapping] = True
                        elif any(w in lowered for w in ["no", "n", "false"]):
                            indicators[mapping] = False
                        else:
                            indicators[mapping] = None
                    else:
                        indicators[mapping] = text
                # also store severity/duration if mentioned
                for sev, kws in SEVERITY_KEYWORDS.items():
                    if any(kw in lowered for kw in kws):
                        patient_data["symptom_severity"] = sev
                for dur, kws in DURATION_KEYWORDS.items():
                    if any(kw in lowered for kw in kws):
                        patient_data["symptom_duration"] = dur
                state["pending_question"] = None
                state["asked_questions"] = state.get("asked_questions", []) + [pending_q.get("question")]

            # safety check on every turn
            safety = self._run_safety(patient_data, text if text else (patient_data.get("complaint_text") or ""))
            state["safety"] = safety
            if self._is_emergency_safety(safety):
                state["stage"] = "emergency"
                state["patient_data"] = patient_data
                self._save_state(conv, state)
                emerg_msg = (
                    "🚨 EMERGENCY: Danger signs detected. Seek immediate medical attention. "
                    "Do not wait - go to the nearest hospital or call emergency services immediately."
                )
                self._add_message(conv, "agent", emerg_msg)
                return self._build_response(conv, state, emerg_msg, suggested=[], progress=100, safety=safety)

            # ask next question
            return self._ask_adaptive(conv, state)

        # ---- completed / emergency / other: just echo guidance ----
        if stage in ("completed", "emergency"):
            msg = state.get("assessment", {}).get("recommended_next_steps") or "Assessment complete. Please follow the guidance above."
            self._add_message(conv, "agent", msg)
            return self._build_response(conv, state, msg, progress=100, assessment=state.get("assessment"), safety=state.get("safety"))

        # fallback
        msg = "I'm not sure how to proceed. Let's start over."
        state["stage"] = "welcome"
        self._save_state(conv, state)
        self._add_message(conv, "agent", msg)
        return self._build_response(conv, state, msg, progress=5)

    def _ask_adaptive(self, conv, state, msg_prefix: str = "") -> Dict[str, Any]:
        patient_data = state.get("patient_data", {}) or {}
        indicators = patient_data.get("symptom_indicators", {}) or {}
        complaint_group = patient_data.get("complaint_group") or "other"
        age_group = patient_data.get("age_group") or "adult"

        # safety check before asking
        safety = self._run_safety(patient_data, patient_data.get("complaint_text") or "")
        state["safety"] = safety
        if self._is_emergency_safety(safety):
            state["stage"] = "emergency"
            state["patient_data"] = patient_data
            self._save_state(conv, state)
            emerg_msg = (
                "🚨 EMERGENCY: Danger signs detected. Seek immediate medical attention. "
                "Do not wait - go to the nearest hospital or call emergency services immediately."
            )
            self._add_message(conv, "agent", emerg_msg)
            return self._build_response(conv, state, emerg_msg, suggested=[], progress=100, safety=safety)

        q = self.adaptive.get_next_question(complaint_group, age_group, indicators)
        if not q.get("has_question"):
            # complete the assessment
            return self._complete_assessment(conv, state)

        question = q["question"]
        state["pending_question"] = q
        state["stage"] = "adaptive"
        state["patient_data"] = patient_data
        self._save_state(conv, state)

        # suggested answers based on question type
        qtype = q.get("question_type", "open_ended")
        if qtype == "yes_no":
            suggested = ["Yes", "No", "Not sure"]
        elif qtype == "capability":
            suggested = ["Yes", "No", "With difficulty"]
        else:
            suggested = []

        full_msg = (msg_prefix + "\n\n" + question).strip() if msg_prefix else question
        self._add_message(conv, "agent", full_msg)
        return self._build_response(conv, state, full_msg, suggested=suggested,
                                   progress=self._progress("adaptive", state), safety=safety)

    def _complete_assessment(self, conv, state) -> Dict[str, Any]:
        patient_data = state.get("patient_data", {}) or {}
        # Build cleaned_data for orchestrator
        cleaned_data = {
            "complaint_text": patient_data.get("complaint_text", ""),
            "complaint_group": patient_data.get("complaint_group", "other"),
            "age_group": patient_data.get("age_group", "adult"),
            "sex": patient_data.get("sex", "other"),
            "symptom_severity": patient_data.get("symptom_severity", "moderate"),
            "symptom_duration": patient_data.get("symptom_duration", "1_3_days"),
            "progression_status": patient_data.get("progression_status", "staying_same"),
            "pregnancy_status": patient_data.get("pregnancy_status", "no"),
            "has_chronic_conditions": bool(patient_data.get("has_chronic_conditions", False)),
            "on_medication": bool(patient_data.get("on_medication", False)),
            "symptom_indicators": patient_data.get("symptom_indicators", {}) or {},
            "red_flag_indicators": patient_data.get("red_flag_indicators", {}) or {},
            "risk_modifiers": patient_data.get("risk_modifiers", {}) or {},
        }

        safety = state.get("safety") or self._run_safety(patient_data, patient_data.get("complaint_text", ""))
        state["safety"] = safety

        # Run orchestrator to create case + risk classification
        case_reference = None
        risk_level = "low"
        recommended_action = "Please visit your nearest health facility for assessment."
        red_flags_list = []
        try:
            result = self.orchestrator.run(conv.patient_token, cleaned_data, conversation_mode=True)
            if isinstance(result, dict):
                risk_level = result.get("risk_level", risk_level)
                recommended_action = result.get("recommended_action", recommended_action)
                red_flags_list = result.get("red_flags", []) or result.get("detected_flags", []) or []
                case_reference = result.get("patient_token") or conv.patient_token
        except Exception as e:
            logger.error(f"Orchestrator run failed during chat completion: {e}")

        if case_reference is None:
            case_reference = conv.patient_token

        # Build structured assessment summary
        assessment = {
            "case_reference": case_reference,
            "main_symptoms": patient_data.get("complaint_text", ""),
            "complaint_group": patient_data.get("complaint_group", "other"),
            "secondary_symptoms": patient_data.get("secondary_symptoms", []),
            "duration": patient_data.get("symptom_duration", "unknown"),
            "severity": patient_data.get("symptom_severity", "moderate"),
            "associated_symptoms": patient_data.get("secondary_symptoms", []),
            "important_findings": {
                "age_group": patient_data.get("age_group"),
                "sex": patient_data.get("sex"),
                "symptom_indicators": patient_data.get("symptom_indicators", {}),
                "warning_signs": red_flags_list,
                "missing_information": [],
            },
            "urgency": {
                "level": risk_level,
                "explanation": f"Urgency level '{risk_level}' assigned by the approved HarakaCare risk engine based on all collected information.",
            },
            "recommended_next_steps": recommended_action,
            "disclaimer": "This AI assessment is NOT a confirmed medical diagnosis and does not replace a qualified healthcare professional.",
        }

        state["stage"] = "completed"
        state["patient_data"] = patient_data
        state["assessment"] = assessment
        state["case_reference"] = case_reference
        self._save_state(conv, state)

        msg = (
            "✅ Assessment complete.\n\n"
            f"Case reference: {case_reference}\n"
            f"Urgency: {risk_level.upper()}\n\n"
            f"{recommended_action}\n\n"
            "⚠️ This is an AI assessment, NOT a medical diagnosis. "
            "Please consult a qualified healthcare worker."
        )
        self._add_message(conv, "agent", msg)
        return self._build_response(conv, state, msg, suggested=[], progress=100,
                                   assessment=assessment, safety=safety)

    def restart(self, conversation_id: Optional[str] = None) -> Dict[str, Any]:
        # mark old conversation completed/cancelled by creating a fresh one
        return self.start()


# Global instance
chat_assessment_service = ChatAssessmentService()

