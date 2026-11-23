"""
OpenAI NLP Symptom Extraction - Phase 3 AI Upgrade

Extracts symptoms, duration, severity, and other clinical details from
natural language patient input using OpenAI.

SAFETY BOUNDARIES:
- Used ONLY for symptom extraction from free text.
- Does NOT diagnose, predict risk, or make medical decisions.
- The deterministic Clinical Safety Engine always has final authority.
- Patient consent is required before sending any data to OpenAI.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
    from openai import APIError, AuthenticationError, RateLimitError, BadRequestError, APIConnectionError
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class OpenAISymptomExtractor:
    """
    Extracts symptoms from patient free-text using OpenAI.
    
    This is an EXPERIMENTAL prototype. Results are used to populate
    structured fields for the rule-based risk classifier and safety engine.
    The LLM never makes risk predictions or diagnoses.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = os.getenv("OPENAI_MODEL", model)
        self.enabled = bool(self.api_key) and OPENAI_AVAILABLE

        if self.enabled:
            self.client = OpenAI(api_key=self.api_key)
            logger.info(f"OpenAI NLP extractor initialized (model: {self.model})")
        else:
            self.client = None
            logger.warning("OpenAI NLP disabled - no API key or package missing")

    def extract_symptoms(self, complaint_text: str, consent_given: bool = False) -> Dict[str, Any]:
        """
        Extract structured symptom information from free text.
        
        Args:
            complaint_text: Patient's natural language description
            consent_given: Whether patient consented to AI processing
            
        Returns:
            Dict with extracted fields. Always returns safe defaults on failure.
        """
        result = {
            "complaint_group": None,
            "primary_symptom": None,
            "secondary_symptoms": [],
            "duration": None,
            "severity": None,
            "progression": None,
            "red_flags": [],
            "risk_modifiers": {},
            "confidence": 0.0,
            "source": "none",
            "error": None,
        }

        if not consent_given:
            result["error"] = "Patient consent not given for AI processing"
            return result

        if not self.enabled:
            result["error"] = "OpenAI NLP not configured"
            return result

        if not complaint_text or not complaint_text.strip():
            result["error"] = "No complaint text provided"
            return result

        system_prompt = """You are a medical symptom extraction assistant. Your ONLY job is to extract symptoms from patient text. 
You must NOT diagnose, predict risk, or give medical advice.
You must NOT suggest treatments or medications.
You must NOT override emergency warnings.

Extract the following from the patient's text and return ONLY valid JSON:
- complaint_group: one of [fever, breathing, chest_pain, bleeding, headache, abdominal, injury, pregnancy, skin, feeding, mental_health, other]
- primary_symptom: the main symptom
- secondary_symptoms: list of other symptoms mentioned
- duration: one of [less_than_1_hour, 1_6_hours, 6_24_hours, 1_3_days, 4_7_days, more_than_1_week, more_than_1_month]
- severity: one of [mild, moderate, severe, very_severe]
- progression: one of [sudden, getting_worse, staying_same, getting_better, comes_and_goes]
- red_flags: list of emergency signs from [airway_obstruction, severe_breathing_difficulty, severe_bleeding, unconscious, convulsions, confusion, stroke_symptoms, pregnancy_emergency, severe_pain]
- risk_modifiers: dict with keys [is_pregnant, has_chronic_conditions, on_medication, is_newborn, is_elderly, is_immunocompromised]
- confidence: float 0.0 to 1.0

If you cannot determine a field, set it to null or empty list. Do not invent information."""

        user_prompt = f'Patient says: "{complaint_text}"\n\nExtract symptoms as JSON only.'

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=500,
            )

            content = (response.choices[0].message.content or "").strip()
            extracted = json.loads(content)

            allowed_keys = {
                "complaint_group", "primary_symptom", "secondary_symptoms",
                "duration", "severity", "progression", "red_flags",
                "risk_modifiers", "confidence"
            }
            result = {k: extracted.get(k) for k in allowed_keys if k in extracted}
            result["source"] = "openai"
            result["error"] = None

            if not isinstance(result.get("secondary_symptoms"), list):
                result["secondary_symptoms"] = []
            if not isinstance(result.get("red_flags"), list):
                result["red_flags"] = []
            if not isinstance(result.get("risk_modifiers"), dict):
                result["risk_modifiers"] = {}

            logger.info(f"OpenAI extraction completed: {result.get('complaint_group')}")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"OpenAI returned invalid JSON: {e}")
            result["error"] = "Failed to parse AI response"
            return result
        except AuthenticationError:
            logger.error("OpenAI authentication failed")
            result["error"] = "AI service authentication failed"
            return result
        except RateLimitError:
            logger.error("OpenAI rate limit exceeded")
            result["error"] = "AI service rate limit exceeded"
            return result
        except BadRequestError as e:
            logger.error(f"OpenAI bad request error: {e}")
            result["error"] = "AI service request error"
            return result
        except APIConnectionError as e:
            logger.error(f"OpenAI connection error: {e}")
            result["error"] = "AI service connection error"
            return result
        except APIError as e:
            logger.error(f"OpenAI error: {e}")
            result["error"] = f"AI service error: {str(e)}"
            return result
        except Exception as e:
            logger.error(f"Unexpected error in OpenAI extraction: {e}")
            result["error"] = "AI extraction failed"
            return result


# Global instance
openai_extractor = OpenAISymptomExtractor()
