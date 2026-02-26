"""
ml_models.py — HuggingFace-backed symptom extraction + intelligent question generation
Hybrid State-Machine Edition

LLM responsibilities (what it DOES):
  - Extract free-text symptoms, complaint group, location, demographics
  - Generate empathetic follow-up questions for open-ended fields
  - Understand complex symptom descriptions

LLM responsibilities (what it DOES NOT do):
  - Infer pregnancy from vague replies  → MenuResolver handles this
  - Interpret numeric menu selections   → MenuResolver handles this
  - Override deterministic structured inputs

CHANGE SUMMARY vs previous version:
  - generate_followup_questions: accepts asked_fields_history as Set[str]
    and EXCLUDES those fields from questions even if still in missing_fields
  - STRUCTURED_FIELDS constant imported/referenced so LLM prompts never ask
    for menu-captured fields
  - Question system prompt updated to reflect hybrid architecture
"""

import os
import json
import logging
import re
from typing import List, Dict, Any, Optional, Set
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

# Fields captured via deterministic menus — LLM must never ask for these
_MENU_CAPTURED_FIELDS: Set[str] = {
    "progression_status", "duration", "severity",
    "pregnancy_status", "condition_occurrence", "allergies",
    "on_medication", "consents",
}


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
        "mild/moderate": "moderate", "moderate/severe": "severe",
        "mild/severe": "moderate",   "very severe": "very_severe",
        "very_severe": "very_severe","life-threatening": "very_severe",
        "critical": "very_severe",   "extreme": "very_severe",
    }
    duration_map = {
        "0_1_days": "1_3_days",        "1_3_days": "1_3_days",
        "4_7_days": "4_7_days",        "over_1_week": "more_than_1_week",
        "more_than_1_week": "more_than_1_week",
        "more_than_1_month": "more_than_1_month",
        "today": "6_24_hours",         "just started": "less_than_1_hour",
        "few hours": "1_6_hours",      "yesterday": "6_24_hours",
    }
    age_group_map = {
        "newborn": "newborn", "neonate": "newborn",
        "infant": "infant",   "baby": "infant",
        "toddler": "child_1_5", "child": "child_1_5", "preschool": "child_1_5",
        "kid": "child_6_12",  "school age": "child_6_12",
        "teen": "teen", "adolescent": "teen", "teenager": "teen",
        "adult": "adult", "grown": "adult",
        "elderly": "elderly", "old": "elderly", "senior": "elderly",
        "under 5": "child_1_5", "5-12": "child_6_12",
        "13-17": "teen", "18-30": "adult", "31-50": "adult",
        "51+": "elderly", "over 50": "elderly",
    }
    complaint_group_map = {
        "fever": "fever", "hot": "fever", "temperature": "fever",
        "malaria": "fever", "omusujja": "fever",
        "breathing": "breathing", "cough": "breathing",
        "wheezing": "breathing", "asthma": "breathing", "pneumonia": "breathing",
        "respiratory": "breathing",
        "injury": "injury", "accident": "injury", "fell": "injury",
        "wound": "injury", "broken": "injury", "fracture": "injury",
        "abdominal": "abdominal", "stomach": "abdominal", "belly": "abdominal",
        "vomit": "abdominal", "diarrhea": "abdominal", "nausea": "abdominal",
        "diarrhoea": "abdominal",
        "headache": "headache", "migraine": "headache", "head pain": "headache",
        "chest pain": "chest_pain", "heart pain": "chest_pain",
        "pregnancy": "pregnancy", "pregnant": "pregnancy", "antenatal": "pregnancy",
        "skin": "skin", "rash": "skin", "eczema": "skin",
        "feeding": "feeding", "appetite": "feeding", "eating": "feeding",
        "bleeding": "bleeding", "hemorrhage": "bleeding",
        "mental": "mental_health", "depress": "mental_health",
        "anxiety": "mental_health", "stress": "mental_health",
    }
    progression_map = {
        "sudden": "sudden", "started suddenly": "sudden", "abrupt": "sudden",
        "getting worse": "getting_worse", "worsening": "getting_worse",
        "deteriorating": "getting_worse",
        "staying same": "staying_same", "not changing": "staying_same", "stable": "staying_same",
        "getting better": "getting_better", "improving": "getting_better",
        "comes and goes": "comes_and_goes", "on and off": "comes_and_goes",
        "intermittent": "comes_and_goes", "periodic": "comes_and_goes",
    }
    condition_occurrence_map = {
        "first time": "first", "never had": "first", "new": "first",
        "happened before": "happened_before", "recurring": "happened_before",
        "had before": "happened_before", "again": "happened_before",
        "chronic": "long_term", "long term": "long_term", "always": "long_term",
        "ongoing": "long_term", "persistent": "long_term",
    }
    allergy_status_map = {
        "yes": "yes", "allergic": "yes", "have allergies": "yes",
        "no": "no", "none": "no", "no allergies": "no",
        "not sure": "not_sure", "maybe": "not_sure", "unsure": "not_sure",
    }

    data["severity"]   = severity_map.get((data.get("severity") or "").lower().strip(), data.get("severity"))
    data["duration"]   = duration_map.get((data.get("duration") or "").strip(), data.get("duration"))

    ag = (data.get("age_group") or "").lower().strip()
    if ag: data["age_group"] = age_group_map.get(ag, ag)

    cg = (data.get("complaint_group") or "").lower().strip()
    if cg: data["complaint_group"] = complaint_group_map.get(cg, cg)

    prog = (data.get("progression_status") or "").lower().strip()
    if prog: data["progression_status"] = progression_map.get(prog, prog)

    co = (data.get("condition_occurrence") or "").lower().strip()
    if co: data["condition_occurrence"] = condition_occurrence_map.get(co, co)

    als = (data.get("allergies_status") or "").lower().strip()
    if als: data["allergies_status"] = allergy_status_map.get(als, als)

    return data


# ============================================================================
# SHARED LLM HELPER
# ============================================================================

def _call_llm(system: str, user: str, max_tokens: int = 400) -> Optional[str]:
    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            temperature=0.2,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"LLM call failed: {e}")
        return None


# ============================================================================
# SYMPTOM EXTRACTION — LLM PRIMARY, REGEX FALLBACK
# ============================================================================

_EXTRACTION_SYSTEM = """You are a clinical data extraction engine for a Ugandan medical triage system.
Extract ONLY what is explicitly stated in the patient message.
Return ONLY a raw JSON object with NO explanation, NO markdown, NO code blocks.

JSON format:
{
  "complaint_group": "fever|breathing|injury|abdominal|headache|chest_pain|pregnancy|skin|feeding|bleeding|mental_health|other|null",
  "complaint_group_confidence": 0.0-1.0,
  "primary_symptom": "string or null",
  "secondary_symptoms": [],
  "severity": "mild|moderate|severe|very_severe|null",
  "severity_confidence": 0.0-1.0,
  "severity_reason": "brief reason",
  "duration": "less_than_1_hour|1_6_hours|6_24_hours|1_3_days|4_7_days|more_than_1_week|more_than_1_month|null",
  "duration_confidence": 0.0-1.0,
  "progression_status": "sudden|getting_worse|staying_same|getting_better|comes_and_goes|null",
  "condition_occurrence": "first|happened_before|long_term|null",
  "allergies_status": "yes|no|not_sure|null",
  "allergy_types": [],
  "age_group": "newborn|infant|child_1_5|child_6_12|teen|adult|elderly|null",
  "age_group_confidence": 0.0-1.0,
  "sex": "male|female|other|null",
  "pregnancy_status": "yes|possible|no|not_applicable|null",
  "patient_relation": "self|child|family|other|null",
  "location_raw": "any location mentioned verbatim or null",
  "district": "district name or null",
  "subcounty": "subcounty or null",
  "village": "village/LC1/area or null",
  "landmark": "any landmark or null",
  "location_confidence": 0.0-1.0,
  "red_flags": [],
  "symptom_indicators": {},
  "chronic_conditions": [],
  "on_medication": true|false|null,
  "medications_mentioned": [],
  "consents_given": true|false
}

IMPORTANT RULES:
- Extract only what is EXPLICITLY stated. Do NOT infer from vague replies like "yes", "no", "same".
- pregnancy_status: only extract if patient explicitly mentions pregnancy. "yes"/"no" alone must NOT be mapped here.
- severity/duration/progression: only extract if the patient describes these in their own words.
  If the patient replied to a numbered menu (e.g. "2"), leave these null — the state machine handles them.
- Set confidence to 0.0 if information is NOT mentioned in the text.

complaint_group classification:
- "fever" = omusujja, temperature, hot body, malaria with fever
- "breathing" = cough, wheezing, difficulty breathing, chest tightness
- "abdominal" = stomach pain, vomiting, diarrhea, nausea
- "headache" = head pain, migraine, dizziness
- "chest_pain" = chest pain, heart pain (NOT cough)
- "injury" = cuts, falls, accidents, fractures
- "skin" = rash, itching, skin changes
- "feeding" = poor appetite, weight loss, breastfeeding issues
- "bleeding" = blood loss, hemorrhage
- "pregnancy" = pregnancy concern, antenatal
- "mental_health" = depression, anxiety, stress

red_flags (WHO IMCI danger signs):
"airway_obstruction","severe_breathing_difficulty","chest_indrawing",
"severe_bleeding","signs_of_shock","unconscious","convulsions","confusion",
"unable_to_drink","vomits_everything","lethargic_floppy",
"pregnancy_emergency","severe_abdominal_pain","stroke_signs","chest_pain_cardiac"

symptom_indicators (boolean map):
{"fever":bool,"cough":bool,"breathing_difficulty":bool,"chest_pain":bool,
 "vomiting":bool,"diarrhea":bool,"rash":bool,"fatigue":bool,
 "dizziness":bool,"confusion":bool,"bleeding":bool,"convulsions":bool,
 "headache":bool,"can_drink":bool}

chronic_conditions list:
["diabetes","hypertension","asthma","heart_disease","epilepsy",
 "sickle_cell","hiv_aids","copd","kidney_disease","liver_disease","cancer"]

age_group 7 categories:
newborn=0-2mo; infant=2-12mo; child_1_5=1-5y; child_6_12=6-12y;
teen=13-17y; adult=18-64y; elderly=65+
Luganda: omwana=child, omukadde=elderly, omusajja=man, omukazi=woman
"""


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
    """LLM-first symptom extractor with regex fallback."""

    def extract(self, text: str) -> Dict[str, Any]:
        raw = _call_llm(_EXTRACTION_SYSTEM, f"Patient message: {text}", max_tokens=500)
        if raw:
            result = _extract_json(raw)
            if result:
                return self._build_result(result, text)
        logger.warning(f"LLM extraction failed for: {text[:100]}")
        return self._regex_fallback(text)

    def extract_with_history(self, text: str, conversation_history: List[Dict]) -> Dict[str, Any]:
        history_text = "\n".join([
            f"{t['role'].upper()}: {t['content']}"
            for t in conversation_history[-8:]
        ])
        prompt = (
            f"Full conversation history:\n{history_text}\n\n"
            f"Latest patient message: {text}\n\n"
            "Extract from the LATEST message, use history only to resolve ambiguities."
        )
        raw = _call_llm(_EXTRACTION_SYSTEM, prompt, max_tokens=500)
        if raw:
            result = _extract_json(raw)
            if result:
                return self._build_result(result, text)
        return self._regex_fallback(text)

    def _build_result(self, result: Dict, text: str) -> Dict[str, Any]:
        symptoms = []
        if result.get("primary_symptom"):
            symptoms.append(result["primary_symptom"])
        symptoms.extend(result.get("secondary_symptoms", []))

        return {
            "symptoms":                   symptoms,
            "severity":                   result.get("severity"),
            "severity_confidence":        result.get("severity_confidence", 0.0),
            "severity_reason":            result.get("severity_reason", ""),
            "duration":                   result.get("duration"),
            "duration_confidence":        result.get("duration_confidence", 0.0),
            "complaint_group":            result.get("complaint_group"),
            "complaint_group_confidence": result.get("complaint_group_confidence", 0.0),
            "age_group":                  result.get("age_group"),
            "age_group_confidence":       result.get("age_group_confidence", 0.0),
            "sex":                        result.get("sex"),
            "pregnancy_status":           result.get("pregnancy_status"),
            "patient_relation":           result.get("patient_relation"),
            "location_raw":               result.get("location_raw"),
            "district":                   result.get("district"),
            "subcounty":                  result.get("subcounty"),
            "village":                    result.get("village"),
            "landmark":                   result.get("landmark"),
            "location_confidence":        result.get("location_confidence", 0.0),
            "progression_status":         result.get("progression_status"),
            "condition_occurrence":       result.get("condition_occurrence"),
            "allergies_status":           result.get("allergies_status"),
            "allergy_types":              result.get("allergy_types", []),
            "chronic_conditions":         result.get("chronic_conditions", []),
            "on_medication":              result.get("on_medication"),
            "red_flags":                  result.get("red_flags", []),
            "symptom_indicators":         result.get("symptom_indicators", {}),
            "medications_mentioned":      result.get("medications_mentioned", []),
            "consents_given":             result.get("consents_given", False),
            "confidence":                 result.get("complaint_group_confidence", 0.85),
        }

    def _regex_fallback(self, text: str) -> Dict[str, Any]:
        t = text.lower()

        complaint_scores: Dict[str, float] = {}
        complaint_patterns = {
            "fever":        [(r"\b(fever|omusujja|hot body|temperature|malaria)\b", 1.0),
                             (r"\b(high temp|warm|feeling hot)\b", 0.7)],
            "breathing":    [(r"\b(can'?t breathe|difficulty breathing|shortness of breath)\b", 1.0),
                             (r"\b(cough|wheezing|asthma|pneumonia|chest tight)\b", 0.9)],
            "abdominal":    [(r"\b(stomach|abdominal|belly|lubuto|epigastric)\b", 1.0),
                             (r"\b(vomit|diarrhea|diarrhoea|nausea)\b", 0.9)],
            "headache":     [(r"\b(headache|migraine|head pain|omutwe)\b", 1.0),
                             (r"\b(dizziness|dizzy|lightheaded)\b", 0.7)],
            "injury":       [(r"\b(injur|accident|fell|broken|wound|cut|fracture)\b", 1.0)],
            "chest_pain":   [(r"\b(chest pain|heart pain|kifuba)\b", 1.0)],
            "pregnancy":    [(r"\b(pregnant|pregnancy|omuzigo|antenatal)\b", 1.0)],
            "skin":         [(r"\b(skin|rash|hives|eczema|olususu)\b", 1.0)],
            "bleeding":     [(r"\b(bleed|hemorrhage)\b", 1.0)],
            "mental_health":[(r"\b(depress|anxiety|stress|mental health|suicidal)\b", 1.0)],
        }
        for group, patterns in complaint_patterns.items():
            score = 0.0
            for pattern, weight in patterns:
                if re.search(pattern, t):
                    score = max(score, weight)
            if score > 0:
                complaint_scores[group] = score

        complaint_group      = max(complaint_scores, key=complaint_scores.get) if complaint_scores else "other"
        complaint_confidence = complaint_scores.get(complaint_group, 0.5)

        severity, severity_confidence = self._regex_severity(t)
        duration    = self._regex_duration(t)
        age_group, age_confidence = self._regex_age_group(t)

        sex = None
        if re.search(r"\b(male|man|boy|omusajja)\b", t):    sex = "male"
        elif re.search(r"\b(female|woman|girl|omukazi)\b", t): sex = "female"

        red_flags = self._regex_red_flags(t)

        condition_occurrence = None
        if re.search(r"\b(chronic|long.?term|for (months|years)|ongoing|persistent)\b", t):
            condition_occurrence = "long_term"
        elif re.search(r"\b(happened before|again|recurring|came back)\b", t):
            condition_occurrence = "happened_before"
        elif re.search(r"\b(first time|never had|new symptom|just started)\b", t):
            condition_occurrence = "first"

        allergies_status = None
        allergy_types    = []
        if re.search(r"\b(no allerg|not allergic|no known allerg)\b", t):
            allergies_status = "no"
        elif re.search(r"\b(allerg|allergic|sensitive to)\b", t):
            allergies_status = "yes"
            if re.search(r"\b(drug|medicine|medication|antibiotic)\b", t): allergy_types.append("medication")
            if re.search(r"\b(food|nuts|peanut|dairy|egg|shellfish)\b", t): allergy_types.append("food")
            if re.search(r"\b(dust|pollen|pet|environmental|bee)\b", t): allergy_types.append("environmental")

        on_medication = None
        if re.search(r"\b(taking medication|on medication|taking tablets|taking medicine)\b", t):
            on_medication = True
        elif re.search(r"\b(no medication|not taking|no medicine)\b", t):
            on_medication = False

        chronic_conditions = []
        for cond, pattern in {
            "diabetes": r"\b(diabetes|sugar)\b", "hypertension": r"\b(hypertension|high blood pressure)\b",
            "asthma": r"\b(asthma)\b", "epilepsy": r"\b(epilepsy)\b",
            "sickle_cell": r"\b(sickle cell)\b", "hiv_aids": r"\b(hiv|aids|slim)\b",
        }.items():
            if re.search(pattern, t): chronic_conditions.append(cond)

        return {
            "symptoms":                   [],
            "severity":                   severity,
            "severity_confidence":        severity_confidence,
            "severity_reason":            "regex fallback",
            "duration":                   duration,
            "duration_confidence":        0.6 if duration else 0.0,
            "complaint_group":            complaint_group,
            "complaint_group_confidence": complaint_confidence,
            "age_group":                  age_group,
            "age_group_confidence":       age_confidence,
            "sex":                        sex,
            "pregnancy_status":           None,
            "patient_relation":           None,
            "location_raw":               None,
            "district":                   None,
            "subcounty":                  None,
            "village":                    None,
            "landmark":                   None,
            "location_confidence":        0.0,
            "progression_status":         None,
            "condition_occurrence":       condition_occurrence,
            "allergies_status":           allergies_status,
            "allergy_types":              allergy_types,
            "chronic_conditions":         chronic_conditions,
            "on_medication":              on_medication,
            "red_flags":                  red_flags,
            "symptom_indicators":         {},
            "medications_mentioned":      [],
            "consents_given":             False,
            "confidence":                 0.5,
        }

    def _regex_severity(self, t: str):
        if re.search(r"\b(can'?t move|can'?t talk|unconscious|dying)\b", t):
            return "very_severe", 0.9
        if re.search(r"\b(very severe|unbearable|worst|extreme|emergency)\b", t):
            return "very_severe", 0.85
        if re.search(r"\b(severe|very bad|terrible|cannot function)\b", t):
            return "severe", 0.8
        has_escalating = bool(re.search(r"\b(fever|headache|cough|pain)\b", t))
        duration = self._regex_duration(t)
        if has_escalating and duration in ["1_3_days", "4_7_days", "more_than_1_week", "more_than_1_month"]:
            return "moderate", 0.75
        if re.search(r"\b(moderate|medium|somewhat|some difficulty)\b", t): return "moderate", 0.75
        if re.search(r"\b(mild|slight|a little|minor|kitono)\b", t):        return "mild", 0.75
        if re.search(r"\b(high fever|very hot|burning up|39|40|41)\b", t):  return "moderate", 0.7
        return None, 0.0

    def _regex_duration(self, t: str) -> Optional[str]:
        if re.search(r"\b(few minutes|just started|just now|minutes ago)\b", t): return "less_than_1_hour"
        if re.search(r"\b(few hours|hours ago|[1-6]\s*hours?)\b", t):            return "1_6_hours"
        if re.search(r"\b(today|leero|this morning|this evening|yesterday)\b", t):return "6_24_hours"
        if re.search(r"\b([1-3]\s*(days?)|jjo|two days|three days)\b", t):        return "1_3_days"
        if re.search(r"\b([4-7]\s*(days?)|four|five|six|seven\s*days?)\b", t):    return "4_7_days"
        if re.search(r"\b(week|wiiki|7\s*days?)\b", t):                           return "more_than_1_week"
        if re.search(r"\b(month|mwezi|weeks?)\b", t):                             return "more_than_1_month"
        return None

    def _regex_age_group(self, t: str):
        if re.search(r"\b(newborn|neonate|0\s*months?|1\s*month?|2\s*months?)\b", t): return "newborn", 0.9
        if re.search(r"\b(infant|baby|omwana omuto|[3-9]\s*months?|1[0-2]\s*months?)\b", t): return "infant", 0.9
        if re.search(r"\b(omwana|toddler|[1-5]\s*years?|year\s*old)\b", t):  return "child_1_5", 0.8
        if re.search(r"\b([6-9]|1[0-2])\s*years?|school.?age\b", t):         return "child_6_12", 0.8
        if re.search(r"\b(teen|adolescent|1[3-7]\s*years?)\b", t):            return "teen", 0.85
        if re.search(r"\b(omukadde|elderly|senior|old person|6[5-9]|[7-9]\d)\s*years?\b", t): return "elderly", 0.85
        if re.search(r"\b(adult|musajja|omukazi|grown|[2-5]\d\s*years?|1[8-9]\s*years?|60\s*years?)\b", t):
            return "adult", 0.75
        age_match = re.search(r"\b(\d{1,3})\s*(years?|yr)\b", t)
        if age_match:
            age = int(age_match.group(1))
            if age <= 2:  return "newborn", 0.8
            if age <= 5:  return "child_1_5", 0.8
            if age <= 12: return "child_6_12", 0.8
            if age <= 17: return "teen", 0.8
            if age <= 64: return "adult", 0.8
            return "elderly", 0.8
        return None, 0.0

    def _regex_red_flags(self, t: str) -> List[str]:
        flags = []
        patterns = {
            "severe_breathing_difficulty": r"\b(can'?t breathe|cannot breathe|struggling to breathe|gasping|no air)\b",
            "airway_obstruction":          r"\b(choking|blocked airway)\b",
            "unconscious":                 r"\b(unconscious|passed out|not waking|unresponsive|fainted)\b",
            "convulsions":                 r"\b(convulsion|seizure|fitting|kiguguumizi)\b",
            "severe_bleeding":             r"\b(heavy bleeding|bleeding a lot|hemorrhage|blood everywhere)\b",
            "signs_of_shock":              r"\b(very pale|cold hands|collapsed|shock|cold sweat)\b",
            "lethargic_floppy":            r"\b(floppy|very sleepy|difficult to wake|limp|listless)\b",
            "unable_to_drink":             r"\b(can'?t drink|cannot swallow|refuses to drink|not drinking)\b",
            "confusion":                   r"\b(confused|disoriented|not making sense|doesn'?t know where)\b",
        }
        for flag, pattern in patterns.items():
            if re.search(pattern, t):
                flags.append(flag)
        return flags

    def extract_symptoms(self, text: str) -> List[ExtractedSymptom]:
        result = self.extract(text)
        return [
            ExtractedSymptom(symptom=s, confidence=0.85, source_text=text)
            for s in result.get("symptoms", [])
        ]


# ============================================================================
# INTELLIGENT QUESTION GENERATION — FREE-TEXT FIELDS ONLY
# ============================================================================

_QUESTION_SYSTEM = """You are HarakaCare, a friendly WhatsApp medical triage assistant in Uganda.

ARCHITECTURE NOTE: This system uses a hybrid state machine.
- Structured fields (progression, duration, severity, pregnancy, condition occurrence,
  allergies, medication, consent) are captured via numbered menus BEFORE this function is called.
- You only ask about FREE-TEXT fields: complaint description, location, age, sex,
  and chronic condition details.
- NEVER ask about fields in "Already captured via menus" or "Already asked about".

RULES:
1. Ask for AT MOST 2 free-text fields per message.
2. Acknowledge the patient's last message briefly (1 sentence, empathetic).
3. Keep messages under 60 words — WhatsApp style.
4. No bullet points, lists, or markdown.
5. Warm, conversational English. Simple Luganda phrases welcome.
6. If ANY emergency signs are present → tell them to seek immediate care NOW.

FREE-TEXT fields you may ask about:
- complaint_group / complaint_text (describe their main symptom)
- age_group (patient's age)
- sex (male or female)
- location / district (which district in Uganda)
- village (specific village or LC1)
- chronic_conditions detail (what specific conditions)
"""


def generate_followup_questions(
    missing_fields: List[str],
    conversation_history: List[Dict[str, str]],
    extracted_so_far: Dict[str, Any],
    intent: str = "routine",
    context: Optional[Dict] = None,
    asked_fields_history: Optional[Set[str]] = None,
) -> str:
    context              = context or {}
    asked_fields_history = asked_fields_history or set()

    # Emergency override
    if context.get("red_flags_detected") or intent == "emergency":
        red_flag_list = list((extracted_so_far.get("red_flag_indicators") or {}).keys())
        flag_str = ", ".join(red_flag_list[:2]) if red_flag_list else "danger signs"
        return (
            f"🚨 EMERGENCY: I can see serious warning signs ({flag_str}). "
            "Please stop and go to the nearest health facility RIGHT NOW or call 0800-100-066. "
            "Do not wait — your life may be at risk."
        )

    # Exclude menu-captured fields and already-asked fields
    free_text_candidates = [
        f for f in missing_fields
        if f not in _MENU_CAPTURED_FIELDS and f not in asked_fields_history
    ]

    # If nothing left to ask via LLM, return empty (caller handles this)
    if not free_text_candidates:
        return ""

    priority_order = [
        "complaint_group", "age_group", "sex", "location", "village", "chronic_conditions",
    ]
    free_text_candidates.sort(
        key=lambda f: priority_order.index(f) if f in priority_order else 99
    )
    fields_to_ask = free_text_candidates[:2]

    recent = conversation_history[-6:]
    history_text = "\n".join(f"{t['role'].upper()}: {t['content']}" for t in recent)

    ei = extracted_so_far
    known_parts = []
    if ei.get("complaint_group"):      known_parts.append(f"complaint={ei['complaint_group']}")
    if ei.get("age_group"):            known_parts.append(f"age_group={ei['age_group']}")
    if ei.get("sex"):                  known_parts.append(f"sex={ei['sex']}")
    if ei.get("severity"):             known_parts.append(f"severity={ei['severity']}")
    if ei.get("duration"):             known_parts.append(f"duration={ei['duration']}")
    if ei.get("progression_status"):   known_parts.append(f"progression={ei['progression_status']}")
    if ei.get("condition_occurrence"): known_parts.append(f"occurrence={ei['condition_occurrence']}")
    if ei.get("district") or ei.get("location"):
        known_parts.append(f"district={ei.get('district') or ei.get('location')}")
    if ei.get("village"):              known_parts.append(f"village={ei['village']}")
    if ei.get("chronic_conditions"):   known_parts.append(f"chronic={ei['chronic_conditions']}")
    if ei.get("on_medication") is not None: known_parts.append(f"on_medication={ei['on_medication']}")
    if ei.get("allergies_status"):     known_parts.append(f"allergies={ei['allergies_status']}")
    if ei.get("pregnancy_status"):     known_parts.append(f"pregnancy={ei['pregnancy_status']}")

    known_summary  = ", ".join(known_parts) if known_parts else "nothing yet"
    already_asked  = ", ".join(asked_fields_history) if asked_fields_history else "none"
    menu_captured  = ", ".join(sorted(_MENU_CAPTURED_FIELDS))

    field_labels = {
        "complaint_group":    "what the main problem or symptom is",
        "age_group":          "the patient's age group",
        "sex":                "whether the patient is male or female",
        "location":           "which district they are in Uganda",
        "village":            "the specific village or LC1 they are in",
        "chronic_conditions": "which specific long-term health conditions they have",
    }

    missing_readable = [field_labels.get(f, f.replace("_", " ")) for f in fields_to_ask]
    missing_str      = " and ".join(missing_readable)

    user_prompt = f"""Recent conversation:
{history_text}

What we already know: {known_summary}
Already asked about: {already_asked}
Already captured via menus (DO NOT ask): {menu_captured}
Intent: {intent}
Free-text fields still needed: {missing_str}

Write ONE WhatsApp reply that:
1. Briefly acknowledges the last message (empathy if needed, 1 sentence max)
2. Asks ONLY about the free-text fields listed under "Free-text fields still needed"
3. Never asks about anything in "What we already know", "Already asked about", or "Already captured via menus"
"""

    raw = _call_llm(_QUESTION_SYSTEM, user_prompt, max_tokens=160)

    if not raw:
        fallback_map = {
            "complaint_group":    "What is the main problem? (fever / breathing / stomach pain / headache / injury / other?)",
            "age_group":          "What is the patient's age? (Newborn / Infant / Child / Teen / Adult / Elderly?)",
            "sex":                "Is the patient male or female?",
            "location":           "Which district in Uganda are you in?",
            "village":            "What is the name of your village or LC1?",
            "chronic_conditions": "Please describe your long-term health conditions.",
        }
        parts = [fallback_map.get(f, f"Please tell me: {f.replace('_', ' ')}") for f in fields_to_ask]
        return "Thank you for sharing. " + " ".join(parts)

    return raw


# ============================================================================
# EMERGENCY DETECTION
# ============================================================================

def detect_emergency_in_text(text: str) -> Dict[str, Any]:
    t = text.lower()
    emergency_patterns = {
        "severe_breathing_difficulty": [r"\b(can'?t breathe|cannot breathe|struggling to breathe|gasping|no air|choking)\b"],
        "unconscious":                 [r"\b(unconscious|passed out|not waking|unresponsive|fainted|collapsed)\b"],
        "convulsions":                 [r"\b(convulsion|seizure|fitting|kiguguumizi|shaking all over)\b"],
        "severe_bleeding":             [r"\b(heavy bleeding|bleeding a lot|hemorrhage|blood everywhere|can'?t stop bleeding)\b"],
        "signs_of_shock":              [r"\b(very pale|cold hands|collapsed|cold sweat|faint)\b"],
        "cardiac_emergency":           [r"\b(chest pain|heart attack|heart pain|crushing chest)\b"],
        "stroke_signs":                [r"\b(stroke|face drooping|arm weakness|speech difficulty|sudden numbness)\b"],
        "lethargic_infant":            [r"\b(floppy|very sleepy|difficult to wake|limp baby|listless baby)\b"],
    }
    detected = {}
    for flag, patterns in emergency_patterns.items():
        for pattern in patterns:
            if re.search(pattern, t):
                detected[flag] = True
                break

    requires_immediate = any(flag in detected for flag in [
        "severe_breathing_difficulty", "unconscious", "convulsions",
        "cardiac_emergency", "stroke_signs",
    ])
    return {
        "has_emergency":      len(detected) > 0,
        "detected_flags":     detected,
        "requires_immediate": requires_immediate,
    }


# ============================================================================
# SEVERITY ESCALATION
# ============================================================================

def escalate_severity(
    base_severity: Optional[str],
    complaint_group: Optional[str],
    duration: Optional[str],
    age_group: Optional[str],
    red_flags: List[str],
) -> str:
    severity_order = ["mild", "moderate", "severe", "very_severe"]

    def upgrade(current: Optional[str], target: str) -> str:
        if not current: return target
        ci = severity_order.index(current) if current in severity_order else 0
        ti = severity_order.index(target)  if target  in severity_order else 0
        return severity_order[max(ci, ti)]

    result = base_severity or "mild"
    if red_flags: return "very_severe"
    if age_group in ["newborn", "infant"]: result = upgrade(result, "severe")
    if age_group == "elderly" and complaint_group in ["chest_pain", "headache", "breathing"]:
        result = upgrade(result, "moderate")
    if complaint_group in ["fever", "headache", "abdominal", "chest_pain"]:
        if duration in ["4_7_days", "more_than_1_week", "more_than_1_month"]:
            result = upgrade(result, "moderate")
    if complaint_group == "breathing": result = upgrade(result, "moderate")
    return result


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def extract_from_text(text: str) -> Dict[str, Any]:
    return APISymptomExtractor().extract(text)


def generate_question(
    missing_fields: List[str],
    history: List[Dict[str, str]],
    extracted: Dict[str, Any],
    intent: str = "routine",
    asked_fields: Optional[Set[str]] = None,
) -> str:
    return generate_followup_questions(
        missing_fields, history, extracted, intent,
        asked_fields_history=asked_fields,
    )