"""
Tool 1: Intake & Validation Tool
Receives patient-submitted data and validates completeness and schema correctness
"""

from typing import Dict, Any, List, Tuple
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
import uuid



class IntakeValidationTool:
    """
    Validates and processes incoming triage data
    """

    # Required fields
    REQUIRED_FIELDS = [
        'age_range',
        'district',
        'primary_symptom',
        'symptom_severity',
        'symptom_duration',
        'condition_occurrence',
        'consent_medical_triage',
        'consent_data_sharing',
        'consent_follow_up',
    ]

    # Field choices validation
    VALID_CHOICES = {
        'age_range': ['under_5', '5_12', '13_17', '18_30', '31_50', '51_plus'],
        'sex': ['male', 'female', 'prefer_not_to_say'],
        'primary_symptom': [
            'fever', 'headache', 'chest_pain', 'difficulty_breathing',
            'abdominal_pain', 'vomiting', 'diarrhea', 'injury_trauma',
            'skin_problem', 'other'
        ],
        'secondary_symptoms': [
            'cough', 'fatigue', 'dizziness', 'nausea', 'body_weakness',
            'swelling', 'bleeding', 'loss_of_appetite', 'none'
        ],
        'symptom_severity': ['mild', 'moderate', 'severe', 'very_severe'],
        'symptom_duration': [
            'today', '1_3_days', '4_7_days', 'more_than_1_week', 'more_than_1_month'
        ],
        'symptom_pattern': ['getting_better', 'staying_same', 'getting_worse', 'comes_and_goes'],
        'condition_occurrence': ['first_occurrence', 'happened_before', 'long_term'],
        'chronic_conditions': [
            'hypertension', 'diabetes', 'asthma', 'heart_disease',
            'epilepsy', 'sickle_cell', 'other_chronic', 'none', 'prefer_not_to_say'
        ],
        'current_medication': ['yes', 'no', 'not_sure'],
        'has_allergies': ['yes', 'no', 'not_sure'],
        'allergy_types': ['medication', 'food', 'environmental'],
        'pregnancy_status': ['yes', 'no', 'not_applicable', 'prefer_not_to_say'],
    }

    # Red flag symptoms
    RED_FLAG_SYMPTOMS = [
        'difficulty_breathing',
        'chest_pain',
        'loss_of_consciousness',
        'convulsions',
        'severe_bleeding',
        'confusion',
        'high_fever_unresponsive',
    ]

    def __init__(self):
        self.errors = []
        self.warnings = []

    def validate(self, data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], List[str]]:
        """
        Validate incoming triage data

        Args:
            data: Raw intake data dictionary

        Returns:
            Tuple of (is_valid, cleaned_data, errors)
        """
        self.errors = []
        self.warnings = []

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

        # Validate text length
        self._validate_text_lengths(data)

        # Clean and prepare data
        cleaned_data = self._clean_data(data) if not self.errors else {}

        return (len(self.errors) == 0, cleaned_data, self.errors)

    def _validate_required_fields(self, data: Dict[str, Any]) -> None:
        """Check all required fields are present"""
        for field in self.REQUIRED_FIELDS:
            if field not in data or data[field] is None or data[field] == '':
                self.errors.append(f"Required field '{field}' is missing or empty")

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
            'location_consent'
        ]

        for field in boolean_fields:
            if field in data and not isinstance(data[field], bool):
                self.errors.append(f"Field '{field}' must be a boolean (true/false)")

        # Array fields
        array_fields = ['secondary_symptoms', 'chronic_conditions', 'allergy_types']
        for field in array_fields:
            if field in data and not isinstance(data[field], list):
                self.errors.append(f"Field '{field}' must be an array/list")

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

    def _validate_consent(self, data: Dict[str, Any]) -> None:
        """Validate consent requirements"""
        # All consents must be True
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
        # If has_allergies is 'yes', allergy_types should be provided
        if data.get('has_allergies') == 'yes':
            if not data.get('allergy_types') or len(data.get('allergy_types', [])) == 0:
                self.warnings.append(
                    "Allergy types should be specified when has_allergies is 'yes'"
                )

        # If location_consent is True, location coordinates should be provided
        if data.get('location_consent'):
            if not (data.get('device_location_lat') and data.get('device_location_lng')):
                self.warnings.append(
                    "Location coordinates missing despite location consent being given"
                )

        # Pregnancy status validation based on sex
        if data.get('sex') == 'male' and data.get('pregnancy_status') == 'yes':
            self.errors.append("Pregnancy status cannot be 'yes' for male patients")

    def _validate_text_lengths(self, data: Dict[str, Any]) -> None:
        """Validate text field lengths"""
        # Additional description limited to 500 characters
        if 'additional_description' in data:
            desc = data['additional_description']
            if desc and len(desc) > 500:
                self.errors.append(
                    f"Additional description exceeds 500 character limit ({len(desc)} characters)"
                )

        # District and subcounty reasonable lengths
        if 'district' in data and len(data['district']) > 100:
            self.errors.append("District name too long (max 100 characters)")

        if 'subcounty' in data and data.get('subcounty') and len(data['subcounty']) > 100:
            self.errors.append("Subcounty name too long (max 100 characters)")

    def _clean_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean and prepare data for storage

        Returns:
            Cleaned data dictionary
        """
        cleaned = data.copy()

        # Generate patient token if not provided
        # if 'patient_token' not in cleaned or not cleaned['patient_token']:
        #     cleaned['patient_token'] = self._generate_patient_token()

        # Normalize text fields
        text_fields = ['district', 'subcounty', 'additional_description']
        for field in text_fields:
            if field in cleaned and cleaned[field]:
                cleaned[field] = cleaned[field].strip()

        # Ensure array fields are lists
        array_fields = ['secondary_symptoms', 'chronic_conditions', 'allergy_types']
        for field in array_fields:
            if field not in cleaned:
                cleaned[field] = []
            elif not isinstance(cleaned[field], list):
                cleaned[field] = [cleaned[field]]

        # Remove 'none' from chronic conditions if other conditions exist
        if 'chronic_conditions' in cleaned:
            conditions = cleaned['chronic_conditions']
            if 'none' in conditions and len(conditions) > 1:
                cleaned['chronic_conditions'] = [c for c in conditions if c != 'none']

        # Set default session status
        # cleaned['session_status'] = 'in_progress'

        # Set channel if not provided
        if 'channel' not in cleaned:
            cleaned['channel'] = 'web'  # Default to web

        return cleaned

    def _generate_patient_token(self) -> str:
        """
        Generate anonymous patient token

        Returns:
            UUID-based patient token
        """
        return f"PT-{uuid.uuid4().hex[:16].upper()}"

    def detect_red_flags(self, data: Dict[str, Any]) -> List[str]:
        """
        Detect red flag symptoms from input data

        Args:
            data: Intake data

        Returns:
            List of detected red flag symptoms
        """
        detected_flags = []

        # Check primary symptom
        if data.get('primary_symptom') in ['chest_pain', 'difficulty_breathing']:
            detected_flags.append(data['primary_symptom'])

        # Check secondary symptoms
        secondary = data.get('secondary_symptoms', [])
        for symptom in secondary:
            if symptom in self.RED_FLAG_SYMPTOMS:
                detected_flags.append(symptom)

        # Check severity combined with certain symptoms
        if data.get('symptom_severity') in ['severe', 'very_severe']:
            if data.get('primary_symptom') == 'fever':
                # Check if it's unresponsive to medication
                if data.get('symptom_duration') in ['4_7_days', 'more_than_1_week', 'more_than_1_month']:
                    detected_flags.append('high_fever_unresponsive')

        return list(set(detected_flags))  # Remove duplicates

    def extract_emergency_indicators(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract emergency-related indicators

        Returns:
            Dictionary with emergency assessment
        """
        red_flags = self.detect_red_flags(data)

        return {
            'has_red_flags': len(red_flags) > 0,
            'red_flags': red_flags,
            'red_flag_count': len(red_flags),
            'is_emergency': len(red_flags) > 0 or data.get('symptom_severity') == 'very_severe',
            'immediate_escalation_needed': len(red_flags) > 0
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