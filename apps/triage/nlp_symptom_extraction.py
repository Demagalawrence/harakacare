"""
NLP Symptom Understanding Module - Phase 3 AI Upgrade

Extracts symptoms, duration, severity, and other clinical details from
natural language patient input. Supports English initially, architected
for Ugandan languages (Luganda, Runyankole, Ateso, Luo).

This is a clinical decision-support tool - it extracts what patients
report, it does NOT diagnose.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ExtractedSymptom:
    """A symptom extracted from patient text"""
    symptom: str
    confidence: float
    source_text: str
    category: Optional[str] = None


@dataclass
class NLPResult:
    """Complete NLP extraction result"""
    complaint_text: str
    complaint_group: Optional[str]
    primary_symptom: Optional[str]
    secondary_symptoms: List[str]
    duration: Optional[str]
    severity: Optional[str]
    progression: Optional[str]
    red_flags: List[str]
    risk_modifiers: Dict[str, Any]
    extracted_symptoms: List[ExtractedSymptom]
    confidence_score: float
    language: str = 'en'
    needs_followup: bool = True
    missing_info: List[str] = field(default_factory=list)


# ============================================================================
# SYMPTOM KEYWORD MAP (English)
# Maps patient language to standardized symptom concepts
# ============================================================================

SYMPTOM_KEYWORDS = {
    'fever': [
        'fever', 'high temperature', 'hot body', 'burning up', 'feeling hot',
        'temperature', 'febrile', 'chills', 'shivering', 'rigors'
    ],
    'headache': [
        'headache', 'head pain', 'migraine', 'throbbing head', 'splitting headache',
        'pain in head', 'aching head'
    ],
    'breathing': [
        'breathing', 'shortness of breath', 'difficulty breathing', 'breathless',
        'cough', 'coughing', 'wheezing', 'cannot breathe', 'struggling to breathe',
        'tight chest', 'chest tightness'
    ],
    'chest_pain': [
        'chest pain', 'chest hurt', 'heart pain', 'tight chest', 'pressing chest',
        'stabbing chest', 'burning chest'
    ],
    'abdominal': [
        'stomach pain', 'abdominal pain', 'tummy pain', 'belly pain', 'gut pain',
        'vomiting', 'throwing up', 'nausea', 'diarrhea', 'runny stomach',
        'stomach ache', 'pain in stomach', 'upper abdominal', 'lower abdominal'
    ],
    'injury': [
        'injury', 'hurt', 'wound', 'cut', 'fall', 'fell', 'accident', 'trauma',
        'broken', 'fracture', 'sprain', 'burn', 'bleeding wound'
    ],
    'bleeding': [
        'bleeding', 'blood loss', 'heavy bleeding', 'hemorrhage', 'bleeding heavily',
        'blood in', 'coughing blood', 'vomiting blood'
    ],
    'skin': [
        'skin problem', 'rash', 'itch', 'itching', 'rash on skin', 'skin infection',
        'wound', 'sore', 'boil', 'abscess'
    ],
    'feeding': [
        'feeding problem', 'not eating', 'loss of appetite', 'cannot eat',
        'difficulty swallowing', 'general weakness', 'weakness', 'fatigue',
        'tired all the time'
    ],
    'mental_health': [
        'mental health', 'emotional crisis', 'depression', 'anxiety', 'suicidal',
        'sad all the time', 'crying', 'panic', 'stress', 'worried'
    ],
    'pregnancy': [
        'pregnancy', 'pregnant', 'labor pains', 'labor', 'childbirth', 'miscarriage',
        'vaginal bleeding', 'heavy vaginal bleeding', 'abdominal pain pregnancy'
    ],
}

# Map complaint groups to standardized values
COMPLAINT_GROUP_MAP = {}
for group, keywords in SYMPTOM_KEYWORDS.items():
    for kw in keywords:
        COMPLAINT_GROUP_MAP[kw.lower()] = group

# Duration keyword patterns
DURATION_PATTERNS = [
    (r'(?i)(today|just started|just now|a few hours ago)', 'less_than_1_hour'),
    (r'(?i)(1.? ?6 hours|one to six hours|1-6 hours|6_24_hours)', '1_6_hours'),
    (r'(?i)(6.? ?24 hours|six to twenty.?four hours|6-24 hours)', '6_24_hours'),
    (r'(?i)(1.? ?3 days|one to three days|1-3 days|two days|three days)', '1_3_days'),
    (r'(?i)(4.? ?7 days|four to seven days|4-7 days|a week|one week)', '4_7_days'),
    (r'(?i)(more than 1 week|over a week|two weeks|more_than_1_week)', 'more_than_1_week'),
    (r'(?i)(more than 1 month|over a month|months|more_than_1_month)', 'more_than_1_month'),
]

# Severity keyword patterns
SEVERITY_PATTERNS = [
    (r'(?i)(very.severe|extreme|critical|life.?threatening|unbearable|worst)', 'very_severe'),
    (r'(?i)(severe|bad|intense|strong|terrible)', 'severe'),
    (r'(?i)(moderate|medium|some difficulty|manageable)', 'moderate'),
    (r'(?i)(mild|slight|minor|little|barely)', 'mild'),
]

# Red flag keywords (WHO ABCD)
RED_FLAG_KEYWORDS = {
    'airway_obstruction': [
        'choking', 'cannot speak', 'cant speak', 'stridor', 'gasping',
        'cannot swallow', 'cant swallow', 'throat closing'
    ],
    'severe_breathing_difficulty': [
        'struggling to breathe', 'cant breathe', 'cannot breathe',
        'blue lips', 'turning blue', 'gasping for air'
    ],
    'severe_bleeding': [
        'heavy bleeding', 'bleeding heavily', 'coughing blood',
        'vomiting blood', 'blood everywhere'
    ],
    'unconscious': [
        'unconscious', 'unresponsive', 'passed out', 'fainted',
        'cannot wake', 'cant wake', 'knocked out'
    ],
    'convulsions': [
        'seizure', 'convulsion', 'fitting', 'convulsing', 'epileptic fit',
        'shaking uncontrollably'
    ],
    'confusion': [
        'confused', 'confusion', 'disoriented', 'does not know where',
        'doesnt know where', 'not making sense'
    ],
    'stroke_symptoms': [
        'face droop', 'arm weakness', 'speech difficulty', 'sudden weakness',
        'one side of body', 'one-sided weakness'
    ],
    'pregnancy_emergency': [
        'heavy vaginal bleeding', 'severe abdominal pain pregnancy',
        'labor pains', 'water broke', 'miscarriage'
    ],
    'severe_pain': [
        'worst pain', 'unbearable pain', 'severe uncontrolled pain',
        'cannot move', 'cant move'
    ],
}

# Risk modifier keywords (age-specific conditions, pregnancy, chronic)
RISK_MODIFIER_KEYWORDS = {
    'is_pregnant': ['pregnant', 'expecting', 'with child'],
    'has_chronic_asthma': ['asthma', 'asthmatic', 'wheezing condition'],
    'has_chronic_diabetes': ['diabetes', 'diabetic', 'sugar disease'],
    'has_chronic_hypertension': ['hypertension', 'high blood pressure', 'bp'],
    'has_chronic_heart_disease': ['heart disease', 'heart problem', 'cardiac'],
    'has_chronic_hiv': ['hiv', 'aids', 'positive'],
    'is_immunocompromised': ['immunocompromised', 'weak immune', 'on steroids'],
    'is_newborn': ['newborn', 'neonate', 'baby under 2 months'],
    'is_elderly': ['elderly', 'senior', 'old age', 'grandmother', 'grandfather'],
}


def extract_complaint_group(text: str) -> Tuple[Optional[str], float]:
    """
    Extract the primary complaint group from free text.
    
    Returns (complaint_group, confidence) or (None, 0.0).
    
    Preserves original text mapping - similar symptoms map to same group
    but original description is retained in source_text.
    """
    text_lower = text.lower()
    best_group = None
    best_confidence = 0.0
    
    for group, keywords in SYMPTOM_KEYWORDS.items():
        matches = sum(1 for kw in keywords if kw.lower() in text_lower)
        if matches > 0:
            confidence = min(matches / len(keywords) * 2.0, 1.0)  # Cap at 1.0
            if confidence > best_confidence:
                best_confidence = confidence
                best_group = group
    
    return best_group, best_confidence


def extract_symptoms(text: str) -> List[ExtractedSymptom]:
    """
    Extract individual symptoms from free text with confidence scores.
    
    Returns list of ExtractedSymptom objects.
    """
    text_lower = text.lower()
    symptoms = []
    
    for group, keywords in SYMPTOM_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                # Calculate confidence based on keyword specificity
                confidence = min(0.5 + (len(kw) / 30.0), 0.95)
                symptoms.append(ExtractedSymptom(
                    symptom=group,
                    confidence=confidence,
                    source_text=kw,
                    category=group
                ))
                break  # One match per group
    
    # Sort by confidence descending
    symptoms.sort(key=lambda s: s.confidence, reverse=True)
    return symptoms


def extract_duration(text: str) -> Optional[str]:
    """Extract symptom duration from text"""
    for pattern, duration_value in DURATION_PATTERNS:
        if re.search(pattern, text):
            return duration_value
    return None


def extract_severity(text: str) -> Optional[str]:
    """Extract symptom severity from text"""
    for pattern, severity_value in SEVERITY_PATTERNS:
        if re.search(pattern, text):
            return severity_value
    return None


def detect_red_flags(text: str, age_group: Optional[str] = None) -> List[str]:
    """
    Detect WHO ABCD red flag indicators from text.
    
    Returns list of red flag names detected.
    Emergency cases should be checked before ML recommendations.
    """
    text_lower = text.lower()
    detected = []
    
    for flag_name, keywords in RED_FLAG_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                # Check age appropriateness if specified
                detected.append(flag_name)
                break
    
    return detected


def extract_risk_modifiers(text: str, age_group: Optional[str] = None,
                           sex: Optional[str] = None,
                           pregnancy_status: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract high-risk population modifiers from text and demographics.
    
    Returns dict of risk modifier flags.
    """
    text_lower = text.lower()
    modifiers = {}
    
    # From text keywords
    for modifier, keywords in RISK_MODIFIER_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                modifiers[modifier] = True
                break
    
    # From age group
    if age_group:
        if age_group in ['newborn', 'infant', 'child_1_5']:
            modifiers['is_high_risk_age'] = True
        if age_group == 'elderly':
            modifiers['is_elderly'] = True
    
    # From pregnancy status
    if pregnancy_status in ['yes', 'possible']:
        modifiers['is_pregnant'] = True
    
    # Sex-specific risk
    if sex == 'female' and pregnancy_status in ['yes', 'possible']:
        modifiers['pregnancy_risk'] = True
    
    return modifiers


def extract_progression(text: str) -> Optional[str]:
    """Extract symptom progression pattern from text"""
    text_lower = text.lower()
    
    if re.search(r'(?i)(getting worse|worsening|deteriorating)', text_lower):
        return 'getting_worse'
    elif re.search(r'(?i)(getting better|improving|recovering)', text_lower):
        return 'getting_better'
    elif re.search(r'(?i)(same|unchanged|staying same)', text_lower):
        return 'staying_same'
    elif re.search(r'(?i)(comes and goes|intermittent|on and off)', text_lower):
        return 'comes_and_goes'
    elif re.search(r'(?i)(sudden|suddenly|all of a sudden|abrupt)', text_lower):
        return 'sudden'
    
    return None


def parse_natural_language(text: str, age_group: Optional[str] = None,
                           sex: Optional[str] = None,
                           pregnancy_status: Optional[str] = None) -> NLPResult:
    """
    Main entry point: parse natural language symptom description.
    
    Returns a complete NLPResult with all extracted fields.
    
    This is an EXPERIMENTAL prototype. It uses keyword-based extraction
    and should be validated with clinician-reviewed data before production use.
    """
    text = text.strip()
    
    # Extract complaint group
    complaint_group, group_confidence = extract_complaint_group(text)
    
    # Extract individual symptoms
    extracted = extract_symptoms(text)
    
    # Primary symptom is the highest-confidence extracted symptom
    primary_symptom = extracted[0].symptom if extracted else None
    
    # Secondary symptoms are the rest
    secondary_symptoms = [s.symptom for s in extracted[1:]]
    
    # Extract duration, severity, progression
    duration = extract_duration(text)
    severity = extract_severity(text)
    progression = extract_progression(text)
    
    # Detect red flags
    red_flags = detect_red_flags(text, age_group)
    
    # Extract risk modifiers
    risk_modifiers = extract_risk_modifiers(text, age_group, sex, pregnancy_status)
    
    # Calculate overall confidence
    confidence_factors = []
    if complaint_group:
        confidence_factors.append(group_confidence)
    if extracted:
        confidence_factors.append(sum(s.confidence for s in extracted) / len(extracted))
    if duration:
        confidence_factors.append(0.8)
    if severity:
        confidence_factors.append(0.8)
    
    overall_confidence = (
        sum(confidence_factors) / len(confidence_factors)
        if confidence_factors else 0.3
    )
    
    # Determine missing information
    missing_info = []
    if not duration:
        missing_info.append('symptom_duration')
    if not severity:
        missing_info.append('symptom_severity')
    if not complaint_group:
        missing_info.append('complaint_group')
    if red_flags:
        missing_info.append('emergency_assessment')
    
    # Determine if follow-up is needed
    needs_followup = (
        len(missing_info) > 0 or
        not red_flags and not complaint_group
    )
    
    return NLPResult(
        complaint_text=text,
        complaint_group=complaint_group,
        primary_symptom=primary_symptom,
        secondary_symptoms=secondary_symptoms,
        duration=duration,
        severity=severity,
        progression=progression,
        red_flags=red_flags,
        risk_modifiers=risk_modifiers,
        extracted_symptoms=extracted,
        confidence_score=overall_confidence,
        language='en',
        needs_followup=needs_followup,
        missing_info=missing_info,
    )


def get_clinician_approved_questions(complaint_group: Optional[str],
                                      age_group: Optional[str],
                                      red_flags: List[str],
                                      missing_info: List[str],
                                      severity: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Generate clinician-approved follow-up questions based on extracted info.
    
    Questions prioritize emergency warning signs over routine assessment.
    
    Returns list of question dicts with 'id', 'question', 'type', 'options'.
    """
    questions = []
    
    # PRIORITY 1: Emergency red flag questions (always first)
    if red_flags:
        emergency_questions = [
            {
                'id': 'emergency_immediate',
                'question': 'Are you experiencing this right now?',
                'type': 'boolean',
                'urgent': True,
            },
            {
                'id': 'emergency_location',
                'question': 'Where are you located? Can someone take you to a hospital?',
                'type': 'text',
                'urgent': True,
            },
        ]
        questions.extend(emergency_questions)
        return questions  # Only emergency questions if red flags present
    
    # PRIORITY 2: Missing critical information
    if 'complaint_group' in missing_info:
        questions.append({
            'id': 'complaint_group',
            'question': 'What is your main symptom?',
            'type': 'choice',
            'options': [
                'fever', 'breathing problem', 'chest pain', 'stomach pain',
                'headache', 'injury', 'bleeding', 'skin problem',
                'feeding problem', 'mental health', 'pregnancy concern', 'other'
            ],
        })
    
    # PRIORITY 3: Duration
    if 'symptom_duration' in missing_info:
        questions.append({
            'id': 'symptom_duration',
            'question': 'How long have you had these symptoms?',
            'type': 'choice',
            'options': [
                'Less than 1 hour', '1-6 hours', '6-24 hours',
                '1-3 days', '4-7 days', 'More than 1 week',
                'More than 1 month'
            ],
        })
    
    # PRIORITY 4: Severity
    if 'symptom_severity' in missing_info:
        questions.append({
            'id': 'symptom_severity',
            'question': 'How severe are your symptoms?',
            'type': 'choice',
            'options': [
                'Mild - can do normal activities',
                'Moderate - some difficulty with activities',
                'Severe - unable to do normal activities',
                'Very severe - unable to move/talk/function',
            ],
        })
    
    # PRIORITY 5: Complaint-specific questions
    complaint_questions = _get_complaint_specific_questions(complaint_group, age_group)
    questions.extend(complaint_questions)
    
    return questions


def _get_complaint_specific_questions(complaint_group: Optional[str],
                                       age_group: Optional[str]) -> List[Dict[str, Any]]:
    """Get complaint-specific follow-up questions"""
    
    question_map = {
        'fever': [
            {
                'id': 'fever_duration',
                'question': 'How long have you had the fever?',
                'type': 'choice',
                'options': ['Less than 1 hour', '1-6 hours', '6-24 hours',
                          '1-3 days', '4-7 days', 'More than 1 week'],
            },
            {
                'id': 'fever_temperature',
                'question': 'Have you measured your temperature?',
                'type': 'choice',
                'options': ['Yes, above 38°C', 'Yes, below 38°C', 'No, not measured'],
            },
            {
                'id': 'fever_breathing',
                'question': 'Are you experiencing difficulty breathing?',
                'type': 'boolean',
                'urgent': True,
            },
            {
                'id': 'fever_weakness',
                'question': 'Are you experiencing severe weakness?',
                'type': 'boolean',
                'urgent': True,
            },
            {
                'id': 'fever_vomiting',
                'question': 'Are you vomiting persistently?',
                'type': 'boolean',
                'urgent': True,
            },
        ],
        'breathing': [
            {
                'id': 'breathing_difficulty',
                'question': 'Are you struggling to breathe right now?',
                'type': 'boolean',
                'urgent': True,
            },
            {
                'id': 'breathing_blue_lips',
                'question': 'Are your lips or fingers turning blue?',
                'type': 'boolean',
                'urgent': True,
            },
            {
                'id': 'breathing_cough',
                'question': 'Are you coughing?',
                'type': 'boolean',
            },
        ],
        'chest_pain': [
            {
                'id': 'chest_pain_severity',
                'question': 'Is the chest pain severe or crushing?',
                'type': 'boolean',
                'urgent': True,
            },
            {
                'id': 'chest_pain_radiation',
                'question': 'Does the pain spread to your arm, jaw, or back?',
                'type': 'boolean',
                'urgent': True,
            },
            {
                'id': 'chest_pain_breathing',
                'question': 'Are you having difficulty breathing with the chest pain?',
                'type': 'boolean',
                'urgent': True,
            },
        ],
        'abdominal': [
            {
                'id': 'abdominal_severity',
                'question': 'Is the abdominal pain severe?',
                'type': 'boolean',
                'urgent': True,
            },
            {
                'id': 'abdominal_vomiting',
                'question': 'Are you vomiting?',
                'type': 'boolean',
            },
            {
                'id': 'abdominal_blood',
                'question': 'Is there blood in your vomit or stool?',
                'type': 'boolean',
                'urgent': True,
            },
        ],
        'headache': [
            {
                'id': 'headache_sudden',
                'question': 'Did the headache start suddenly and severely?',
                'type': 'boolean',
                'urgent': True,
            },
            {
                'id': 'headache_confusion',
                'question': 'Are you confused or having difficulty speaking?',
                'type': 'boolean',
                'urgent': True,
            },
            {
                'id': 'headache_stiff_neck',
                'question': 'Do you have a stiff neck with the headache?',
                'type': 'boolean',
                'urgent': True,
            },
        ],
        'bleeding': [
            {
                'id': 'bleeding_heavy',
                'question': 'Is the bleeding heavy or difficult to stop?',
                'type': 'boolean',
                'urgent': True,
            },
            {
                'id': 'bleeding_location',
                'question': 'Where is the bleeding coming from?',
                'type': 'text',
                'urgent': True,
            },
        ],
        'pregnancy': [
            {
                'id': 'pregnancy_bleeding',
                'question': 'Is there heavy vaginal bleeding?',
                'type': 'boolean',
                'urgent': True,
            },
            {
                'id': 'pregnancy_pain',
                'question': 'Do you have severe abdominal pain?',
                'type': 'boolean',
                'urgent': True,
            },
            {
                'id': 'pregnancy_labor',
                'question': 'Are you in labor or is your water broken?',
                'type': 'boolean',
                'urgent': True,
            },
        ],
        'injury': [
            {
                'id': 'injury_bleeding',
                'question': 'Is there heavy bleeding from the injury?',
                'type': 'boolean',
                'urgent': True,
            },
            {
                'id': 'injury_consciousness',
                'question': 'Did you lose consciousness at any point?',
                'type': 'boolean',
                'urgent': True,
            },
            {
                'id': 'injury_movement',
                'question': 'Can you move the injured part?',
                'type': 'boolean',
            },
        ],
    }
    
    if complaint_group and complaint_group in question_map:
        return question_map[complaint_group]
    
    # Default questions for unknown/other complaint
    return [
        {
            'id': 'general_description',
            'question': 'Can you describe your symptoms in more detail?',
            'type': 'text',
        },
        {
            'id': 'general_severity',
            'question': 'How severe are your symptoms on a scale of 1-10?',
            'type': 'number',
        },
    ]


def get_missing_info_explanation(missing_info: List[str]) -> str:
    """
    Generate a patient-friendly explanation of what information is still needed.
    """
    if not missing_info:
        return "All necessary information has been collected."
    
    explanations = {
        'symptom_duration': 'How long your symptoms have been present',
        'symptom_severity': 'How severe your symptoms are',
        'complaint_group': 'What your main symptom is',
        'emergency_assessment': 'Whether you need emergency care',
    }
    
    items = [explanations.get(m, m.replace('_', ' ')) for m in missing_info]
    
    if len(items) == 1:
        return f"Still needed: {items[0]}."
    else:
        return f"Still needed: {', '.join(items[:-1])} and {items[-1]}."