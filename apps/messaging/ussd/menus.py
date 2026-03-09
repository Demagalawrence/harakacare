"""
USSD Menu Definitions
Centralises all menu text, option mappings, and the menu state enum.
"""

from enum import Enum


class USSDMenu(Enum):
    """All possible USSD menu states."""
    WELCOME = "welcome"
    LANGUAGE = "language"
    MAIN_MENU = "main_menu"

    # New-triage branch
    COMPLAINT_SELECTION = "complaint_selection"
    AGE_SELECTION = "age_selection"
    SEX_SELECTION = "sex_selection"
    DISTRICT_INPUT = "district_input"
    VILLAGE_INPUT = "village_input"
    ALLERGIES_INPUT = "allergies_input"
    CHRONIC_CONDITIONS_INPUT = "chronic_conditions_input"
    MEDICATION_INPUT = "medication_input"
    SEVERITY_SELECTION = "severity_selection"
    DURATION_SELECTION = "duration_selection"
    PREGNANCY_CHECK = "pregnancy_check"
    CONSENT = "consent"
    PROCESSING = "processing"

    # Status-check branch
    STATUS_TOKEN_INPUT = "status_token_input"

    # Terminal screens
    EMERGENCY = "emergency"
    COMPLETE = "complete"


# ---------------------------------------------------------------------------
# Menu text — keyed by USSDMenu → language
# ---------------------------------------------------------------------------

MENU_TEXTS = {
    USSDMenu.WELCOME: {
        "en": (
            "Welcome to HarakaCare\n"
            "Fast health assessment.\n"
            "1. Start assessment\n"
            "2. Check previous result\n"
            "3. Help"
        ),
    },

    USSDMenu.MAIN_MENU: {
        "en": (
            "HarakaCare Menu:\n"
            "1. Start health assessment\n"
            "2. Check previous result\n"
            "3. Help"
        ),
    },

    USSDMenu.COMPLAINT_SELECTION: {
        "en": (
            "What is the main problem?\n"
            "1. Fever / feeling hot\n"
            "2. Breathing / cough\n"
            "3. Injury / accident\n"
            "4. Stomach pain / vomiting\n"
            "5. Headache / confusion\n"
            "6. Chest pain\n"
            "7. Bleeding\n"
            "8. Other"
        ),
    },

    USSDMenu.AGE_SELECTION: {
        "en": (
            "Age of patient:\n"
            "1. Newborn (0-2 months)\n"
            "2. Infant (2-12 months)\n"
            "3. Child (1-5 years)\n"
            "4. Child (6-12 years)\n"
            "5. Teen (13-17 years)\n"
            "6. Adult (18-64 years)\n"
            "7. Elderly (65+ years)"
        ),
    },

    USSDMenu.SEX_SELECTION: {
        "en": "Sex of patient:\n1. Male\n2. Female",
    },

    USSDMenu.DISTRICT_INPUT: {
        "en": "Enter your district name (e.g. Kampala, Wakiso, Jinja):",
    },

    USSDMenu.VILLAGE_INPUT: {
        "en": "Enter your village/town name (e.g. Kibuye, Nateete):",
    },

    USSDMenu.ALLERGIES_INPUT: {
        "en": "Does the patient have any known allergies?\n1. Yes\n2. No\n3. Not sure",
    },

    USSDMenu.CHRONIC_CONDITIONS_INPUT: {
        "en": "Does the patient have any long-term conditions? (e.g. diabetes, hypertension)\n1. Yes - please describe\n2. No",
    },

    USSDMenu.MEDICATION_INPUT: {
        "en": "Is the patient currently taking any medication?\n1. Yes\n2. No",
    },

    USSDMenu.SEVERITY_SELECTION: {
        "en": (
            "How severe are the symptoms?\n"
            "1. Mild - still doing daily activities\n"
            "2. Moderate - some difficulty\n"
            "3. Severe - cannot do activities\n"
            "4. Very severe - cannot move/speak"
        ),
    },

    USSDMenu.DURATION_SELECTION: {
        "en": (
            "How long have the symptoms lasted?\n"
            "1. Less than 1 hour\n"
            "2. 1-6 hours\n"
            "3. 6-24 hours\n"
            "4. 1-3 days\n"
            "5. 4-7 days\n"
            "6. More than 1 week\n"
            "7. More than 1 month"
        ),
    },

    USSDMenu.PREGNANCY_CHECK: {
        "en": "Is the patient pregnant?\n1. Yes\n2. Possibly\n3. No",
    },

    USSDMenu.CONSENT: {
        "en": (
            "HarakaCare will assess your symptoms.\n"
            "Data used for health assessment only.\n"
            "1. I agree - continue\n"
            "2. Cancel"
        ),
    },

    USSDMenu.PROCESSING: {
        "en": "Assessing your symptoms. Please wait...",
    },

    USSDMenu.EMERGENCY: {
        "en": (
            "⚠️ EMERGENCY SIGNS DETECTED\n"
            "Go to the nearest hospital NOW.\n"
            "Call emergency: 999 / 0800 100 066\n"
            "Do not wait."
        ),
    },
}

# ---------------------------------------------------------------------------
# Input → model value mappings
# ---------------------------------------------------------------------------

COMPLAINT_MAPPING = {
    "1": "fever",
    "2": "breathing",
    "3": "injury",
    "4": "abdominal",
    "5": "headache",
    "6": "chest_pain",
    "7": "bleeding",
    "8": "other",
}

AGE_MAPPING = {
    "1": "newborn",
    "2": "infant",
    "3": "child_1_5",
    "4": "child_6_12",
    "5": "teen",
    "6": "adult",
    "7": "elderly",
}

SEX_MAPPING = {
    "1": "male",
    "2": "female",
}

SEVERITY_MAPPING = {
    "1": "mild",
    "2": "moderate",
    "3": "severe",
    "4": "very_severe",
}

DURATION_MAPPING = {
    "1": "less_than_1_hour",
    "2": "1_6_hours",
    "3": "6_24_hours",
    "4": "1_3_days",
    "5": "4_7_days",
    "6": "more_than_1_week",
    "7": "more_than_1_month",
}

PREGNANCY_MAPPING = {
    "1": "yes",
    "2": "possible",
    "3": "no",
}

ALLERGIES_MAPPING = {
    "1": "yes",
    "2": "no",
    "3": "not_sure",
}

CHRONIC_CONDITIONS_MAPPING = {
    "1": "yes",
    "2": "no",
}

MEDICATION_MAPPING = {
    "1": "yes",
    "2": "no",
}

# ---------------------------------------------------------------------------
# Emergency triggers
# ---------------------------------------------------------------------------

# Complaints that should immediately end with an emergency screen
EMERGENCY_COMPLAINTS: set = set()  # e.g. add "chest_pain" if you want instant escalation

# Severity levels that trigger immediate emergency escalation
EMERGENCY_SEVERITIES = {"very_severe"}