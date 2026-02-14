"""
ml_models.py — HuggingFace-backed symptom extraction + intelligent question generation
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

load_dotenv()
logger = logging.getLogger(__name__)

HF_TOKEN = os.getenv("HF_TOKEN")

client = InferenceClient(
    model="Qwen/Qwen2.5-7B-Instruct",
    token=HF_TOKEN
)


# ============================================================================
# DATA STRUCTURE
# ============================================================================

@dataclass
class ExtractedSymptom:
    symptom: str
    confidence: float
    source_text: str


# ============================================================================
# NORMALIZATION
# ============================================================================

def normalize_result(data: dict) -> dict:
    severity_map = {
        "mild/moderate":   "moderate",
        "moderate/severe": "severe",
        "mild/severe":     "moderate",
        "very severe":     "very_severe",
        "very_severe":     "very_severe",
    }
    valid_durations = {
        "0_1_days", "1_3_days", "4_7_days",
        "over_1_week", "more_than_1_week",
        "more_than_1_month", "today",
    }
    severity = data.get("severity", "").lower().strip()
    data["severity"] = severity_map.get(severity, severity)

    duration = data.get("duration", "").strip()
    data["duration"] = duration if duration in valid_durations else duration
    return data


# ============================================================================
# SHARED LLM HELPER
# ============================================================================

def _call_llm(system: str, user: str, max_tokens: int = 300) -> Optional[str]:
    """Single LLM call — returns raw text or None on failure."""
    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            temperature=0.3,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"LLM call failed: {e}")
        return None


# ============================================================================
# SYMPTOM EXTRACTION
# ============================================================================

_EXTRACTION_SYSTEM = """You are a medical triage assistant.
Extract clinical data from the patient message.
Return ONLY a raw JSON object. No explanation. No markdown. No code blocks.

Use this exact format:
{
  "primary_symptom": "",
  "secondary_symptoms": [],
  "severity": "mild/moderate/severe/very_severe",
  "duration": "0_1_days/1_3_days/4_7_days/over_1_week"
}"""


def _extract_json(text: str) -> Optional[Dict]:
    try:
        return normalize_result(json.loads(text))
    except json.JSONDecodeError:
        try:
            start = text.index("{")
            end   = text.rindex("}") + 1
            return normalize_result(json.loads(text[start:end]))
        except Exception:
            return None


class APISymptomExtractor:
    """
    HuggingFace-backed extractor.
    Implements the same interface the ConversationalIntakeAgent expects.
    """

    def extract(self, text: str) -> Dict[str, Any]:
        raw = _call_llm(_EXTRACTION_SYSTEM, f"Patient message: {text}", max_tokens=200)
        if not raw:
            return {"symptoms": [], "severity": None, "duration": None, "confidence": 0.0}

        result = _extract_json(raw)
        if not result:
            logger.warning(f"Could not parse extraction JSON: {raw[:200]}")
            return {"symptoms": [], "severity": None, "duration": None, "confidence": 0.0}

        symptoms = []
        if result.get("primary_symptom"):
            symptoms.append(result["primary_symptom"])
        symptoms.extend(result.get("secondary_symptoms", []))

        return {
            "symptoms":   symptoms,
            "severity":   result.get("severity"),
            "duration":   result.get("duration"),
            "confidence": 0.85,
        }

    def extract_symptoms(self, text: str) -> List[ExtractedSymptom]:
        raw = _call_llm(_EXTRACTION_SYSTEM, f"Patient message: {text}", max_tokens=200)
        if not raw:
            return []

        result = _extract_json(raw)
        if not result:
            return []

        out: List[ExtractedSymptom] = []
        if result.get("primary_symptom"):
            out.append(ExtractedSymptom(
                symptom=result["primary_symptom"],
                confidence=0.9,
                source_text=text,
            ))
        for sym in result.get("secondary_symptoms", []):
            out.append(ExtractedSymptom(
                symptom=sym,
                confidence=0.75,
                source_text=text,
            ))
        return out


# ============================================================================
# INTELLIGENT QUESTION GENERATION
# ============================================================================

_QUESTION_SYSTEM = """You are HarakaCare, a friendly WhatsApp medical triage assistant in Uganda.

Your job is to ask the patient for missing information needed to complete their triage.

Rules:
- Write in a warm, conversational WhatsApp style — short, clear, human
- Ask for at most 2 missing pieces of information per message
- Always acknowledge what the patient just said before asking
- If the patient seems worried or in pain, show empathy first
- When asking about age, offer clear options (Under 5 / 5-12 / 13-17 / 18-30 / 31-50 / 51+)
- When asking about severity, offer: mild / moderate / severe / very severe
- When asking about duration, give natural examples (today / a few days / about a week / over a month)
- When asking about location, ask for their district
- When asking about consent, briefly explain why it is needed
- Do NOT repeat questions that have already been answered
- Do NOT output JSON, lists, or bullet points — write as a natural chat message
- Keep the entire message under 60 words"""


def generate_followup_questions(
    missing_fields: List[str],
    conversation_history: List[Dict[str, str]],
    extracted_so_far: Dict[str, Any],
    intent: str = "routine",
) -> str:
    """
    Use the LLM to generate a context-aware follow-up message for the patient.

    Args:
        missing_fields:        fields still needed
        conversation_history:  list of {"role": "patient"/"agent", "content": "..."}
        extracted_so_far:      dict of what has been collected already
        intent:                detected intent (emergency / follow_up / routine)

    Returns:
        A natural-language WhatsApp message string.
    """
    # Build a readable summary of what we already know
    known_parts = []
    ei = extracted_so_far
    if ei.get("primary_symptom"):
        known_parts.append(f"symptom: {ei['primary_symptom']}")
    if ei.get("severity"):
        known_parts.append(f"severity: {ei['severity']}")
    if ei.get("duration"):
        known_parts.append(f"duration: {ei['duration']}")
    if ei.get("age_range"):
        known_parts.append(f"age: {ei['age_range']}")
    if ei.get("location"):
        known_parts.append(f"location: {ei['location']}")

    known_summary = ", ".join(known_parts) if known_parts else "nothing yet"

    # Last patient message for context
    last_patient_msg = ""
    for turn in reversed(conversation_history):
        if turn.get("role") == "patient":
            last_patient_msg = turn.get("content", "")
            break

    # Readable field names for the prompt
    field_labels = {
        "age_range":          "age range",
        "severity":           "symptom severity",
        "duration":           "how long they have had the symptoms",
        "location":           "district/location",
        "condition_occurrence": "whether this has happened before",
        "pregnancy_status":   "pregnancy status",
        "consents":           "consent to triage and data sharing",
        "sex":                "sex (male/female)",
    }
    missing_readable = [field_labels.get(f, f.replace("_", " ")) for f in missing_fields[:2]]
    missing_str      = " and ".join(missing_readable)

    user_prompt = f"""
Patient's last message: "{last_patient_msg}"

What we already know: {known_summary}
Intent detected: {intent}
Still missing: {missing_str}

Write a single WhatsApp reply that:
1. Briefly acknowledges their last message (1 sentence, show empathy if needed)
2. Asks only for the missing information above
"""

    raw = _call_llm(_QUESTION_SYSTEM, user_prompt, max_tokens=120)

    # Fallback to a sensible static message if LLM fails
    if not raw:
        fallback_map = {
            "age_range":            "Could you tell me your age? (Under 5 / 5-12 / 13-17 / 18-30 / 31-50 / 51+)",
            "severity":             "How severe are your symptoms? (mild / moderate / severe / very severe)",
            "duration":             "How long have you had these symptoms?",
            "location":             "Which district are you located in?",
            "condition_occurrence": "Is this the first time you have had these symptoms?",
            "pregnancy_status":     "Are you currently pregnant? (yes / no)",
            "consents":             "Do you consent to medical triage and follow-up messages? (yes / no)",
            "sex":                  "Are you male or female?",
        }
        parts = [fallback_map.get(f, f"Please provide: {f.replace('_', ' ')}") for f in missing_fields[:2]]
        return " ".join(parts)

    return raw