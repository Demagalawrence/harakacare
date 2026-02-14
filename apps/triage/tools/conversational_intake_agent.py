"""
HarakaCare Conversational Intake Agent
=======================================
WhatsApp-style chatbot intake — every follow-up question is generated
by the LLM based on context, not static templates.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from django.core.cache import cache

from apps.triage.ml_models import APISymptomExtractor, generate_followup_questions
from apps.conversations.models import Conversation, Message
from dataclasses import asdict


logger = logging.getLogger(__name__)


# ============================================================================
# CONSTANTS
# ============================================================================

ALL_REQUIRED_FIELDS = [
    "age_range", "district", "primary_symptom",
    "symptom_severity", "symptom_duration", "condition_occurrence",
    "consent_medical_triage", "consent_data_sharing", "consent_follow_up",
]

CONVERSATIONAL_REQUIRED = [
    "age_range", "primary_symptom", "severity", "duration",
    "location", "condition_occurrence", "consents",
]

EMERGENCY_REQUIRED = ["age_range", "primary_symptom", "severity"]

UGANDAN_DISTRICTS = [
    "kampala", "wakiso", "mukono", "jinja", "mbarara",
    "gulu", "lira", "mbale", "arua", "kasese", "masaka",
    "hoima", "fort portal", "kabale", "soroti", "tororo",
    "iganga", "entebbe", "mityana", "mubende",
]


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
    primary_symptom: Optional[str]       = None
    secondary_symptoms: List[str]        = field(default_factory=list)
    severity: Optional[str]             = None
    duration: Optional[str]             = None
    age_range: Optional[str]            = None
    sex: Optional[str]                  = None
    pregnancy_status: Optional[str]     = None
    location: Optional[str]            = None
    condition_occurrence: Optional[str] = None
    chronic_conditions: List[str]       = field(default_factory=list)
    current_medication: Optional[str]   = None
    has_allergies: Optional[str]        = None
    consents_given: bool                = False

    primary_symptom_confidence: float   = 0.0
    severity_confidence: float          = 0.0
    duration_confidence: float          = 0.0


@dataclass
class ConversationState:
    patient_token: str
    turn_number: int
    extracted_info: ExtractedInfo
    missing_fields: List[str]
    conversation_history: List[Dict[str, str]]
    intent: str = "routine"
    completed: bool = False

    def to_dict(self) -> Dict:
        return {
            **asdict(self),
            "intent": self.intent,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ConversationState":
        data = data.copy()
        data["extracted_info"] = ExtractedInfo(**data["extracted_info"])
        return cls(**data)


# ============================================================================
# PATTERN LEARNING MEMORY
# ============================================================================

class ValidationPatternMemory:
    MAX = 1000

    def __init__(self):
        self._store: Dict[str, Dict] = {}

    def save(self, key: str, pattern: Dict):
        if len(self._store) >= self.MAX:
            del self._store[next(iter(self._store))]
        self._store[key] = pattern

    def by_intent(self, intent: str) -> List[Dict]:
        return [p for p in self._store.values() if p.get("intent") == intent]


# ============================================================================
# CONVERSATIONAL INTAKE AGENT
# ============================================================================

class ConversationalIntakeAgent:

    def __init__(self):
        self.extractor      = APISymptomExtractor()
        self.pattern_memory = ValidationPatternMemory()
        self._mem_cache: Dict[str, Dict] = {}
        logger.info("✓ ConversationalIntakeAgent initialised")

    # ------------------------------------------------------------------ #
    # PUBLIC ENTRY POINTS
    # ------------------------------------------------------------------ #

    def start_conversation(self, token: str, message: str) -> Dict[str, Any]:
        print(f"\n🆕 NEW CONVERSATION: {token}")
        info    = self._extract(message)
        intent  = self._detect_intent(info, message)
        missing = self._missing(info, intent)

        state = ConversationState(
            patient_token=token,
            turn_number=1,
            extracted_info=info,
            missing_fields=missing,
            conversation_history=[{"role": "patient", "content": message, "turn": 1}],
            intent=intent,
            completed=len(missing) == 0,
        )
        self._save(state)
        self._learn(state)

        print(f"   Intent: {intent}  |  Missing: {missing}")
        return self._build_complete(state) if state.completed else self._build_question(state)

    def continue_conversation(self, token: str, message: str) -> Dict[str, Any]:
        print(f"\n🔄 CONTINUE: {token}  msg={message!r}")
        state = self._load(token)
        if not state:
            print("   ❌ No state — starting fresh")
            return self.start_conversation(token, message)

        state.turn_number += 1
        state.conversation_history.append(
            {"role": "patient", "content": message, "turn": state.turn_number}
        )

        new = self._extract(message)
        self._merge(state.extracted_info, new)

        state.intent        = self._detect_intent(state.extracted_info, message)
        state.missing_fields = self._missing(state.extracted_info, state.intent)
        state.completed      = len(state.missing_fields) == 0

        print(f"   Intent: {state.intent}  |  Missing: {state.missing_fields}  |  Done: {state.completed}")
        self._save(state)
        self._learn(state)

        return self._build_complete(state) if state.completed else self._build_question(state)

    # ------------------------------------------------------------------ #
    # EXTRACTION
    # ------------------------------------------------------------------ #

    def _extract(self, text: str) -> ExtractedInfo:
        api  = self.extractor.extract(text)
        syms = self.extractor.extract_symptoms(text)

        primary, p_conf, secondary = None, 0.0, []
        if syms:
            syms.sort(key=lambda s: s.confidence, reverse=True)
            primary, p_conf = syms[0].symptom, syms[0].confidence
            secondary = [s.symptom for s in syms[1:]]
        elif api.get("symptoms"):
            lst = api["symptoms"]
            primary, p_conf = lst[0], api.get("confidence", 0.8)
            secondary = lst[1:]

        severity, s_conf = (
            (api.get("severity"), api.get("confidence", 0.8))
            if api.get("severity")
            else self._severity_rules(text)
        )
        duration, d_conf = (
            (api.get("duration"), api.get("confidence", 0.8))
            if api.get("duration")
            else self._duration_rules(text)
        )

        return ExtractedInfo(
            primary_symptom             = primary,
            secondary_symptoms          = secondary,
            severity                    = severity,
            duration                    = duration,
            age_range                   = self._age_rules(text),
            sex                         = self._sex_rules(text),
            pregnancy_status            = self._pregnancy_rules(text),
            location                    = self._location_rules(text),
            condition_occurrence        = self._occurrence_rules(text),
            consents_given              = self._consent_rules(text),
            primary_symptom_confidence  = p_conf,
            severity_confidence         = s_conf,
            duration_confidence         = d_conf,
        )

    # ------------------------------------------------------------------ #
    # MERGING
    # ------------------------------------------------------------------ #

    def _merge(self, base: ExtractedInfo, new: ExtractedInfo):
        for attr in ("primary_symptom", "severity", "duration", "condition_occurrence"):
            if not getattr(base, attr) and getattr(new, attr):
                setattr(base, attr, getattr(new, attr))

        for attr in ("age_range", "sex", "location", "pregnancy_status",
                     "current_medication", "has_allergies"):
            if getattr(new, attr):
                setattr(base, attr, getattr(new, attr))

        if new.consents_given:
            base.consents_given = True

        base.secondary_symptoms = list(set(base.secondary_symptoms + new.secondary_symptoms))
        if new.chronic_conditions:
            base.chronic_conditions = list(set(base.chronic_conditions + new.chronic_conditions))

    # ------------------------------------------------------------------ #
    # INTENT DETECTION
    # ------------------------------------------------------------------ #

    def _detect_intent(self, info: ExtractedInfo, text: str) -> str:
        t = text.lower()
        if info.severity in ("severe", "very_severe"):
            return "emergency"
        if re.search(r"\b(emergency|dying|can'?t breathe|chest pain|stroke|collapse)\b", t):
            return "emergency"
        if re.search(r"\b(follow.?up|came back|again|still sick|last time|previous)\b", t):
            return "follow_up"
        if info.condition_occurrence in ("happened_before", "long_term"):
            return "follow_up"
        return "routine"

    # ------------------------------------------------------------------ #
    # MISSING FIELD LOGIC
    # ------------------------------------------------------------------ #

    def _missing(self, info: ExtractedInfo, intent: str) -> List[str]:
        required = EMERGENCY_REQUIRED if intent == "emergency" else CONVERSATIONAL_REQUIRED
        missing  = []

        for f in required:
            if f == "consents":
                if not info.consents_given:
                    missing.append("consents")
            elif f == "location":
                if not info.location:
                    missing.append("location")
            else:
                if not getattr(info, f, None):
                    missing.append(f)

        if info.sex == "female" and not info.pregnancy_status:
            if "pregnancy_status" not in missing:
                missing.append("pregnancy_status")

        return missing

    # ------------------------------------------------------------------ #
    # CONSISTENCY CHECKS
    # ------------------------------------------------------------------ #

    def _consistency_check(self, info: ExtractedInfo) -> List[str]:
        issues = []
        if info.sex == "male" and info.pregnancy_status == "pregnant":
            issues.append("⚠️ Male patient marked as pregnant — please verify.")
        if info.duration in ("today", "0_1_days") and info.condition_occurrence == "long_term":
            issues.append("⚠️ Symptom started today but marked as long-term — please clarify.")
        if info.age_range in ("under_5", "5_12") and "hypertension" in info.chronic_conditions:
            issues.append("⚠️ Hypertension in a child is unusual — please confirm.")
        return issues

    # ------------------------------------------------------------------ #
    # CLINICAL SUGGESTIONS
    # ------------------------------------------------------------------ #

    def _clinical_suggestions(self, info: ExtractedInfo, intent: str) -> List[Dict]:
        suggestions = []
        if info.primary_symptom == "fever" and info.duration in ("more_than_1_week", "over_1_week"):
            suggestions.append({
                "priority": "high",
                "message": "Fever lasting over a week may indicate malaria or typhoid. Consider a rapid diagnostic test.",
            })
        if "diabetes" in info.chronic_conditions and info.primary_symptom in (
            "fatigue", "increased_thirst", "frequent_urination"
        ):
            suggestions.append({
                "priority": "medium",
                "message": "Diabetic patients with these symptoms should check their blood sugar levels.",
            })
        if intent == "emergency":
            suggestions.append({
                "priority": "critical",
                "message": "Based on your symptoms, please seek immediate medical attention.",
            })
        return suggestions

    # ------------------------------------------------------------------ #
    # RESPONSE BUILDERS
    # ------------------------------------------------------------------ #

    def _build_question(self, state: ConversationState) -> Dict[str, Any]:
        """Ask the LLM to generate a context-aware follow-up message."""

        # Call LLM to generate intelligent follow-up
        agent_message = generate_followup_questions(
            missing_fields       = state.missing_fields,
            conversation_history = state.conversation_history,
            extracted_so_far     = asdict(state.extracted_info),
            intent               = state.intent,
        )

        # Log the agent turn into history
        state.conversation_history.append({
            "role":    "agent",
            "content": agent_message,
            "turn":    state.turn_number,
        })
        self._save(state)

        total     = len(CONVERSATIONAL_REQUIRED)
        collected = total - len([f for f in CONVERSATIONAL_REQUIRED if f in state.missing_fields])

        return {
            "status":           "incomplete",
            "action":           "answer_questions",
            "intent":           state.intent,
            # Single natural-language message for the WhatsApp UI
            "message":          agent_message,
            # Also expose structured list for any UI that needs it
            "missing_fields":   state.missing_fields,
            "extracted_so_far": asdict(state.extracted_info),
            "progress":         f"{collected}/{total} fields collected",
            "patient_token":    state.patient_token,
        }

    def _build_complete(self, state: ConversationState) -> Dict[str, Any]:
        structured  = self._to_structured(state.extracted_info)
        consistency = self._consistency_check(state.extracted_info)
        suggestions = self._clinical_suggestions(state.extracted_info, state.intent)

        return {
            "status":               "complete",
            "action":               "proceed_to_validation",
            "intent":               state.intent,
            "structured_data":      structured,
            "consistency_issues":   consistency,
            "clinical_suggestions": suggestions,
            "confidence_scores": {
                "primary_symptom": state.extracted_info.primary_symptom_confidence,
                "severity":        state.extracted_info.severity_confidence,
                "duration":        state.extracted_info.duration_confidence,
            },
            "conversation_turns": state.turn_number,
            "patient_token":      state.patient_token,
        }

    def _to_structured(self, info: ExtractedInfo) -> Dict[str, Any]:
        return {
            "age_range":              info.age_range,
            "sex":                    info.sex,
            "district":               info.location or "Unknown",
            "primary_symptom":        info.primary_symptom,
            "secondary_symptoms":     info.secondary_symptoms,
            "symptom_severity":       info.severity,
            "symptom_duration":       info.duration,
            "pregnancy_status":       info.pregnancy_status,
            "condition_occurrence":   info.condition_occurrence or "first_occurrence",
            "chronic_conditions":     info.chronic_conditions or ["none"],
            "current_medication":     info.current_medication or "no",
            "has_allergies":          info.has_allergies or "no",
            "consent_medical_triage": info.consents_given,
            "consent_data_sharing":   info.consents_given,
            "consent_follow_up":      info.consents_given,
            "session_status":         "in_progress",
            "channel":                "whatsapp",
        }

    # ------------------------------------------------------------------ #
    # RULE-BASED EXTRACTORS
    # ------------------------------------------------------------------ #

    def _severity_rules(self, text: str) -> Tuple[Optional[str], float]:
        t = text.lower()
        if re.search(r"\b(very severe|unbearable|worst|kya maanyi|cannot stand)\b", t): return "very_severe", 0.7
        if re.search(r"\b(severe|bad|terrible|kingi)\b", t):                            return "severe",      0.7
        if re.search(r"\b(moderate|medium|okay|kya bulijjo)\b", t):                     return "moderate",    0.6
        if re.search(r"\b(mild|slight|kitono|a little)\b", t):                          return "mild",        0.6
        return "moderate", 0.5

    def _duration_rules(self, text: str) -> Tuple[Optional[str], float]:
        t = text.lower()
        if re.search(r"\b(today|just started|leero)\b", t):                              return "today",            0.8
        if re.search(r"\b(yesterday|jjo)\b", t):                                         return "1_3_days",          0.8
        if re.search(r"\b([1-3]|one|two|three)\s*(day|days)\b", t):                      return "1_3_days",          0.8
        if re.search(r"\b([4-7]|four|five|six|seven)\s*(day|days)\b", t):                return "4_7_days",          0.8
        if re.search(r"\b(week|wiiki)\b", t):                                            return "more_than_1_week",  0.7
        if re.search(r"\b(month|mwezi)\b", t):                                           return "more_than_1_month", 0.7
        return None, 0.0

    def _age_rules(self, text: str) -> Optional[str]:
        t = text.lower()
        if re.search(r"\b(baby|infant|under\s*5|omwana)\b", t):                      return "under_5"
        if re.search(r"\b(child|kid|([5-9]|1[0-2])\s*years?)\b", t):                return "5_12"
        if re.search(r"\b(teen|adolescent|1[3-7]\s*year)\b", t):                     return "13_17"
        if re.search(r"\b(1[8-9]|2[0-9]|30)\s*years?\b", t):                        return "18_30"
        if re.search(r"\b(3[1-9]|4[0-9]|50)\s*years?\b", t):                        return "31_50"
        if re.search(r"\b((5[1-9]|[6-9]\d)\s*year|elderly|musajja mukulu)\b", t):   return "51_plus"
        m = re.search(r"\b(\d{2})\s*[-–]\s*(\d{2})\b", t)
        if m:
            lo = int(m.group(1))
            if lo < 5:  return "under_5"
            if lo < 13: return "5_12"
            if lo < 18: return "13_17"
            if lo < 31: return "18_30"
            if lo < 51: return "31_50"
            return "51_plus"
        return None

    def _sex_rules(self, text: str) -> Optional[str]:
        t = text.lower()
        if re.search(r"\b(male|man|boy|omusajja)\b", t):               return "male"
        if re.search(r"\b(female|woman|girl|omukazi|pregnant)\b", t):  return "female"
        return None

    def _pregnancy_rules(self, text: str) -> Optional[str]:
        t = text.lower()
        if re.search(r"\b(not pregnant|not expecting|not with child)\b", t):      return "not_pregnant"
        if re.search(r"\b(pregnant|expecting|omuzigo|trimester|with child)\b", t): return "pregnant"
        return None

    def _location_rules(self, text: str) -> Optional[str]:
        t = text.lower()
        for d in UGANDAN_DISTRICTS:
            if d in t:
                return d.title()
        return None

    def _occurrence_rules(self, text: str) -> Optional[str]:
        t = text.lower()
        if re.search(r"\b(first time|never had|first occurrence)\b", t):          return "first_occurrence"
        if re.search(r"\b(happened before|had it before|again|recurrent)\b", t):  return "happened_before"
        if re.search(r"\b(long.?term|chronic|always|on.?going|years)\b", t):      return "long_term"
        return None

    def _consent_rules(self, text: str) -> bool:
        return bool(re.search(r"\b(yes|agree|i consent|okay|ok|sure|ndabyemera)\b", text.lower()))

    # ------------------------------------------------------------------ #
    # STATE PERSISTENCE
    # ------------------------------------------------------------------ #

    def _save(self, state: ConversationState):

        conversation, _ = Conversation.objects.get_or_create(
            patient_token=state.patient_token
        )

        # update conversation state
        conversation.turn_number = state.turn_number
        conversation.intent = state.intent
        conversation.completed = state.completed
        conversation.extracted_state = asdict(state.extracted_info)
        conversation.save()

        # store only the newest message
        last_message = state.conversation_history[-1]

        Message.objects.create(
            conversation=conversation,
            role=last_message["role"],
            content=last_message["content"],
            turn=last_message["turn"],
        )

    def _load(self, token: str) -> Optional[ConversationState]:

        try:
            conversation = Conversation.objects.get(patient_token=token)
        except Conversation.DoesNotExist:
            return None

        # rebuild message history
        messages = conversation.messages.all().order_by("turn")

        history = [
            {"role": m.role, "content": m.content, "turn": m.turn}
            for m in messages
        ]

        # rebuild ExtractedInfo dataclass
        info = ExtractedInfo(**conversation.extracted_state)

        return ConversationState(
            patient_token=conversation.patient_token,
            turn_number=conversation.turn_number,
            extracted_info=info,
            missing_fields=self._missing(info, conversation.intent),
            conversation_history=history,
            intent=conversation.intent,
            completed=conversation.completed,
        )

    # ------------------------------------------------------------------ #
    # LEARNING
    # ------------------------------------------------------------------ #

    def _learn(self, state: ConversationState):
        key = hashlib.md5(f"{state.patient_token}:{state.turn_number}".encode()).hexdigest()
        self.pattern_memory.save(key, {
            "intent":    state.intent,
            "turn":      state.turn_number,
            "missing":   state.missing_fields,
            "completed": state.completed,
            "ts":        datetime.now().isoformat(),
        })


# ============================================================================
# INTAKE VALIDATION TOOL  (backward-compatible wrapper)
# ============================================================================

class IntakeValidationTool:

    REQUIRED_FIELDS = ALL_REQUIRED_FIELDS

    def __init__(self):
        self.agent    = ConversationalIntakeAgent()
        self.errors:   List[str] = []
        self.warnings: List[str] = []

    def process_intake(
        self,
        patient_token: str,
        free_text: str,
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if conversation_id:
            return self.agent.continue_conversation(patient_token, free_text)
        return self.agent.start_conversation(patient_token, free_text)

    def validate(self, data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], List[str]]:
        self.errors   = []
        self.warnings = []
        self._validate_required(data)
        self._validate_consents(data)
        self._validate_consistency(data)
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

    def _validate_consistency(self, data: Dict):
        if data.get("sex") == "male" and data.get("pregnancy_status") == "pregnant":
            self.errors.append("Inconsistency: male patient cannot be pregnant.")
        if data.get("age_range") in ("under_5", "5_12") and \
                "hypertension" in data.get("chronic_conditions", []):
            self.warnings.append("Unusual: hypertension in a child — please verify.")

    def _clean(self, data: Dict) -> Dict:
        cleaned = data.copy()
        if "patient_token" not in cleaned:
            cleaned["patient_token"] = f"PT-{uuid.uuid4().hex[:16].upper()}"
        cleaned.setdefault("session_status", "in_progress")
        cleaned.setdefault("channel", "whatsapp")
        return cleaned


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def process_conversational_intake(patient_token: str, text: str) -> Dict[str, Any]:
    return IntakeValidationTool().process_intake(patient_token, text)


def validate_structured_intake(data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], List[str]]:
    return IntakeValidationTool().validate(data)