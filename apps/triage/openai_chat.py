"""
OpenAI Conversational Triage - Intelligent Chat Interface
SAFETY: Extracts symptoms only. Never diagnoses. Safety engine always overrides.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
    from openai import APIError, AuthenticationError, RateLimitError, BadRequestError, APIConnectionError
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class ConversationalTriageAI:
    """
    Intelligent conversational triage using OpenAI.
    Understands natural language, maintains context, asks smart follow-ups.
    NEVER diagnoses or predicts risk - that's the safety engine's job.
    """

    SYSTEM_PROMPT = """You are HarakaCare, a compassionate healthcare triage assistant for patients in Uganda.

CRITICAL RULES - NEVER BREAK THESE:
1. You are NOT a doctor. You do NOT diagnose diseases. You do NOT prescribe medication.
2. You only collect symptom information and ask clarifying questions.
3. If you detect emergency signs (chest pain, difficulty breathing, severe bleeding, unconsciousness, stroke symptoms), IMMEDIATELY tell them to seek emergency care and stop asking routine questions.
4. Always be kind, clear, and simple. Use short sentences.
5. Ask ONE question at a time.
6. Support English initially. If they speak another language, respond in English but simply.

CONVERSATION FLOW:
1. Welcome + disclaimer (not a doctor)
2. Get consent
3. Ask: "What symptoms are you experiencing?" (natural language)
4. Extract: symptoms, duration, severity, age, sex, location
5. Ask 2-3 smart follow-ups based on what they said
6. Check for red flags
7. Give clear care-seeking guidance
8. Provide case reference number

NEVER say "You have [disease]." NEVER say "Take [medication]."
ALWAYS say "Please see a healthcare worker" or "Go to the hospital" for emergencies.
"""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = os.getenv("OPENAI_MODEL", model)
        self.enabled = bool(self.api_key) and OPENAI_AVAILABLE
        if self.enabled:
            self.client = OpenAI(api_key=self.api_key)
            logger.info(f"OpenAI Conversational Triage initialized (model: {self.model})")
        else:
            self.client = None
            logger.warning("OpenAI Conversational Triage disabled - no API key or package missing")

    def start_conversation(self) -> Dict[str, Any]:
        """Start a new triage conversation."""
        return {
            "message": (
                "🏥 Welcome to HarakaCare Medical Triage!\n\n"
                "I'm here to help assess your health concerns. "
                "This takes about 2-3 minutes.\n\n"
                "⚠️ IMPORTANT: I am an AI assistant, NOT a doctor. "
                "I cannot diagnose diseases or prescribe medicine. "
                "For emergencies, go to the nearest hospital immediately.\n\n"
                "Please describe your main symptoms or health issue to begin:"
            ),
            "stage": "symptoms",
            "patient_data": {},
            "conversation_id": None,
            "needs_consent": False,
        }

    def process_message(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process user message and return AI response.
        context contains: stage, patient_data, conversation_id, etc.
        """
        if not user_input or not user_input.strip():
            return {
                "message": "I didn't catch that. Could you please describe your symptoms?",
                "stage": context.get("stage", "symptoms"),
                "patient_data": context.get("patient_data", {}),
            }

        patient_data = context.get("patient_data", {})
        stage = context.get("stage", "symptoms")

        # If OpenAI not available, fall back to simple rule-based
        if not self.enabled:
            return self._fallback_response(user_input, stage, patient_data)

        try:
            # Build conversation history for OpenAI
            messages = [
                {"role": "system", "content": self.SYSTEM_PROMPT},
            ]

            # Add previous context as a summary
            if patient_data:
                context_summary = f"Patient info collected so far: {json.dumps(patient_data)}"
                messages.append({"role": "system", "content": context_summary})

            messages.append({"role": "user", "content": user_input})

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=400,
            )

            ai_message = (response.choices[0].message.content or "").strip()

            # Extract structured data from conversation
            updated_data = self._extract_from_conversation(ai_message, patient_data, user_input)

            # Determine next stage
            new_stage = self._determine_stage(stage, updated_data, ai_message)

            return {
                "message": ai_message,
                "stage": new_stage,
                "patient_data": updated_data,
                "conversation_id": context.get("conversation_id"),
            }

        except AuthenticationError:
            logger.error("OpenAI authentication failed")
            return self._fallback_response(user_input, stage, patient_data)
        except RateLimitError:
            logger.error("OpenAI rate limit exceeded")
            return self._fallback_response(user_input, stage, patient_data)
        except BadRequestError as e:
            logger.error(f"OpenAI bad request error: {e}")
            return self._fallback_response(user_input, stage, patient_data)
        except APIConnectionError as e:
            logger.error(f"OpenAI connection error: {e}")
            return self._fallback_response(user_input, stage, patient_data)
        except APIError as e:
            logger.error(f"OpenAI error: {e}")
            return self._fallback_response(user_input, stage, patient_data)
        except Exception as e:
            logger.error(f"OpenAI chat error: {e}")
            return self._fallback_response(user_input, stage, patient_data)

    def _extract_from_conversation(self, ai_message: str, patient_data: Dict, user_input: str) -> Dict:
        """Extract structured data from conversation text."""
        data = dict(patient_data)
        text = (ai_message + " " + user_input).lower()

        # Extract age mentions
        age_keywords = {
            "newborn": "newborn", "infant": "infant",
            "child (1-5)": "child_1_5", "child (6-12)": "child_6_12",
            "teen": "teen", "adult": "adult", "elderly": "elderly", "senior": "elderly",
        }
        for kw, val in age_keywords.items():
            if kw in text:
                data["age_group"] = val
                break

        # Extract sex mentions
        if any(w in text for w in ["male", "man", "boy"]):
            data["sex"] = "male"
        elif any(w in text for w in ["female", "woman", "girl"]):
            data["sex"] = "female"

        # Extract duration mentions
        duration_keywords = {
            "today": "less_than_1_hour", "hour": "1_6_hours",
            "hours": "1_6_hours", "days": "1_3_days",
            "week": "more_than_1_week", "month": "more_than_1_month",
        }
        for kw, val in duration_keywords.items():
            if kw in text:
                data["symptom_duration"] = val
                break

        # Extract severity
        if any(w in text for w in ["severe", "very bad", "worst", "unbearable", "terrible"]):
            data["symptom_severity"] = "severe"
        elif any(w in text for w in ["moderate", "medium", "some difficulty"]):
            data["symptom_severity"] = "moderate"
        elif any(w in text for w in ["mild", "slight", "little", "minor"]):
            data["symptom_severity"] = "mild"

        # Extract complaint text
        if not data.get("complaint_text"):
            data["complaint_text"] = user_input

        return data

    def _determine_stage(self, current_stage: str, patient_data: Dict, ai_message: str) -> str:
        """Determine conversation stage."""
        if current_stage == "symptoms":
            if patient_data.get("complaint_text"):
                return "followup"
        elif current_stage == "followup":
            if patient_data.get("age_group") and patient_data.get("sex"):
                return "consent"
        elif current_stage == "consent":
            if any(w in ai_message.lower() for w in ["agree", "yes", "consent"]):
                return "assessment"
        return current_stage

    def _fallback_response(self, user_input: str, stage: str, patient_data: Dict) -> Dict:
        """Rule-based fallback when OpenAI unavailable."""
        if stage == "symptoms":
            return {
                "message": (
                    "Thank you for telling me. To help assess you, I need to know:\n"
                    "1. How old is the patient?\n"
                    "2. Are they male or female?\n"
                    "3. How long have symptoms lasted?\n\n"
                    "Please describe your symptoms in more detail."
                ),
                "stage": "followup",
                "patient_data": {"complaint_text": user_input},
            }
        return {
            "message": (
                "I understand. Based on your symptoms, please visit your nearest "
                "health facility for assessment by a qualified healthcare worker."
            ),
            "stage": "assessment",
            "patient_data": patient_data,
        }


# Global instance
chat_ai = ConversationalTriageAI()
