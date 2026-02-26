"""
Tool 1: Intake & Validation Tool - UPDATED
Receives patient-submitted data and validates completeness and schema correctness
Now supports complaint-based intake and age-adaptive validation
"""

from typing import Dict, Any, List, Tuple, Optional
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
import uuid
import re


class IntakeValidationTool:
    """
    Validates and processes incoming triage data - UPDATED
    Supports complaint-based intake and age-adaptive validation
    """

    def __init__(self):
        self.errors = []
        self.warnings = []

        # ====================================================================
        # NEW: Required fields for complaint-based model
        # ====================================================================
        self.REQUIRED_FIELDS = [
            'age_group',  # Replaces age_range
            'sex',  # Now required
            'district',
            'consent_medical_triage',
            'consent_data_sharing',
            'consent_follow_up',
        ]

        # ====================================================================
        # NEW: Valid choices for all fields
        # ====================================================================
        self.VALID_CHOICES = {
            # Complaint-based fields
            'complaint_group': [
                'fever', 'breathing', 'injury', 'abdominal', 'headache',
                'chest_pain', 'pregnancy', 'skin', 'feeding', 'bleeding',
                'mental_health', 'other'
            ],
            
            # Age groups (7 categories)
            'age_group': [
                'newborn', 'infant', 'child_1_5', 'child_6_12',
                'teen', 'adult', 'elderly'
            ],
            
            # Sex (now required)
            'sex': ['male', 'female', 'other'],
            
            # Patient relation
            'patient_relation': ['self', 'child', 'family', 'other'],
            
            # Symptom severity (updated)
            'symptom_severity': [
                'mild', 'moderate', 'severe', 'very_severe'
            ],
            
            # Symptom duration (expanded)
            'symptom_duration': [
                'less_than_1_hour', '1_6_hours', '6_24_hours', '1_3_days',
                '4_7_days', 'more_than_1_week', 'more_than_1_month'
            ],
            
            # Progression status (replaces symptom_pattern)
            'progression_status': [
                'sudden', 'getting_worse', 'staying_same',
                'getting_better', 'comes_and_goes'
            ],
            
            # Pregnancy status (updated)
            'pregnancy_status': [
                'yes', 'possible', 'no', 'not_applicable'
            ],
            
            # Chronic conditions (expanded)
            'chronic_conditions': [
                'hypertension', 'diabetes', 'asthma', 'heart_disease',
                'copd', 'epilepsy', 'sickle_cell', 'hiv_aids',
                'cancer', 'kidney_disease', 'liver_disease',
                'other_chronic', 'none', 'prefer_not_to_say'
            ],
            
            # Channel
            'channel': ['ussd', 'sms', 'whatsapp', 'web', 'mobile_app'],
        }

        # ====================================================================
        # RED FLAG SYMPTOMS (WHO ABCD - expanded)
        # ====================================================================
        self.RED_FLAG_SYMPTOMS = [
            # Airway/Breathing
            'airway_obstruction', 'severe_breathing_difficulty', 'chest_indrawing',
            # Circulation
            'severe_bleeding', 'signs_of_shock',
            # Disability
            'unconscious', 'convulsions', 'confusion', 'stroke_symptoms',
            # Pediatric
            'unable_to_drink', 'vomits_everything', 'lethargic_floppy',
            # Obstetric
            'pregnancy_emergency',
            # Other
            'severe_pain'
        ]

        # ====================================================================
        # DEPRECATED FIELDS (for backward compatibility)
        # ====================================================================
        self.DEPRECATED_FIELDS = {
            'age_range': 'Use age_group instead (newborn/infant/child_1_5/child_6_12/teen/adult/elderly)',
            'primary_symptom': 'Use complaint_group instead',
            'secondary_symptoms': 'Use symptom_indicators JSON field instead',
            'symptom_pattern': 'Use progression_status instead',
            'condition_occurrence': 'Use risk_modifiers instead',
            'chronic_conditions_list': 'Use has_chronic_conditions + risk_modifiers',
            'current_medication': 'Use on_medication boolean instead',
            'has_allergies': 'Include in risk_modifiers',
            'allergy_types': 'Include in risk_modifiers',
            'additional_description': 'Use complaint_text instead'
        }

    def validate(self, data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], List[str]]:
        """
        Validate incoming triage data - UPDATED

        Args:
            data: Raw intake data dictionary

        Returns:
            Tuple of (is_valid, cleaned_data, errors)
        """
        self.errors = []
        self.warnings = []

        print("\n🔍 INTAKE VALIDATION")
        
        # Handle deprecated fields (add warnings)
        self._check_deprecated_fields(data)

        # Check required fields
        self._validate_required_fields(data)

        # Validate field choices
        self._validate_field_choices(data)

        # Validate data types
        self._validate_data_types(data)

        # Validate consent
        self._validate_consent(data)

        # Validate conditional fields
        self._validate_conditional_fields(data)

        # Validate text fields
        self._validate_text_fields(data)

        # Validate complaint text if provided
        self._validate_complaint_text(data)

        # Validate symptom indicators if provided
        self._validate_symptom_indicators(data)

        # Validate red flag indicators if provided
        self._validate_red_flag_indicators(data)

        # Validate risk modifiers if provided
        self._validate_risk_modifiers(data)

        # Clean and prepare data
        cleaned_data = self._clean_data(data) if not self.errors else {}

        print(f"  • Valid: {len(self.errors) == 0}")
        if self.warnings:
            print(f"  • Warnings: {len(self.warnings)}")
        if self.errors:
            print(f"  • Errors: {len(self.errors)}")

        return (len(self.errors) == 0, cleaned_data, self.errors)

    def _check_deprecated_fields(self, data: Dict[str, Any]) -> None:
        """Check for deprecated fields and add warnings"""
        for field, message in self.DEPRECATED_FIELDS.items():
            if field in data and data[field] not in [None, '', [], {}]:
                self.warnings.append(f"Field '{field}' is deprecated. {message}")

    def _validate_required_fields(self, data: Dict[str, Any]) -> None:
        """Check all required fields are present"""
        for field in self.REQUIRED_FIELDS:
            if field not in data or data[field] is None or data[field] == '':
                self.errors.append(f"Required field '{field}' is missing or empty")
        
        # At least one of complaint_text or complaint_group must be provided
        if not data.get('complaint_text') and not data.get('complaint_group'):
            self.errors.append("Either 'complaint_text' or 'complaint_group' must be provided")

    def _validate_field_choices(self, data: Dict[str, Any]) -> None:
        """Validate that field values are from allowed choices"""
        for field, valid_choices in self.VALID_CHOICES.items():
            if field not in data:
                continue

            value = data[field]

            # Handle array fields (multiple choice)
            if isinstance(value, list):
                for item in value:
                    if item not in valid_choices:
                        self.errors.append(
                            f"Invalid value '{item}' for field '{field}'. "
                            f"Must be one of: {', '.join(valid_choices)}"
                        )
            # Handle single choice fields
            elif value and value not in valid_choices:
                self.errors.append(
                    f"Invalid value '{value}' for field '{field}'. "
                    f"Must be one of: {', '.join(valid_choices)}"
                )

    def _validate_data_types(self, data: Dict[str, Any]) -> None:
        """Validate data types"""
        
        # Boolean fields
        boolean_fields = [
            'consent_medical_triage',
            'consent_data_sharing',
            'consent_follow_up',
            'location_consent',
            'has_red_flags',
            'has_chronic_conditions',
            'on_medication'
        ]

        for field in boolean_fields:
            if field in data and not isinstance(data[field], bool):
                self.errors.append(f"Field '{field}' must be a boolean (true/false)")

        # JSON fields
        json_fields = ['symptom_indicators', 'red_flag_indicators', 'risk_modifiers']
        for field in json_fields:
            if field in data and not isinstance(data[field], dict):
                self.errors.append(f"Field '{field}' must be a JSON object/dictionary")

        # Float fields (location)
        if 'device_location_lat' in data and data['device_location_lat'] is not None:
            try:
                lat = float(data['device_location_lat'])
                if not (-90 <= lat <= 90):
                    self.errors.append("Latitude must be between -90 and 90")
            except (ValueError, TypeError):
                self.errors.append("Invalid latitude value")

        if 'device_location_lng' in data and data['device_location_lng'] is not None:
            try:
                lng = float(data['device_location_lng'])
                if not (-180 <= lng <= 180):
                    self.errors.append("Longitude must be between -180 and 180")
            except (ValueError, TypeError):
                self.errors.append("Invalid longitude value")

        # Integer fields
        if 'conversation_turns' in data and data['conversation_turns'] is not None:
            if not isinstance(data['conversation_turns'], int) or data['conversation_turns'] < 0:
                self.errors.append("'conversation_turns' must be a positive integer")

    def _validate_consent(self, data: Dict[str, Any]) -> None:
        """Validate consent requirements"""
        required_consents = [
            'consent_medical_triage',
            'consent_data_sharing',
            'consent_follow_up'
        ]

        for consent in required_consents:
            if not data.get(consent):
                self.errors.append(
                    f"User must consent to {consent.replace('_', ' ')} to proceed"
                )

    def _validate_conditional_fields(self, data: Dict[str, Any]) -> None:
        """Validate fields that depend on other fields"""
        
        # Location validation
        if data.get('location_consent'):
            if not (data.get('device_location_lat') and data.get('device_location_lng')):
                self.warnings.append(
                    "Location coordinates missing despite location consent being given"
                )

        # Pregnancy validation
        if data.get('sex') == 'male' and data.get('pregnancy_status') in ['yes', 'possible']:
            self.errors.append("Pregnancy status cannot be 'yes' or 'possible' for male patients")

        # Age group and pregnancy
        if data.get('age_group') in ['newborn', 'infant', 'child_1_5', 'child_6_12']:
            if data.get('pregnancy_status') in ['yes', 'possible']:
                self.errors.append(f"Invalid pregnancy status for age group '{data['age_group']}'")

        # Chronic conditions validation
        if data.get('has_chronic_conditions') and not data.get('risk_modifiers', {}).get('chronic_conditions'):
            self.warnings.append(
                "has_chronic_conditions is true but no chronic conditions specified in risk_modifiers"
            )

    def _validate_text_fields(self, data: Dict[str, Any]) -> None:
        """Validate text field lengths"""
        
        # Complaint text - longer allowed for free text
        if 'complaint_text' in data and data['complaint_text']:
            if len(data['complaint_text']) > 2000:
                self.errors.append(
                    f"Complaint text exceeds 2000 character limit ({len(data['complaint_text'])} characters)"
                )

        # District and subcounty
        if 'district' in data and len(data['district']) > 100:
            self.errors.append("District name too long (max 100 characters)")

        if 'subcounty' in data and data.get('subcounty') and len(data['subcounty']) > 100:
            self.errors.append("Subcounty name too long (max 100 characters)")

        if 'village' in data and data.get('village') and len(data['village']) > 100:
            self.errors.append("Village name too long (max 100 characters)")

    def _validate_complaint_text(self, data: Dict[str, Any]) -> None:
        """Validate complaint text content"""
        complaint_text = data.get('complaint_text', '')
        
        if not complaint_text:
            return
        
        # Check for obviously invalid content
        if len(complaint_text.strip()) < 3:
            self.warnings.append("Complaint text is very short - may not provide enough information")
        
        # Check for excessive repetition
        words = complaint_text.lower().split()
        if len(words) > 10:
            # Check if same word repeated many times
            word_freq = {}
            for word in words:
                word_freq[word] = word_freq.get(word, 0) + 1
            
            max_freq = max(word_freq.values())
            if max_freq > len(words) * 0.5:
                self.warnings.append("Complaint text appears repetitive - may not be meaningful")

    def _validate_symptom_indicators(self, data: Dict[str, Any]) -> None:
        """Validate symptom indicators JSON structure"""
        indicators = data.get('symptom_indicators', {})
        
        if not indicators:
            return
        
        if not isinstance(indicators, dict):
            self.errors.append("symptom_indicators must be a dictionary")
            return
        
        # Check for boolean values
        for key, value in indicators.items():
            if not isinstance(value, bool):
                self.errors.append(f"symptom_indicators['{key}'] must be a boolean (true/false)")

    def _validate_red_flag_indicators(self, data: Dict[str, Any]) -> None:
        """Validate red flag indicators JSON structure"""
        indicators = data.get('red_flag_indicators', {})
        
        if not indicators:
            return
        
        if not isinstance(indicators, dict):
            self.errors.append("red_flag_indicators must be a dictionary")
            return
        
        # Check for valid red flag names
        for key, value in indicators.items():
            if not isinstance(value, bool):
                self.errors.append(f"red_flag_indicators['{key}'] must be a boolean")
            
            if key not in self.RED_FLAG_SYMPTOMS:
                self.warnings.append(f"Unknown red flag indicator: '{key}'")

    def _validate_risk_modifiers(self, data: Dict[str, Any]) -> None:
        """Validate risk modifiers JSON structure"""
        modifiers = data.get('risk_modifiers', {})
        
        if not modifiers:
            return
        
        if not isinstance(modifiers, dict):
            self.errors.append("risk_modifiers must be a dictionary")
            return
        
        # Validate specific fields if present
        if 'chronic_conditions' in modifiers:
            if not isinstance(modifiers['chronic_conditions'], list):
                self.errors.append("risk_modifiers.chronic_conditions must be a list")
        
        if 'medications' in modifiers:
            if not isinstance(modifiers['medications'], list):
                self.errors.append("risk_modifiers.medications must be a list")

    def _clean_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean and prepare data for storage - UPDATED

        Returns:
            Cleaned data dictionary
        """
        cleaned = data.copy()

        # Generate patient token if not provided
        # if 'patient_token' not in cleaned or not cleaned['patient_token']:
        #     cleaned['patient_token'] = self._generate_patient_token()

        # Normalize text fields
        text_fields = ['district', 'subcounty', 'village', 'complaint_text']
        for field in text_fields:
            if field in cleaned and cleaned[field]:
                cleaned[field] = cleaned[field].strip()

        # Ensure JSON fields are dictionaries
        json_fields = ['symptom_indicators', 'red_flag_indicators', 'risk_modifiers']
        for field in json_fields:
            if field not in cleaned:
                cleaned[field] = {}
            elif not isinstance(cleaned[field], dict):
                try:
                    cleaned[field] = dict(cleaned[field])
                except:
                    cleaned[field] = {}

        # Set default values for new fields if not provided
        if 'patient_relation' not in cleaned:
            cleaned['patient_relation'] = 'self'
        
        if 'conversation_turns' not in cleaned:
            cleaned['conversation_turns'] = 1

        # Set channel if not provided
        if 'channel' not in cleaned:
            cleaned['channel'] = 'web'  # Default to web

        # Map deprecated fields if present (for backward compatibility)
        cleaned = self._map_deprecated_fields(cleaned)

        return cleaned

    def _map_deprecated_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Map deprecated fields to new fields for backward compatibility"""
        
        # Map age_range to age_group
        if 'age_range' in data and 'age_group' not in data:
            age_range_map = {
                'under_5': 'child_1_5',
                '5_12': 'child_6_12',
                '13_17': 'teen',
                '18_30': 'adult',
                '31_50': 'adult',
                '51_plus': 'elderly',
            }
            data['age_group'] = age_range_map.get(data['age_range'], 'adult')
        
        # Map primary_symptom to complaint_group
        if 'primary_symptom' in data and 'complaint_group' not in data:
            symptom_map = {
                'fever': 'fever',
                'headache': 'headache',
                'chest_pain': 'chest_pain',
                'difficulty_breathing': 'breathing',
                'abdominal_pain': 'abdominal',
                'vomiting': 'abdominal',
                'diarrhea': 'abdominal',
                'injury_trauma': 'injury',
                'skin_problem': 'skin',
                'other': 'other',
            }
            data['complaint_group'] = symptom_map.get(data['primary_symptom'], 'other')
        
        # Map additional_description to complaint_text
        if 'additional_description' in data and not data.get('complaint_text'):
            data['complaint_text'] = data['additional_description']
        
        # Map symptom_pattern to progression_status
        if 'symptom_pattern' in data and 'progression_status' not in data:
            pattern_map = {
                'getting_better': 'getting_better',
                'staying_same': 'staying_same',
                'getting_worse': 'getting_worse',
                'comes_and_goes': 'comes_and_goes',
            }
            data['progression_status'] = pattern_map.get(data['symptom_pattern'])
        
        # Map current_medication to on_medication boolean
        if 'current_medication' in data and 'on_medication' not in data:
            data['on_medication'] = data['current_medication'] == 'yes'
        
        # Map chronic_conditions list to has_chronic_conditions
        if 'chronic_conditions' in data and 'has_chronic_conditions' not in data:
            chronic_list = data.get('chronic_conditions', [])
            has_chronic = any(c not in ['none', 'prefer_not_to_say'] for c in chronic_list)
            data['has_chronic_conditions'] = has_chronic
            
            # Add to risk_modifiers
            if 'risk_modifiers' not in data:
                data['risk_modifiers'] = {}
            if has_chronic:
                data['risk_modifiers']['chronic_conditions'] = chronic_list
        
        return data

    def _generate_patient_token(self) -> str:
        """
        Generate anonymous patient token

        Returns:
            UUID-based patient token
        """
        return f"PT-{uuid.uuid4().hex[:16].upper()}"

    def detect_red_flags(self, data: Dict[str, Any]) -> List[str]:
        """
        Detect red flag symptoms from input data - UPDATED

        Args:
            data: Intake data

        Returns:
            List of detected red flag symptoms
        """
        detected_flags = []

        # Check red_flag_indicators if present
        red_flag_indicators = data.get('red_flag_indicators', {})
        for flag, value in red_flag_indicators.items():
            if value and flag in self.RED_FLAG_SYMPTOMS:
                detected_flags.append(flag)

        # Check complaint text for keywords (basic detection)
        complaint_text = data.get('complaint_text', '').lower()
        red_flag_keywords = {
            'severe_breathing_difficulty': ['can\'t breathe', 'struggling to breathe', 'gasping'],
            'unconscious': ['unconscious', 'passed out', 'not waking'],
            'convulsions': ['convulsions', 'seizure', 'fitting'],
            'severe_bleeding': ['heavy bleeding', 'bleeding a lot'],
        }
        
        for flag, keywords in red_flag_keywords.items():
            for keyword in keywords:
                if keyword in complaint_text:
                    detected_flags.append(flag)
                    break

        return list(set(detected_flags))

    def extract_emergency_indicators(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract emergency-related indicators - UPDATED

        Returns:
            Dictionary with emergency assessment
        """
        red_flags = self.detect_red_flags(data)
        
        # Check severity
        severity = data.get('symptom_severity')
        is_very_severe = severity == 'very_severe'
        
        # Check age group for automatic high risk
        age_group = data.get('age_group')
        high_risk_age = age_group in ['newborn', 'infant', 'elderly']

        return {
            'has_red_flags': len(red_flags) > 0,
            'red_flags': red_flags,
            'red_flag_count': len(red_flags),
            'is_emergency': len(red_flags) > 0 or is_very_severe or high_risk_age,
            'immediate_escalation_needed': len(red_flags) > 0,
            'high_risk_age': high_risk_age
        }

    def get_validation_summary(self) -> Dict[str, Any]:
        """
        Get summary of validation results

        Returns:
            Dictionary with validation summary
        """
        return {
            'is_valid': len(self.errors) == 0,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
            'errors': self.errors,
            'warnings': self.warnings,
        }


# Convenience function for external use
def validate_triage_intake(data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], List[str]]:
    """
    Validate triage intake data

    Args:
        data: Raw intake data

    Returns:
        Tuple of (is_valid, cleaned_data, errors)
    """
    tool = IntakeValidationTool()
    return tool.validate(data)


def validate_conversation_update(data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], List[str]]:
    """
    Validate conversation update data (partial updates during conversation)
    
    Args:
        data: Partial update data

    Returns:
        Tuple of (is_valid, cleaned_data, errors)
    """
    tool = IntakeValidationTool()
    
    # Override required fields for conversation updates
    original_required = tool.REQUIRED_FIELDS.copy()
    tool.REQUIRED_FIELDS = []  # No required fields for updates
    
    result = tool.validate(data)
    
    # Restore original required fields
    tool.REQUIRED_FIELDS = original_required
    
    return result