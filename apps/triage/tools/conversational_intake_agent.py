"""
HarakaCare Conversational Intake Agent — Hybrid State-Machine Edition
======================================================================
Architecture: Deterministic state machine for critical clinical fields,
LLM for free-text symptom extraction and empathetic language generation.

KEY CHANGES vs previous version:
- last_question_field tracking: every structured question records which field
  it is capturing so numeric/short answers are bound deterministically.
- Structured menus for: progression_status, duration, severity,
  pregnancy_status, condition_occurrence, allergies, on_medication,
  chronic_conditions (yes/no gate), consents.
- LLM is NEVER used to interpret menu responses.
- Pregnancy auto-added to missing_fields for female teen/adult patients.
- Pregnancy escalates severity when clinical triggers present.
- Fields removed from missing_fields immediately on capture.
- asked_fields_history prevents re-asking captured fields.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from django.core.cache import cache

from apps.triage.ml_models import APISymptomExtractor, generate_followup_questions
from apps.conversations.models import Conversation, Message

logger = logging.getLogger(__name__)


# ============================================================================
# CONSTANTS
# ============================================================================

ALL_REQUIRED_FIELDS = [
    "age_group", "sex", "district", "complaint_group",
    "symptom_severity", "symptom_duration", "progression_status",
    "consent_medical_triage", "consent_data_sharing", "consent_follow_up",
]

CONVERSATIONAL_REQUIRED = [
    "age_group",
    "sex",
    "complaint_group",
    "severity",
    "duration",
    "progression_status",
    "condition_occurrence",
    "allergies",
    "chronic_conditions",
    "location",
    "village",
    "on_medication",
    "consents",
]

EMERGENCY_REQUIRED = ["age_group", "complaint_group", "severity"]

HIGH_RISK_AGE_GROUPS = ["newborn", "infant", "elderly"]

UGANDAN_DISTRICTS = [
    "kampala", "wakiso", "mukono", "jinja", "mbarara",
    "gulu", "lira", "mbale", "arua", "kasese", "masaka",
    "hoima", "fort portal", "kabale", "soroti", "tororo",
    "iganga", "entebbe", "mityana", "mubende",
]

_CONDITION_OCCURRENCE_PRIORITY = {"long_term": 2, "happened_before": 1, "first": 0}
_ALLERGY_STATUS_PRIORITY        = {"yes": 2, "not_sure": 1, "no": 0}

# ── Structured menu definitions ───────────────────────────────────────────────
# Each entry: field_name → {prompt, options: {user_input → stored_value}}
STRUCTURED_MENUS: Dict[str, Dict] = {
    "progression_status": {
        "prompt": (
            "How are the symptoms changing?\n"
            "1️⃣ Getting worse\n"
            "2️⃣ Staying the same\n"
            "3️⃣ Getting better\n"
            "4️⃣ Comes and goes\n"
            "Reply with 1, 2, 3, or 4."
        ),
        "options": {
            "1": "getting_worse", "getting worse": "getting_worse", "worse": "getting_worse",
            "2": "staying_same",  "staying same": "staying_same",  "same": "staying_same",
            "3": "getting_better","getting better": "getting_better","better": "getting_better",
            "4": "comes_and_goes","comes and goes": "comes_and_goes","on and off": "comes_and_goes",
        },
    },
    "duration": {
        "prompt": (
            "How long have these symptoms lasted?\n"
            "1️⃣ Less than 1 day\n"
            "2️⃣ 1–3 days\n"
            "3️⃣ 4–7 days\n"
            "4️⃣ More than 1 week\n"
            "5️⃣ More than 1 month\n"
            "Reply with 1, 2, 3, 4, or 5."
        ),
        "options": {
            "1": "6_24_hours",        "less than 1 day": "6_24_hours",   "today": "6_24_hours",
            "2": "1_3_days",          "1-3 days": "1_3_days",            "1 to 3 days": "1_3_days",
            "3": "4_7_days",          "4-7 days": "4_7_days",            "4 to 7 days": "4_7_days",
            "4": "more_than_1_week",  "more than a week": "more_than_1_week", "over a week": "more_than_1_week",
            "5": "more_than_1_month", "more than a month": "more_than_1_month","chronic": "more_than_1_month",
        },
    },
    "severity": {
        "prompt": (
            "How severe are the symptoms?\n"
            "1️⃣ Mild — can do normal activities\n"
            "2️⃣ Moderate — some difficulty with normal activities\n"
            "3️⃣ Severe — cannot do normal activities\n"
            "4️⃣ Very severe — unable to move or respond normally\n"
            "Reply with 1, 2, 3, or 4."
        ),
        "options": {
            "1": "mild",        "mild": "mild",        "light": "mild",
            "2": "moderate",    "moderate": "moderate","medium": "moderate",
            "3": "severe",      "severe": "severe",    "bad": "severe",
            "4": "very_severe", "very severe": "very_severe","very bad": "very_severe","critical": "very_severe",
        },
    },
    "pregnancy_status": {
        "prompt": (
            "Is the patient currently pregnant?\n"
            "1️⃣ Yes\n"
            "2️⃣ No\n"
            "3️⃣ Not sure\n"
            "Reply with 1, 2, or 3."
        ),
        "options": {
            "1": "yes",      "yes": "yes",      "pregnant": "yes",
            "2": "no",       "no": "no",        "not pregnant": "no",
            "3": "not_sure", "not sure": "not_sure", "unsure": "not_sure", "maybe": "not_sure",
        },
    },
    "condition_occurrence": {
        "prompt": (
            "Is this the first time experiencing this, or has it happened before?\n"
            "1️⃣ First time\n"
            "2️⃣ Has happened before\n"
            "3️⃣ Long-term / ongoing condition\n"
            "Reply with 1, 2, or 3."
        ),
        "options": {
            "1": "first",           "first time": "first",        "never before": "first",
            "2": "happened_before", "before": "happened_before",  "again": "happened_before","recurring": "happened_before",
            "3": "long_term",       "long term": "long_term",     "chronic": "long_term","ongoing": "long_term",
        },
    },
    "allergies": {
        "prompt": (
            "Does the patient have any known allergies?\n"
            "1️⃣ Yes\n"
            "2️⃣ No\n"
            "3️⃣ Not sure\n"
            "Reply with 1, 2, or 3."
        ),
        "options": {
            "1": "yes",      "yes": "yes",      "allergic": "yes",
            "2": "no",       "no": "no",        "none": "no",   "no allergies": "no",
            "3": "not_sure", "not sure": "not_sure","unsure": "not_sure",
        },
    },
    "on_medication": {
        "prompt": (
            "Is the patient currently taking any medication?\n"
            "1️⃣ Yes\n"
            "2️⃣ No\n"
            "Reply with 1 or 2."
        ),
        "options": {
            "1": True,  "yes": True,  "taking medication": True,  "on medication": True,
            "2": False, "no": False,  "no medication": False,     "not taking": False,
        },
    },
    "chronic_conditions_gate": {
        "prompt": (
            "Does the patient have any long-term health conditions? (e.g. diabetes, hypertension, asthma)\n"
            "1️⃣ Yes — please describe\n"
            "2️⃣ No\n"
            "Reply with 1 or 2, then list any conditions."
        ),
        "options": {
            "1": True,  "yes": True,
            "2": False, "no": False, "none": False,
        },
    },
    "consents": {
        "prompt": (
            "Do you agree to:\n"
            "• Medical triage assessment\n"
            "• Anonymous data sharing for health records\n"
            "• Follow-up contact if needed\n\n"
            "1️⃣ Yes, I agree\n"
            "2️⃣ No\n"
            "Reply with 1 or 2."
        ),
        "options": {
            "1": True,  "yes": True,  "agree": True, "i agree": True, "okay": True, "ok": True,
            "2": False, "no": False,
        },
    },
}

# Fields that use structured menus (deterministic capture)
STRUCTURED_FIELDS: Set[str] = {
    "progression_status", "duration", "severity",
    "pregnancy_status", "condition_occurrence", "allergies",
    "on_medication", "consents",
}

# Pregnancy escalation triggers
PREGNANCY_ESCALATION_COMPLAINTS = {"abdominal", "bleeding", "fever", "chest_pain"}


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class ExtractedSymptom:
    symptom: str
    confidence: float
    source_text: str


@dataclass
class ExtractedInfo:
    complaint_text: str = ""
    complaint_group: Optional[str] = None

    age_group: Optional[str] = None
    sex: Optional[str] = None
    patient_relation: Optional[str] = "self"

    primary_symptom: Optional[str] = None
    secondary_symptoms: List[str] = field(default_factory=list)
    symptom_indicators: Dict[str, bool] = field(default_factory=dict)
    severity: Optional[str] = None
    duration: Optional[str] = None
    progression_status: Optional[str] = None

    condition_occurrence: Optional[str] = None
    allergies_status: Optional[str] = None
    allergy_types: List[str] = field(default_factory=list)
    chronic_conditions: List[str] = field(default_factory=list)

    red_flag_indicators: Dict[str, bool] = field(default_factory=dict)
    risk_modifiers: Dict[str, Any] = field(default_factory=dict)

    location: Optional[str] = None
    village: Optional[str] = None
    district: Optional[str] = None
    subcounty: Optional[str] = None

    pregnancy_status: Optional[str] = None
    has_chronic_conditions: bool = False
    on_medication: Optional[bool] = None

    consents_given: bool = False

    complaint_group_confidence: float = 0.0
    severity_confidence: float = 0.0
    duration_confidence: float = 0.0
    age_group_confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConversationState:
    patient_token: str
    turn_number: int
    extracted_info: ExtractedInfo
    missing_fields: List[str]
    conversation_history: List[Dict[str, str]]
    intent: str = "routine"
    completed: bool = False
    red_flags_detected: bool = False
    red_flag_detected_at_turn: Optional[int] = None
    # ── State machine tracking ─────────────────────────────────────────────
    last_question_field: Optional[str] = None      # Field the last menu was asking about
    asked_fields_history: List[str] = field(default_factory=list)  # All fields ever asked

    def to_dict(self) -> Dict:
        return {**asdict(self), "intent": self.intent}

    @classmethod
    def from_dict(cls, data: Dict) -> "ConversationState":
        data = data.copy()
        data["extracted_info"] = ExtractedInfo(**data["extracted_info"])
        if "asked_fields_history" not in data:
            data["asked_fields_history"] = []
        if "last_question_field" not in data:
            data["last_question_field"] = None
        return cls(**data)


# ============================================================================
# STRUCTURED MENU RESOLVER
# ============================================================================

class MenuResolver:
    """
    Deterministically interprets user responses to structured menu questions.
    Never uses LLM inference.
    """

    @staticmethod
    def resolve(field: str, user_text: str) -> Tuple[bool, Any]:
        """
        Try to resolve a menu response deterministically.
        Returns (matched: bool, value: Any)
        """
        menu = STRUCTURED_MENUS.get(field) or STRUCTURED_MENUS.get(field + "_gate")
        if not menu:
            return False, None

        t = user_text.strip().lower()
        options = menu["options"]

        # Exact match first
        if t in options:
            return True, options[t]

        # Check if response is just a number matching a menu option
        if re.match(r"^\d+$", t) and t in options:
            return True, options[t]

        # Partial match for longer responses
        for key, value in options.items():
            if len(key) > 1 and key in t:
                return True, value

        return False, None

    @staticmethod
    def get_prompt(field: str) -> Optional[str]:
        menu = STRUCTURED_MENUS.get(field) or STRUCTURED_MENUS.get(field + "_gate")
        return menu["prompt"] if menu else None


# ============================================================================
# PREGNANCY RISK ESCALATOR
# ============================================================================

class PregnancyRiskEscalator:
    """Applies clinical risk escalation when pregnancy is confirmed."""

    @staticmethod
    def should_escalate(info: ExtractedInfo) -> bool:
        if info.pregnancy_status != "yes":
            return False
        triggers = (
            info.complaint_group in PREGNANCY_ESCALATION_COMPLAINTS
            or info.severity in ("severe", "very_severe")
            or bool(info.red_flag_indicators)
        )
        return triggers

    @staticmethod
    def escalate(info: ExtractedInfo) -> None:
        """Mutates info in place to add pregnancy risk modifier and escalate severity."""
        info.risk_modifiers["pregnancy_risk"] = True

        severity_ladder = ["mild", "moderate", "severe", "very_severe"]
        if info.severity in severity_ladder:
            idx = severity_ladder.index(info.severity)
            # Escalate one step up if not already at max
            if idx < len(severity_ladder) - 1:
                info.severity = severity_ladder[idx + 1]

        # Add red flag for obstetric cases
        if info.complaint_group in ("bleeding", "abdominal"):
            info.red_flag_indicators["pregnancy_emergency"] = True


# ============================================================================
# CONVERSATIONAL INTAKE AGENT
# ============================================================================

class ConversationalIntakeAgent:

    def __init__(self):
        self.extractor = APISymptomExtractor()
        self.menu_resolver = MenuResolver()
        logger.info("✓ ConversationalIntakeAgent initialised (hybrid state-machine)")

    # ── Public entry points ────────────────────────────────────────────────────

    def start_conversation(self, token: str, message: str) -> Dict[str, Any]:
        print(f"\n🆕 NEW CONVERSATION: {token}")
        print(f"   Message: {message[:50]}...")

        info   = self._extract(message)
        intent = self._detect_intent(info, message)

        red_flags = self._check_red_flags(info, message)
        if red_flags:
            info.red_flag_indicators.update(red_flags)

        # Apply pregnancy escalation if applicable
        if PregnancyRiskEscalator.should_escalate(info):
            PregnancyRiskEscalator.escalate(info)

        missing = self._missing(info, intent)

        state = ConversationState(
            patient_token=token,
            turn_number=1,
            extracted_info=info,
            missing_fields=missing,
            conversation_history=[{"role": "patient", "content": message, "turn": 1}],
            intent=intent,
            completed=len(missing) == 0,
            red_flags_detected=bool(info.red_flag_indicators),
            red_flag_detected_at_turn=1 if info.red_flag_indicators else None,
            last_question_field=None,
            asked_fields_history=[],
        )

        self._save(state)
        print(f"   Intent: {intent} | Missing: {missing} | Red flags: {state.red_flags_detected}")

        if state.completed or state.red_flags_detected:
            return self._build_complete(state)
        return self._build_question(state)

    def continue_conversation(self, token: str, message: str) -> Dict[str, Any]:
        print(f"\n🔄 CONTINUE: {token}")
        print(f"   Message: {message[:50]}...")

        state = self._load(token)
        if not state:
            return self.start_conversation(token, message)

        state.turn_number += 1
        state.conversation_history.append(
            {"role": "patient", "content": message, "turn": state.turn_number}
        )

        # ── 1. Try deterministic menu resolution first ─────────────────────
        if state.last_question_field:
            resolved, value = self.menu_resolver.resolve(state.last_question_field, message)
            if resolved:
                print(f"   ✅ Menu resolved: {state.last_question_field} = {value!r}")
                self._apply_structured_value(state, state.last_question_field, value)
                state.last_question_field = None
            else:
                print(f"   ⚠️ Menu not resolved for {state.last_question_field}, trying NLP")
                # Fall through to NLP extraction — user may have given a description
                new = self._extract(message)
                self._merge(state.extracted_info, new)
        else:
            # No active menu — use full NLP extraction
            new = self._extract(message)
            self._merge(state.extracted_info, new)

        # ── 2. Re-check red flags ──────────────────────────────────────────
        new_red_flags = self._check_red_flags(state.extracted_info, message)
        if new_red_flags:
            state.extracted_info.red_flag_indicators.update(new_red_flags)
            if not state.red_flags_detected:
                state.red_flags_detected = True
                state.red_flag_detected_at_turn = state.turn_number

        # ── 3. Pregnancy escalation check ──────────────────────────────────
        if PregnancyRiskEscalator.should_escalate(state.extracted_info):
            PregnancyRiskEscalator.escalate(state.extracted_info)
            if not state.red_flags_detected and state.extracted_info.red_flag_indicators:
                state.red_flags_detected = True
                state.red_flag_detected_at_turn = state.turn_number

        # ── 4. Update intent and missing fields ────────────────────────────
        state.intent         = self._detect_intent(state.extracted_info, message)
        state.missing_fields = self._missing(state.extracted_info, state.intent)
        state.completed = (
            len(state.missing_fields) == 0
            or state.red_flags_detected
            or self._has_sufficient_info(state.extracted_info)
        )

        print(f"   Intent: {state.intent} | Missing: {state.missing_fields} | Done: {state.completed}")

        self._save(state)

        if state.completed:
            return self._build_complete(state)
        return self._build_question(state)

    # ── Structured value application ───────────────────────────────────────────

    def _apply_structured_value(self, state: ConversationState, field: str, value: Any) -> None:
        """Apply a deterministically-resolved menu value to extracted_info and update tracking."""
        info = state.extracted_info

        if field == "progression_status":
            info.progression_status = value
        elif field == "duration":
            info.duration = value
            info.duration_confidence = 1.0
        elif field == "severity":
            info.severity = value
            info.severity_confidence = 1.0
        elif field == "pregnancy_status":
            info.pregnancy_status = value
        elif field == "condition_occurrence":
            info.condition_occurrence = value
        elif field == "allergies":
            info.allergies_status = value
        elif field == "on_medication":
            info.on_medication = value
        elif field == "consents":
            info.consents_given = value
        elif field == "chronic_conditions_gate":
            if value is False:
                info.has_chronic_conditions = False
                info.chronic_conditions = []

        # Remove from missing_fields immediately
        field_aliases = {
            "chronic_conditions_gate": "chronic_conditions",
        }
        resolved_field = field_aliases.get(field, field)

        if resolved_field in state.missing_fields:
            state.missing_fields.remove(resolved_field)

        # Add to asked history so it's never asked again
        if resolved_field not in state.asked_fields_history:
            state.asked_fields_history.append(resolved_field)

    # ── Database persistence ───────────────────────────────────────────────────

    def _save(self, state: ConversationState):
        try:
            extra = {
                "last_question_field":  state.last_question_field,
                "asked_fields_history": state.asked_fields_history,
            }
            conversation, created = Conversation.objects.get_or_create(
                patient_token=state.patient_token,
                defaults={
                    "turn_number":     state.turn_number,
                    "intent":          state.intent,
                    "completed":       state.completed,
                    "extracted_state": {**state.extracted_info.to_dict(), **extra},
                },
            )
            if not created:
                conversation.turn_number     = state.turn_number
                conversation.intent          = state.intent
                conversation.completed       = state.completed
                conversation.extracted_state = {**state.extracted_info.to_dict(), **extra}
                conversation.save()

            if state.conversation_history:
                last = state.conversation_history[-1]
                exists = Message.objects.filter(
                    conversation=conversation,
                    turn=last.get("turn", state.turn_number),
                    role=last.get("role", "patient"),
                ).exists()
                if not exists:
                    Message.objects.create(
                        conversation=conversation,
                        role=last.get("role", "patient"),
                        content=last.get("content", ""),
                        turn=last.get("turn", state.turn_number),
                    )
            print(f"   💾 Saved turn {state.turn_number}")
        except Exception as e:
            logger.error(f"Error saving conversation state: {e}")

    def _load(self, token: str) -> Optional[ConversationState]:
        try:
            conversation = Conversation.objects.get(patient_token=token)
            messages = conversation.messages.all().order_by("turn")
            history  = [{"role": m.role, "content": m.content, "turn": m.turn} for m in messages]
            es       = conversation.extracted_state or {}

            # Extract state-machine tracking fields before passing to ExtractedInfo
            last_question_field  = es.pop("last_question_field", None)
            asked_fields_history = es.pop("asked_fields_history", [])

            valid_fields = {f.name for f in ExtractedInfo.__dataclass_fields__.values()}
            filtered     = {k: v for k, v in es.items() if k in valid_fields}
            info         = ExtractedInfo(**filtered)

            return ConversationState(
                patient_token=conversation.patient_token,
                turn_number=conversation.turn_number,
                extracted_info=info,
                missing_fields=self._missing(info, conversation.intent),
                conversation_history=history,
                intent=conversation.intent,
                completed=conversation.completed,
                red_flags_detected=bool(info.red_flag_indicators),
                red_flag_detected_at_turn=None,
                last_question_field=last_question_field,
                asked_fields_history=asked_fields_history,
            )
        except Conversation.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error loading conversation: {e}")
            return None

    # ── Extraction ─────────────────────────────────────────────────────────────

    def _extract(self, text: str) -> ExtractedInfo:
        """LLM-backed extraction for free-text fields only."""
        api  = self.extractor.extract(text)
        syms = self.extractor.extract_symptoms(text)

        info = ExtractedInfo(complaint_text=text)

        # Complaint group — LLM + regex
        info.complaint_group, info.complaint_group_confidence = self._extract_complaint_group(text, api)

        # Symptom indicators
        for s in syms[:5]:
            key = self._symptom_to_indicator(s.symptom)
            if key:
                info.symptom_indicators[key] = True

        # Severity — LLM only, deterministic capture via menu supercedes this
        info.severity, info.severity_confidence = self._extract_severity(text, api)

        # Duration — LLM only, deterministic capture via menu supercedes this
        info.duration, info.duration_confidence = self._extract_duration(text, api)

        # Progression — LLM only, deterministic menu supercedes
        info.progression_status = self._extract_progression(text)

        # Demographics
        info.age_group, info.age_group_confidence = self._extract_age_group(text)
        info.sex               = self._extract_sex(text)
        info.patient_relation  = self._extract_patient_relation(text)

        # Pregnancy — LLM extraction; deterministic menu supercedes when explicitly asked
        info.pregnancy_status  = self._extract_pregnancy_status(text)

        # Location
        info.location, info.district, info.subcounty, info.village = self._extract_location(text)

        # Chronic conditions
        info.chronic_conditions, info.has_chronic_conditions = self._extract_chronic_conditions(text)
        if info.chronic_conditions:
            info.risk_modifiers["chronic_conditions"] = info.chronic_conditions

        # Medication — deterministic menu supercedes
        info.on_medication = self._extract_medication_status(text)

        # Consent
        info.consents_given = self._extract_consent(text)

        # Condition occurrence — deterministic menu supercedes
        info.condition_occurrence = self._extract_condition_occurrence(text)

        # Allergies — deterministic menu supercedes
        info.allergies_status, info.allergy_types = self._extract_allergies(text)

        if syms:
            info.primary_symptom    = syms[0].symptom
            info.secondary_symptoms = [s.symptom for s in syms[1:4]]

        return info

    # ── Individual extractors (regex + LLM passthrough) ───────────────────────

    def _extract_complaint_group(self, text: str, api: Dict) -> Tuple[Optional[str], float]:
        t = text.lower()
        complaint_patterns = {
            "fever":        [r"\b(fever|hot|temperature|omusujja)\b"],
            "breathing":    [r"\b(breath|cough|wheezing|asthma|pneumonia)\b"],
            "injury":       [r"\b(injur|accident|fell|broken|wound|cut)\b"],
            "abdominal":    [r"\b(stomach|abdominal|belly|vomit|diarrhea|nausea|lubuto)\b"],
            "headache":     [r"\b(headache|migraine|omutwe|head pain)\b"],
            "chest_pain":   [r"\b(chest pain|heart pain|kifuba)\b"],
            "pregnancy":    [r"\b(pregnant|pregnancy|omuzigo|antenatal|maternal)\b"],
            "skin":         [r"\b(skin|rash|hives|eczema|olususu)\b"],
            "feeding":      [r"\b(feed|eat|appetite|breastfeed|okulya)\b"],
            "bleeding":     [r"\b(bleed|hemorrhage|blood|omusaayi)\b"],
            "mental_health":[r"\b(depress|anxiety|stress|mental|sad|worried)\b"],
        }
        for group, patterns in complaint_patterns.items():
            for pattern in patterns:
                if re.search(pattern, t):
                    return group, 0.8
        if api.get("complaint_group"):
            return api["complaint_group"], api.get("confidence", 0.7)
        return "other", 0.5

    def _symptom_to_indicator(self, symptom: str) -> Optional[str]:
        mapping = {
            "cough": "cough", "fever": "fever", "headache": "headache",
            "difficulty breathing": "breathing_difficulty", "chest pain": "chest_pain",
            "vomiting": "vomiting", "diarrhea": "diarrhea", "rash": "rash",
            "fatigue": "fatigue", "dizziness": "dizziness", "confusion": "confusion",
            "bleeding": "bleeding", "pain": "severe_pain", "seizure": "convulsions",
            "unconscious": "unconscious",
        }
        for key, value in mapping.items():
            if key in symptom.lower():
                return value
        return None

    def _extract_severity(self, text: str, api: Dict) -> Tuple[Optional[str], float]:
        t = text.lower()
        if re.search(r"\b(very severe|unbearable|worst|kya maanyi|cannot stand|emergency)\b", t):
            return "very_severe", 0.8
        if re.search(r"\b(severe|bad|terrible|kingi|extreme)\b", t):
            return "severe", 0.8
        if re.search(r"\b(moderate|medium|okay|kya bulijjo|somewhat)\b", t):
            return "moderate", 0.7
        if re.search(r"\b(mild|slight|kitono|a little|minor)\b", t):
            return "mild", 0.7
        if api.get("severity"):
            return api["severity"], api.get("confidence", 0.6)
        return None, 0.0

    def _extract_duration(self, text: str, api: Dict) -> Tuple[Optional[str], float]:
        t = text.lower()
        if re.search(r"\b(today|just started|leero|now|few hours)\b", t):
            return "6_24_hours", 0.8
        if re.search(r"\b(yesterday|jjo|last night)\b", t):
            return "6_24_hours", 0.8
        if re.search(r"\b([1-3]|one|two|three)\s*(day|days)\b", t):
            return "1_3_days", 0.8
        if re.search(r"\b([4-7]|four|five|six|seven)\s*(day|days)\b", t):
            return "4_7_days", 0.8
        if re.search(r"\b(week|wiiki)\s", t):
            return "more_than_1_week", 0.7
        if re.search(r"\b(month|mwezi)\s", t):
            return "more_than_1_month", 0.7
        if api.get("duration"):
            return api["duration"], api.get("confidence", 0.6)
        return None, 0.0

    def _extract_progression(self, text: str) -> Optional[str]:
        t = text.lower()
        if re.search(r"\b(sudden|started suddenly|all of a sudden)\b", t):
            return "sudden"
        if re.search(r"\b(getting worse|worsening|becoming more|increasing)\b", t):
            return "getting_worse"
        if re.search(r"\b(staying same|not changing|same as before)\b", t):
            return "staying_same"
        if re.search(r"\b(getting better|improving|feeling better)\b", t):
            return "getting_better"
        if re.search(r"\b(comes and goes|on and off|sometimes)\b", t):
            return "comes_and_goes"
        return None

    def _extract_age_group(self, text: str) -> Tuple[Optional[str], float]:
        t = text.lower()
        if re.search(r"\b(newborn|neonate|[0-2]\s*months?|omwana omuto)\b", t):
            return "newborn", 0.9
        if re.search(r"\b(infant|baby|[3-9]|1[0-2])\s*months?\b", t):
            return "infant", 0.9
        if re.search(r"\b(toddler|preschool|[1-5]\s*years?|omwana)\b", t):
            return "child_1_5", 0.8
        if re.search(r"\b([6-9]|1[0-2])\s*years?|school[ -]?age\b", t):
            return "child_6_12", 0.8
        if re.search(r"\b(teen|adolescent|1[3-7]\s*years?)\b", t):
            return "teen", 0.8
        if re.search(r"\b(adult|grown|([2-5][0-9]|1[8-9]|60)\s*years?|musajja|omukazi)\b", t):
            return "adult", 0.7
        if re.search(r"\b(elderly|senior|old|(6[5-9]|[7-9][0-9])\s*years?|omukadde)\b", t):
            return "elderly", 0.8
        age_match = re.search(r"\b(\d{1,2})\s*years?\b", t)
        if age_match:
            age = int(age_match.group(1))
            if age < 2:   return "newborn", 0.7
            if age < 6:   return "child_1_5", 0.7
            if age < 13:  return "child_6_12", 0.7
            if age < 18:  return "teen", 0.7
            if age < 65:  return "adult", 0.7
            return "elderly", 0.7
        return None, 0.0

    def _extract_sex(self, text: str) -> Optional[str]:
        t = text.lower()
        if re.search(r"\b(male|man|boy|omusajja)\b", t):   return "male"
        if re.search(r"\b(female|woman|girl|omukazi)\b", t): return "female"
        return None

    def _extract_patient_relation(self, text: str) -> str:
        t = text.lower()
        if re.search(r"\b(my child|my son|my daughter|my baby|omwana wange)\b", t): return "child"
        if re.search(r"\b(my mother|my father|my parent|my brother|my sister)\b", t): return "family"
        if re.search(r"\b(my friend|neighbor|someone|omulala)\b", t): return "other"
        return "self"

    def _extract_pregnancy_status(self, text: str) -> Optional[str]:
        """
        Only extracts pregnancy from explicit free-text mentions.
        Deterministic menu is the primary capture path; this is a supplementary check.
        """
        t = text.lower()
        if re.search(r"\b(pregnant|expecting|omuzigo|with child)\b", t): return "yes"
        if re.search(r"\b(maybe pregnant|might be pregnant|possibly pregnant)\b", t): return "possible"
        if re.search(r"\b(not pregnant|not expecting)\b", t): return "no"
        return None

    def _extract_location(self, text: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        t = text.lower()
        for district in UGANDAN_DISTRICTS:
            if district in t:
                return district.title(), district.title(), None, None
        village_match = re.search(r"\b(in|at)\s+([a-z\s]+?)\s*(village|lc1|parish)\b", t)
        if village_match:
            village = village_match.group(2).strip().title()
            return village, None, None, village
        return None, None, None, None

    def _extract_chronic_conditions(self, text: str) -> Tuple[List[str], bool]:
        t = text.lower()
        conditions = []
        patterns = {
            "diabetes":     r"\b(diabetes|sugar|sukaali)\b",
            "hypertension": r"\b(hypertension|high blood pressure|pressure)\b",
            "asthma":       r"\b(asthma)\b",
            "heart_disease":r"\b(heart disease|cardiac)\b",
            "epilepsy":     r"\b(epilepsy|kiguguumizi)\b",
            "sickle_cell":  r"\b(sickle cell|ss)\b",
            "hiv_aids":     r"\b(hiv|aids|slim)\b",
        }
        for condition, pattern in patterns.items():
            if re.search(pattern, t):
                conditions.append(condition)
        return conditions, len(conditions) > 0

    def _extract_medication_status(self, text: str) -> Optional[bool]:
        t = text.lower()
        if re.search(r"\b(taking medication|on medication|using drugs|taking tablets|taking medicine)\b", t):
            return True
        if re.search(r"\b(no medication|not taking|no medicine|not on any)\b", t):
            return False
        return None

    def _extract_consent(self, text: str) -> bool:
        t = text.lower()
        for pattern in [
            r"\b(yes|agree|i consent|okay|ok|sure|ndabyemera|accept)\b",
            r"\b(i understand|proceed|continue)\b",
        ]:
            if re.search(pattern, t):
                return True
        return False

    def _extract_condition_occurrence(self, text: str) -> Optional[str]:
        t = text.lower()
        if re.search(r"\b(chronic|long.?term|always have|for (months|years)|ongoing|persistent|since (childhood|birth))\b", t):
            return "long_term"
        if re.search(r"\b(happened before|had this before|again|last time|recurring|returned|came back|before)\b", t):
            return "happened_before"
        if re.search(r"\b(first time|never had|new symptom|just started|never before|for the first)\b", t):
            return "first"
        return None

    def _extract_allergies(self, text: str) -> Tuple[Optional[str], List[str]]:
        t = text.lower()
        allergy_types: List[str] = []
        if re.search(r"\b(no allerg|not allergic|don't have allerg|no known allerg)\b", t):
            return "no", []
        if re.search(r"\b(not sure|maybe allerg|possibly allerg|don't know if)\b", t):
            return "not_sure", []
        has_allergy = bool(re.search(r"\b(allerg|allergic|reaction to|sensitive to|intolerant)\b", t))
        if has_allergy:
            if re.search(r"\b(drug|medicine|medication|penicillin|aspirin|antibiotic|sulfa)\b", t):
                allergy_types.append("medication")
            if re.search(r"\b(food|nuts|peanut|dairy|milk|egg|wheat|gluten|shellfish|fish)\b", t):
                allergy_types.append("food")
            if re.search(r"\b(dust|pollen|grass|pet|animal|cat|dog|environmental|mold|bee|insect)\b", t):
                allergy_types.append("environmental")
            return "yes", allergy_types
        return None, []

    # ── Red flag detection ─────────────────────────────────────────────────────

    def _check_red_flags(self, info: ExtractedInfo, text: str) -> Dict[str, bool]:
        red_flags = {}
        t = text.lower()
        if re.search(r"\b(can'?t breathe|struggling to breathe|choking|gasping)\b", t):
            red_flags["severe_breathing_difficulty"] = True
        if re.search(r"\b(chest indrawing|ribs show|difficulty breathing)\b", t) and \
                info.age_group in ["newborn", "infant", "child_1_5"]:
            red_flags["chest_indrawing"] = True
        if re.search(r"\b(heavy bleeding|bleeding a lot|hemorrhage)\b", t):
            red_flags["severe_bleeding"] = True
        if re.search(r"\b(very pale|cold hands|collapsed|fainted)\b", t):
            red_flags["signs_of_shock"] = True
        if re.search(r"\b(unconscious|passed out|not waking|unresponsive)\b", t):
            red_flags["unconscious"] = True
        if re.search(r"\b(convulsions|seizure|fitting)\b", t):
            red_flags["convulsions"] = True
        if re.search(r"\b(confused|disoriented|not making sense)\b", t):
            red_flags["confusion"] = True
        if info.age_group in ["newborn", "infant"]:
            if re.search(r"\b(not drinking|refusing to drink|cannot breastfeed)\b", t):
                red_flags["unable_to_drink"] = True
            if re.search(r"\b(floppy|very sleepy|difficult to wake|limp)\b", t):
                red_flags["lethargic_floppy"] = True
        if info.sex == "female" and info.pregnancy_status == "yes":
            if re.search(r"\b(vaginal bleeding|bleeding in pregnancy)\b", t):
                red_flags["pregnancy_emergency"] = True
        return red_flags

    # ── Merge ──────────────────────────────────────────────────────────────────

    def _merge(self, base: ExtractedInfo, new: ExtractedInfo) -> None:
        """
        Merge NLP-extracted info into existing state.
        Deterministically-captured fields (confidence == 1.0) are never overwritten.
        """
        # Complaint group — higher confidence wins
        if new.complaint_group and new.complaint_group_confidence > base.complaint_group_confidence:
            base.complaint_group            = new.complaint_group
            base.complaint_group_confidence = new.complaint_group_confidence

        # Demographics
        if new.age_group and new.age_group_confidence > base.age_group_confidence:
            base.age_group            = new.age_group
            base.age_group_confidence = new.age_group_confidence
        if new.sex:              base.sex              = new.sex
        if new.patient_relation: base.patient_relation = new.patient_relation

        # Severity — do NOT overwrite if captured deterministically (confidence == 1.0)
        if new.severity and base.severity_confidence < 1.0 and new.severity_confidence > base.severity_confidence:
            base.severity            = new.severity
            base.severity_confidence = new.severity_confidence

        # Duration — same guard
        if new.duration and base.duration_confidence < 1.0 and new.duration_confidence > base.duration_confidence:
            base.duration            = new.duration
            base.duration_confidence = new.duration_confidence

        # Progression — do NOT overwrite deterministic capture
        if new.progression_status and not base.progression_status:
            base.progression_status = new.progression_status

        # condition_occurrence — priority merge, never overwrite deterministic
        if new.condition_occurrence and not base.condition_occurrence:
            base_pri = _CONDITION_OCCURRENCE_PRIORITY.get(base.condition_occurrence or "", -1)
            new_pri  = _CONDITION_OCCURRENCE_PRIORITY.get(new.condition_occurrence, -1)
            if new_pri > base_pri:
                base.condition_occurrence = new.condition_occurrence

        # allergies_status — never overwrite deterministic capture
        if new.allergies_status and not base.allergies_status:
            base_pri = _ALLERGY_STATUS_PRIORITY.get(base.allergies_status or "", -1)
            new_pri  = _ALLERGY_STATUS_PRIORITY.get(new.allergies_status, -1)
            if new_pri > base_pri:
                base.allergies_status = new.allergies_status

        if new.allergy_types:
            base.allergy_types = list(set(base.allergy_types + new.allergy_types))

        if new.chronic_conditions:
            base.chronic_conditions     = list(set(base.chronic_conditions + new.chronic_conditions))
            base.has_chronic_conditions = True

        base.symptom_indicators.update(new.symptom_indicators)
        base.red_flag_indicators.update(new.red_flag_indicators)

        for key, value in (new.risk_modifiers or {}).items():
            if key not in base.risk_modifiers:
                base.risk_modifiers[key] = value
            elif isinstance(value, list) and isinstance(base.risk_modifiers.get(key), list):
                base.risk_modifiers[key] = list(set(base.risk_modifiers[key] + value))

        if new.location  and not base.location:  base.location  = new.location
        if new.district  and not base.district:  base.district  = new.district
        if new.subcounty and not base.subcounty: base.subcounty = new.subcounty
        if new.village   and not base.village:   base.village   = new.village

        # Pregnancy — only update from NLP if not yet captured
        if new.pregnancy_status and not base.pregnancy_status:
            base.pregnancy_status = new.pregnancy_status

        if new.has_chronic_conditions: base.has_chronic_conditions = True
        if new.on_medication is not None and base.on_medication is None:
            base.on_medication = new.on_medication

        if new.consents_given: base.consents_given = True

        if new.primary_symptom and not base.primary_symptom:
            base.primary_symptom = new.primary_symptom
        base.secondary_symptoms = list(set(base.secondary_symptoms + new.secondary_symptoms))

    # ── Intent detection ───────────────────────────────────────────────────────

    def _detect_intent(self, info: ExtractedInfo, text: str) -> str:
        t = text.lower()
        for pattern in [
            r"\b(emergency|dying|can'?t breathe|chest pain|stroke|collapse)\b",
            r"\b(unconscious|seizure|convulsion|severe bleeding)\b",
        ]:
            if re.search(pattern, t): return "emergency"
        if info.severity in ("severe", "very_severe"): return "emergency"
        if info.red_flag_indicators:                   return "emergency"
        for pattern in [
            r"\b(follow.?up|came back|again|still sick|last time|previous)\b",
            r"\b(recurring|returning|chronic|long.?term)\b",
        ]:
            if re.search(pattern, t): return "follow_up"
        return "routine"

    # ── Missing field logic ────────────────────────────────────────────────────

    def _missing(self, info: ExtractedInfo, intent: str) -> List[str]:
        if intent == "emergency":
            required = EMERGENCY_REQUIRED
        else:
            required = CONVERSATIONAL_REQUIRED

        missing = []

        for f in required:
            if f == "age_group"            and not info.age_group:            missing.append("age_group")
            elif f == "sex"                and not info.sex:                  missing.append("sex")
            elif f == "complaint_group"    and not info.complaint_group:      missing.append("complaint_group")
            elif f == "severity"           and not info.severity:             missing.append("severity")
            elif f == "duration"           and not info.duration:             missing.append("duration")
            elif f == "progression_status" and not info.progression_status:   missing.append("progression_status")
            elif f == "condition_occurrence" and not info.condition_occurrence: missing.append("condition_occurrence")
            elif f == "allergies"          and not info.allergies_status:     missing.append("allergies")
            elif f == "chronic_conditions" and not info.has_chronic_conditions and not info.chronic_conditions:
                missing.append("chronic_conditions")
            elif f == "village"            and not info.village:              missing.append("village")
            elif f == "on_medication"      and info.on_medication is None:    missing.append("on_medication")
            elif f == "location"           and not (info.location or info.district): missing.append("location")
            elif f == "consents"           and not info.consents_given:       missing.append("consents")

        # ── PREGNANCY: auto-add for female teen/adult if not captured ──────────
        if (
            info.sex == "female"
            and info.age_group in ("teen", "adult")
            and not info.pregnancy_status
            and "pregnancy_status" not in missing
        ):
            missing.append("pregnancy_status")

        return missing

    def _has_sufficient_info(self, info: ExtractedInfo) -> bool:
        if info.red_flag_indicators:
            return True
        core = [info.age_group, info.sex, info.complaint_group, info.severity,
                info.duration, info.consents_given]
        return all(core) and bool(info.location or info.district)

    # ── Response builders ─────────────────────────────────────────────────────

    def _build_question(self, state: ConversationState) -> Dict[str, Any]:
        """
        Determine the next question. Uses structured menus for eligible fields;
        falls back to LLM for free-text fields (complaint_group, location, village,
        age_group, sex, chronic_conditions detail).
        """
        missing = state.missing_fields
        asked   = set(state.asked_fields_history)

        # Priority order for asking
        priority_order = [
            "complaint_group", "severity", "duration", "age_group", "sex",
            "progression_status", "condition_occurrence", "location", "village",
            "chronic_conditions", "on_medication", "allergies",
            "pregnancy_status", "consents",
        ]

        # Exclude already-asked fields
        unasked = [f for f in missing if f not in asked]
        if not unasked:
            unasked = missing[:1]  # Re-ask first if all asked (shouldn't happen normally)

        unasked.sort(key=lambda f: priority_order.index(f) if f in priority_order else 99)
        next_field = unasked[0]

        # ── Structured menu path ───────────────────────────────────────────
        if next_field in STRUCTURED_FIELDS:
            prompt = MenuResolver.get_prompt(next_field)
            if prompt:
                # Prepend empathy line from LLM if we have conversation context
                empathy = self._get_empathy_prefix(state)
                message  = f"{empathy}\n\n{prompt}" if empathy else prompt

                state.last_question_field = next_field
                if next_field not in state.asked_fields_history:
                    state.asked_fields_history.append(next_field)

                state.conversation_history.append({
                    "role": "agent", "content": message, "turn": state.turn_number,
                })
                self._save(state)

                total     = len(CONVERSATIONAL_REQUIRED)
                collected = total - len([f for f in CONVERSATIONAL_REQUIRED if f in state.missing_fields])

                return {
                    "status":             "incomplete",
                    "action":             "answer_menu",
                    "intent":             state.intent,
                    "message":            message,
                    "missing_fields":     state.missing_fields,
                    "active_menu_field":  next_field,
                    "extracted_so_far":   state.extracted_info.to_dict(),
                    "progress":           f"{collected}/{total} fields collected",
                    "patient_token":      state.patient_token,
                    "red_flags_detected": state.red_flags_detected,
                }

        # ── LLM free-text path (location, age, sex, complaint, chronic detail) ─
        state.last_question_field = None  # No deterministic binding for these

        context = {
            "missing_fields":   missing,
            "extracted_so_far": {
                "complaint_group":      state.extracted_info.complaint_group,
                "age_group":            state.extracted_info.age_group,
                "sex":                  state.extracted_info.sex,
                "severity":             state.extracted_info.severity,
                "duration":             state.extracted_info.duration,
                "progression_status":   state.extracted_info.progression_status,
                "condition_occurrence": state.extracted_info.condition_occurrence,
                "allergies_status":     state.extracted_info.allergies_status,
                "allergy_types":        state.extracted_info.allergy_types,
                "chronic_conditions":   state.extracted_info.chronic_conditions,
                "village":              state.extracted_info.village,
                "on_medication":        state.extracted_info.on_medication,
                "symptom_indicators":   state.extracted_info.symptom_indicators,
                "district":             state.extracted_info.district,
                "location":             state.extracted_info.location,
            },
            "red_flags_detected": state.red_flags_detected,
            "intent":             state.intent,
            "turn_number":        state.turn_number,
        }

        # Limit to two most urgent free-text fields
        free_text_missing = [f for f in unasked if f not in STRUCTURED_FIELDS][:2]
        if not free_text_missing:
            free_text_missing = [next_field]

        agent_message = generate_followup_questions(
            missing_fields=free_text_missing,
            conversation_history=state.conversation_history,
            extracted_so_far=context["extracted_so_far"],
            intent=state.intent,
            context=context,
            asked_fields_history=set(state.asked_fields_history),
        )

        for f in free_text_missing:
            if f not in state.asked_fields_history:
                state.asked_fields_history.append(f)

        state.conversation_history.append({
            "role": "agent", "content": agent_message, "turn": state.turn_number,
        })
        self._save(state)

        total     = len(CONVERSATIONAL_REQUIRED)
        collected = total - len([f for f in CONVERSATIONAL_REQUIRED if f in state.missing_fields])

        return {
            "status":             "incomplete",
            "action":             "answer_questions",
            "intent":             state.intent,
            "message":            agent_message,
            "missing_fields":     state.missing_fields,
            "extracted_so_far":   state.extracted_info.to_dict(),
            "progress":           f"{collected}/{total} fields collected",
            "patient_token":      state.patient_token,
            "red_flags_detected": state.red_flags_detected,
        }

    def _get_empathy_prefix(self, state: ConversationState) -> str:
        """
        Ask LLM for a single empathetic sentence acknowledging the last patient message.
        Kept under 15 words to be brief. Returns empty string on failure.
        """
        if len(state.conversation_history) < 2:
            return ""
        last_patient = next(
            (m["content"] for m in reversed(state.conversation_history) if m["role"] == "patient"),
            "",
        )
        if not last_patient:
            return ""

        from apps.triage.ml_models import _call_llm
        prompt = (
            f"Patient said: '{last_patient[:100]}'\n"
            "Write ONE short empathetic sentence (under 15 words) acknowledging this. "
            "Do not ask anything. Just acknowledge."
        )
        result = _call_llm(
            "You are a warm medical triage assistant in Uganda. Be brief and kind.",
            prompt,
            max_tokens=40,
        )
        return result.strip() if result else ""

    def _build_complete(self, state: ConversationState) -> Dict[str, Any]:
        structured   = self._to_structured(state.extracted_info)
        consistency  = self._consistency_check(state.extracted_info)
        suggestions  = self._clinical_suggestions(state.extracted_info, state.intent)

        triage_result = None
        try:
            print(f"\n🎯 Auto-submitting to triage orchestrator: {state.patient_token}")
            from apps.triage.services.triage_orchestrator import TriageOrchestrator
            from apps.triage.tools.intake_validation import IntakeValidationTool

            intake_tool = IntakeValidationTool()
            is_valid, cleaned_data, errors = intake_tool.validate(structured)

            if is_valid:
                session, decision, red_flags = TriageOrchestrator.run(
                    state.patient_token, cleaned_data
                )
                triage_result = {
                    "risk_level":             session.risk_level,
                    "follow_up_priority":     session.follow_up_priority,
                    "decision_basis":         decision.get("decision_basis"),
                    "facility_type":          decision.get("facility_type"),
                    "recommended_action":     decision.get("recommended_action"),
                    "assessment_completed_at": (
                        session.assessment_completed_at.isoformat()
                        if session.assessment_completed_at else None
                    ),
                }
                print(f"✅ Triage complete: {session.risk_level}")
            else:
                print(f"⚠️ Validation failed: {errors}")
                triage_result = {"error": "Validation failed", "errors": errors}
        except Exception as e:
            print(f"⚠️ Triage submission failed: {e}")
            import traceback; traceback.print_exc()
            triage_result = {"error": str(e)}

        return {
            "status":                    "complete",
            "action":                    "proceed_to_triage",
            "intent":                    state.intent,
            "structured_data":           structured,
            "triage_result":             triage_result,
            "consistency_issues":        consistency,
            "clinical_suggestions":      suggestions,
            "red_flags_detected":        state.red_flags_detected,
            "red_flag_detected_at_turn": state.red_flag_detected_at_turn,
            "confidence_scores": {
                "complaint_group": state.extracted_info.complaint_group_confidence,
                "age_group":       state.extracted_info.age_group_confidence,
                "severity":        state.extracted_info.severity_confidence,
                "duration":        state.extracted_info.duration_confidence,
            },
            "conversation_turns": state.turn_number,
            "patient_token":      state.patient_token,
        }

    # ── Structured output ─────────────────────────────────────────────────────

    def _to_structured(self, info: ExtractedInfo) -> Dict[str, Any]:
        age_group = info.age_group or "adult"
        district  = info.district or info.location or "Unknown"

        severity_map = {
            "very_severe": "very_severe", "severe": "severe",
            "moderate": "moderate",       "mild": "mild",
        }
        duration_map = {
            "less_than_1_hour": "less_than_1_hour", "1_6_hours": "1_6_hours",
            "6_24_hours": "6_24_hours",              "1_3_days": "1_3_days",
            "4_7_days": "4_7_days",                  "more_than_1_week": "more_than_1_week",
            "more_than_1_month": "more_than_1_month",
        }
        pregnancy_map = {"yes": "yes", "possible": "possible", "no": "no",
                         "not_sure": "possible", None: "not_applicable"}

        return {
            "complaint_text":   info.complaint_text,
            "complaint_group":  info.complaint_group or "other",
            "age_group":        age_group,
            "sex":              info.sex or "other",
            "patient_relation": info.patient_relation,
            "symptom_indicators":   info.symptom_indicators,
            "red_flag_indicators":  info.red_flag_indicators,
            "risk_modifiers":       info.risk_modifiers,
            "symptom_severity":     severity_map.get(info.severity, "moderate"),
            "symptom_duration":     duration_map.get(info.duration, "1_3_days"),
            "progression_status":   info.progression_status,
            "condition_occurrence": info.condition_occurrence,
            "allergies_status":     info.allergies_status,
            "allergy_types":        info.allergy_types,
            "chronic_conditions":   info.chronic_conditions,
            "district":             district,
            "subcounty":            info.subcounty,
            "village":              info.village,
            "pregnancy_status":     pregnancy_map.get(info.pregnancy_status, "not_applicable"),
            "has_chronic_conditions": info.has_chronic_conditions,
            "on_medication":        info.on_medication if info.on_medication is not None else False,
            "consent_medical_triage": info.consents_given,
            "consent_data_sharing":   info.consents_given,
            "consent_follow_up":      info.consents_given,
            "session_status":       "in_progress",
            "channel":              "whatsapp",
            "age_range":            self._map_age_group_to_range(age_group),
            "primary_symptom":      info.primary_symptom or info.complaint_group,
            "secondary_symptoms":   info.secondary_symptoms,
            "symptom_pattern":      info.progression_status,
        }

    def _map_age_group_to_range(self, age_group: str) -> str:
        return {
            "newborn": "under_5", "infant": "under_5", "child_1_5": "under_5",
            "child_6_12": "5_12", "teen": "13_17", "adult": "18_30", "elderly": "51_plus",
        }.get(age_group, "18_30")

    # ── Consistency & suggestions ─────────────────────────────────────────────

    def _consistency_check(self, info: ExtractedInfo) -> List[str]:
        issues = []
        if info.sex == "male" and info.pregnancy_status in ["yes", "possible"]:
            issues.append("⚠️ Male patient marked as pregnant — please verify.")
        if info.pregnancy_status in ["yes", "possible"] and info.age_group not in ["teen", "adult"]:
            issues.append(f"⚠️ Pregnancy status unusual for age group '{info.age_group}'.")
        if info.duration in ["less_than_1_hour", "1_6_hours"] and info.has_chronic_conditions:
            issues.append("⚠️ Short duration with chronic condition — may be acute episode.")
        if info.severity in ["severe", "very_severe"] and info.severity_confidence < 0.6:
            issues.append("⚠️ Severe symptoms with low confidence — confirm.")
        return issues

    def _clinical_suggestions(self, info: ExtractedInfo, intent: str) -> List[Dict]:
        suggestions = []
        if info.complaint_group == "fever":
            if info.duration in ["more_than_1_week", "more_than_1_month"]:
                suggestions.append({"priority": "high",
                    "message": "Fever >1 week may indicate malaria, typhoid, or other infections."})
            if info.age_group in ["newborn", "infant"]:
                suggestions.append({"priority": "critical",
                    "message": "Fever in young infants requires urgent evaluation."})
        if info.complaint_group == "breathing" and info.symptom_indicators.get("breathing_difficulty"):
            suggestions.append({"priority": "high",
                "message": "Breathing difficulty requires prompt medical assessment."})
        if info.pregnancy_status == "yes":
            suggestions.append({"priority": "high",
                "message": "Pregnant patient — ensure antenatal care access and monitor closely."})
        if info.age_group == "elderly" and info.complaint_group in ["chest_pain", "breathing", "headache"]:
            suggestions.append({"priority": "high",
                "message": "Elderly patients with these symptoms need urgent evaluation."})
        if intent == "emergency":
            suggestions.append({"priority": "critical",
                "message": "Based on symptoms, please seek immediate medical attention."})
        return suggestions


# ============================================================================
# INTAKE VALIDATION TOOL
# ============================================================================

class IntakeValidationTool:
    """Validates structured triage data before submission to the orchestrator."""

    REQUIRED_FIELDS = ALL_REQUIRED_FIELDS

    VALID_CHOICES: Dict[str, List[str]] = {
        "complaint_group": [
            "fever", "breathing", "injury", "abdominal", "headache",
            "chest_pain", "pregnancy", "skin", "feeding", "bleeding",
            "mental_health", "other",
        ],
        "age_group": ["newborn", "infant", "child_1_5", "child_6_12", "teen", "adult", "elderly"],
        "sex": ["male", "female", "other"],
        "patient_relation": ["self", "child", "family", "other"],
        "symptom_severity": ["mild", "moderate", "severe", "very_severe"],
        "symptom_duration": [
            "less_than_1_hour", "1_6_hours", "6_24_hours", "1_3_days",
            "4_7_days", "more_than_1_week", "more_than_1_month",
        ],
        "progression_status": [
            "sudden", "getting_worse", "staying_same", "getting_better", "comes_and_goes",
        ],
        "pregnancy_status": ["yes", "possible", "no", "not_applicable"],
        "channel": ["ussd", "sms", "whatsapp", "web", "mobile_app"],
        "condition_occurrence": ["first", "happened_before", "long_term"],
        "allergies_status":     ["yes", "no", "not_sure"],
        "allergy_types":        ["medication", "food", "environmental"],
    }

    def __init__(self):
        self.agent    = ConversationalIntakeAgent()
        self.errors:   List[str] = []
        self.warnings: List[str] = []

    def process_intake(self, patient_token: str, free_text: str,
                       conversation_id: Optional[str] = None) -> Dict[str, Any]:
        if conversation_id:
            return self.agent.continue_conversation(patient_token, free_text)
        return self.agent.start_conversation(patient_token, free_text)

    def validate(self, data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], List[str]]:
        self.errors   = []
        self.warnings = []
        self._validate_required(data)
        self._validate_consents(data)
        self._validate_field_choices(data)
        self._validate_consistency(data)
        self._validate_age_group(data)
        self._validate_condition_occurrence(data)
        self._validate_allergies(data)
        self._validate_pregnancy(data)
        cleaned = self._clean(data) if not self.errors else {}
        return (not self.errors, cleaned, self.errors)

    def _validate_required(self, data: Dict):
        for f in self.REQUIRED_FIELDS:
            if not data.get(f):
                self.errors.append(f"Required field '{f}' is missing")

    def _validate_consents(self, data: Dict):
        for c in ["consent_medical_triage", "consent_data_sharing", "consent_follow_up"]:
            if not data.get(c):
                self.errors.append(f"Patient must consent to: {c}")

    def _validate_field_choices(self, data: Dict):
        for field, valid in self.VALID_CHOICES.items():
            value = data.get(field)
            if not value:
                continue
            if isinstance(value, list):
                for item in value:
                    if item not in valid:
                        self.errors.append(f"Invalid value '{item}' for '{field}'.")
            elif value not in valid:
                self.errors.append(f"Invalid value '{value}' for '{field}'.")

    def _validate_consistency(self, data: Dict):
        if data.get("sex") == "male" and data.get("pregnancy_status") in ["yes", "possible"]:
            self.errors.append("Inconsistency: male patient cannot be pregnant.")
        if data.get("age_group") in ["newborn", "infant", "child_1_5", "child_6_12"] and \
                "hypertension" in data.get("chronic_conditions", []):
            self.warnings.append("Unusual: hypertension in a child — please verify.")

    def _validate_age_group(self, data: Dict):
        valid = self.VALID_CHOICES["age_group"]
        ag = data.get("age_group")
        if ag and ag not in valid:
            self.errors.append(f"Invalid age_group '{ag}'.")

    def _validate_condition_occurrence(self, data: Dict):
        value = data.get("condition_occurrence")
        if value and value not in self.VALID_CHOICES["condition_occurrence"]:
            self.errors.append(f"Invalid condition_occurrence '{value}'.")

    def _validate_allergies(self, data: Dict):
        status = data.get("allergies_status")
        if status and status not in self.VALID_CHOICES["allergies_status"]:
            self.errors.append(f"Invalid allergies_status '{status}'.")
        types = data.get("allergy_types", [])
        if types and not isinstance(types, list):
            self.errors.append("allergy_types must be a list")
        elif types:
            for t in types:
                if t not in self.VALID_CHOICES["allergy_types"]:
                    self.errors.append(f"Invalid allergy_type '{t}'.")

    def _validate_pregnancy(self, data: Dict):
        """Ensure pregnancy_status is captured for female teens/adults."""
        if (
            data.get("sex") == "female"
            and data.get("age_group") in ("teen", "adult")
            and not data.get("pregnancy_status")
        ):
            self.warnings.append(
                "pregnancy_status missing for female teen/adult patient — "
                "should be captured before triage completion."
            )

    def _clean(self, data: Dict) -> Dict:
        cleaned = data.copy()
        if "patient_token" not in cleaned:
            cleaned["patient_token"] = f"PT-{uuid.uuid4().hex[:16].upper()}"
        cleaned.setdefault("session_status",      "in_progress")
        cleaned.setdefault("channel",             "whatsapp")
        cleaned.setdefault("symptom_indicators",  {})
        cleaned.setdefault("red_flag_indicators", {})
        cleaned.setdefault("risk_modifiers",      {})
        cleaned.setdefault("chronic_conditions",  [])
        cleaned.setdefault("allergy_types",       [])

        if "age_range" in cleaned and "age_group" not in cleaned:
            cleaned["age_group"] = {
                "under_5": "child_1_5", "5_12": "child_6_12",
                "13_17": "teen", "18_30": "adult",
                "31_50": "adult", "51_plus": "elderly",
            }.get(cleaned["age_range"], "adult")

        return cleaned


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def process_conversational_intake(patient_token: str, text: str) -> Dict[str, Any]:
    return IntakeValidationTool().process_intake(patient_token, text)


def validate_structured_intake(data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], List[str]]:
    return IntakeValidationTool().validate(data)