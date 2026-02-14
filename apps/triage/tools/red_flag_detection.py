"""
Tool 3: Red-Flag Detection Tool
Immediately identifies emergency indicators and triggers override
"""

from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum


class EmergencySeverity(Enum):
    """Emergency severity levels"""
    CRITICAL = "critical"  # Life-threatening
    URGENT = "urgent"  # Needs immediate attention
    WARNING = "warning"  # Concerning but not immediate


@dataclass
class RedFlag:
    """Red flag symptom definition"""
    name: str
    severity: EmergencySeverity
    description: str
    action_required: str


class RedFlagDetectionTool:
    """
    Detects emergency red-flag symptoms that require immediate escalation
    """

    # Define all red flag symptoms with their severity
    RED_FLAGS = {
        'difficulty_breathing': RedFlag(
            name='difficulty_breathing',
            severity=EmergencySeverity.CRITICAL,
            description='Severe respiratory distress',
            action_required='Immediate emergency care required'
        ),
        'chest_pain': RedFlag(
            name='chest_pain',
            severity=EmergencySeverity.CRITICAL,
            description='Chest pain (possible cardiac event)',
            action_required='Immediate emergency care required'
        ),
        'loss_of_consciousness': RedFlag(
            name='loss_of_consciousness',
            severity=EmergencySeverity.CRITICAL,
            description='Loss of consciousness or altered mental state',
            action_required='Immediate emergency care required'
        ),
        'convulsions': RedFlag(
            name='convulsions',
            severity=EmergencySeverity.CRITICAL,
            description='Seizures or convulsions',
            action_required='Immediate emergency care required'
        ),
        'severe_bleeding': RedFlag(
            name='severe_bleeding',
            severity=EmergencySeverity.CRITICAL,
            description='Uncontrolled or severe bleeding',
            action_required='Immediate emergency care required'
        ),
        'confusion': RedFlag(
            name='confusion',
            severity=EmergencySeverity.URGENT,
            description='Confusion or inability to communicate clearly',
            action_required='Urgent medical attention required'
        ),
        'high_fever_unresponsive': RedFlag(
            name='high_fever_unresponsive',
            severity=EmergencySeverity.URGENT,
            description='High fever not responding to medication',
            action_required='Urgent medical attention required'
        ),
    }

    # Symptom combinations that indicate red flags
    SYMPTOM_COMBINATIONS = {
        'respiratory_distress': {
            'symptoms': ['difficulty_breathing', 'chest_pain'],
            'severity': EmergencySeverity.CRITICAL
        },
        'neurological_emergency': {
            'symptoms': ['loss_of_consciousness', 'convulsions', 'confusion'],
            'severity': EmergencySeverity.CRITICAL
        },
        'hemorrhage': {
            'symptoms': ['severe_bleeding'],
            'severity': EmergencySeverity.CRITICAL
        },
    }

    def __init__(self):
        self.detected_flags = []
        self.emergency_override = False

    def detect(self, triage_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect red flags in triage data

        Args:
            triage_data: Validated triage intake data

        Returns:
            Dictionary with detection results
        """
        self.detected_flags = []
        self.emergency_override = False

        # Check primary symptom
        self._check_primary_symptom(triage_data)

        # Check secondary symptoms
        self._check_secondary_symptoms(triage_data)

        # Check severity-based flags
        self._check_severity_flags(triage_data)

        # Check symptom combinations
        self._check_symptom_combinations(triage_data)

        # Check age-specific red flags
        self._check_age_specific_flags(triage_data)

        # Determine emergency override
        self._determine_emergency_override()

        return self._build_detection_result()

    def _check_primary_symptom(self, data: Dict[str, Any]) -> None:
        """Check if primary symptom is a red flag"""
        primary = data.get('primary_symptom')

        if primary in self.RED_FLAGS:
            self.detected_flags.append({
                'flag': self.RED_FLAGS[primary],
                'source': 'primary_symptom',
                'confidence': 1.0
            })

    def _check_secondary_symptoms(self, data: Dict[str, Any]) -> None:
        """Check secondary symptoms for red flags"""
        secondary = data.get('secondary_symptoms', [])

        for symptom in secondary:
            # Map common symptom names to red flags
            symptom_mapping = {
                'cough': None,  # Not a red flag by itself
                'bleeding': 'severe_bleeding',  # Could be red flag
                'dizziness': 'confusion',  # Could indicate confusion
            }

            flag_name = symptom_mapping.get(symptom, symptom)

            if flag_name and flag_name in self.RED_FLAGS:
                # Check if it's truly severe
                severity = data.get('symptom_severity')
                if severity in ['severe', 'very_severe']:
                    self.detected_flags.append({
                        'flag': self.RED_FLAGS[flag_name],
                        'source': 'secondary_symptoms',
                        'confidence': 0.9
                    })

    def _check_severity_flags(self, data: Dict[str, Any]) -> None:
        """Check for red flags based on severity"""
        severity = data.get('symptom_severity')
        primary = data.get('primary_symptom')

        # Very severe symptoms are always concerning
        if severity == 'very_severe':
            # Chest pain + very severe = critical
            if primary == 'chest_pain':
                if 'chest_pain' not in [f['flag'].name for f in self.detected_flags]:
                    self.detected_flags.append({
                        'flag': self.RED_FLAGS['chest_pain'],
                        'source': 'severity_escalation',
                        'confidence': 1.0
                    })

            # Difficulty breathing + very severe = critical
            elif primary == 'difficulty_breathing':
                if 'difficulty_breathing' not in [f['flag'].name for f in self.detected_flags]:
                    self.detected_flags.append({
                        'flag': self.RED_FLAGS['difficulty_breathing'],
                        'source': 'severity_escalation',
                        'confidence': 1.0
                    })

        # Severe fever for extended duration
        if primary == 'fever' and severity in ['severe', 'very_severe']:
            duration = data.get('symptom_duration')
            if duration in ['4_7_days', 'more_than_1_week', 'more_than_1_month']:
                self.detected_flags.append({
                    'flag': self.RED_FLAGS['high_fever_unresponsive'],
                    'source': 'duration_severity',
                    'confidence': 0.85
                })

    def _check_symptom_combinations(self, data: Dict[str, Any]) -> None:
        """Check for dangerous symptom combinations"""
        all_symptoms = [data.get('primary_symptom')] + data.get('secondary_symptoms', [])

        # Check for respiratory distress combination
        if 'difficulty_breathing' in all_symptoms and 'chest_pain' in all_symptoms:
            self.detected_flags.append({
                'flag': RedFlag(
                    name='respiratory_cardiac_distress',
                    severity=EmergencySeverity.CRITICAL,
                    description='Combined respiratory and cardiac symptoms',
                    action_required='Immediate emergency care - possible cardiac/respiratory failure'
                ),
                'source': 'symptom_combination',
                'confidence': 1.0
            })

    def _check_age_specific_flags(self, data: Dict[str, Any]) -> None:
        """Check age-specific red flags"""
        age_range = data.get('age_range')
        severity = data.get('symptom_severity')
        primary = data.get('primary_symptom')

        # Infants/young children with severe symptoms
        if age_range == 'under_5':
            if severity in ['severe', 'very_severe']:
                # Any severe symptom in under-5 is more concerning
                if primary in ['fever', 'vomiting', 'diarrhea', 'difficulty_breathing']:
                    self.detected_flags.append({
                        'flag': RedFlag(
                            name='pediatric_emergency',
                            severity=EmergencySeverity.URGENT,
                            description=f'Severe {primary} in child under 5',
                            action_required='Urgent pediatric care required'
                        ),
                        'source': 'age_specific',
                        'confidence': 0.9
                    })

        # Elderly with certain symptoms
        elif age_range == '51_plus':
            if primary in ['chest_pain', 'difficulty_breathing', 'confusion']:
                if severity in ['moderate', 'severe', 'very_severe']:
                    self.detected_flags.append({
                        'flag': RedFlag(
                            name='geriatric_emergency',
                            severity=EmergencySeverity.URGENT,
                            description=f'{primary} in elderly patient',
                            action_required='Urgent geriatric assessment required'
                        ),
                        'source': 'age_specific',
                        'confidence': 0.85
                    })

    def _determine_emergency_override(self) -> None:
        """Determine if emergency override should be triggered"""
        # Any CRITICAL severity flag triggers override
        for flag_data in self.detected_flags:
            if flag_data['flag'].severity == EmergencySeverity.CRITICAL:
                self.emergency_override = True
                return

        # Multiple URGENT flags trigger override
        urgent_count = sum(
            1 for f in self.detected_flags
            if f['flag'].severity == EmergencySeverity.URGENT
        )
        if urgent_count >= 2:
            self.emergency_override = True

    def _build_detection_result(self) -> Dict[str, Any]:
        """Build final detection result"""
        # Get unique flags (avoid duplicates)
        unique_flags = {}
        for flag_data in self.detected_flags:
            flag_name = flag_data['flag'].name
            if flag_name not in unique_flags:
                unique_flags[flag_name] = flag_data
            else:
                # Keep the one with higher confidence
                if flag_data['confidence'] > unique_flags[flag_name]['confidence']:
                    unique_flags[flag_name] = flag_data

        flags_list = list(unique_flags.values())

        # Determine highest severity
        highest_severity = None
        if flags_list:
            severities = [f['flag'].severity for f in flags_list]
            if EmergencySeverity.CRITICAL in severities:
                highest_severity = EmergencySeverity.CRITICAL
            elif EmergencySeverity.URGENT in severities:
                highest_severity = EmergencySeverity.URGENT
            else:
                highest_severity = EmergencySeverity.WARNING

        # Build individual flag details
        flag_details = {}
        for flag_name in self.RED_FLAGS.keys():
            flag_details[flag_name] = any(
                f['flag'].name == flag_name for f in flags_list
            )

        return {
            'has_red_flags': len(flags_list) > 0,
            'detected_flags_count': len(flags_list),
            'detected_flags': [f['flag'].name for f in flags_list],
            'emergency_override': self.emergency_override,
            'highest_severity': highest_severity.value if highest_severity else None,
            'flag_details': flag_details,
            'flags_with_context': [
                {
                    'name': f['flag'].name,
                    'severity': f['flag'].severity.value,
                    'description': f['flag'].description,
                    'action_required': f['flag'].action_required,
                    'source': f['source'],
                    'confidence': f['confidence']
                }
                for f in flags_list
            ],
            'requires_immediate_action': self.emergency_override,
            'recommended_facility_type': 'emergency' if self.emergency_override else 'hospital',
            'detection_method': self._get_detection_method(flags_list)
        }

    def _get_detection_method(self, flags_list: List[Dict]) -> str:
        """Determine primary detection method"""
        if not flags_list:
            return 'none'

        sources = [f['source'] for f in flags_list]

        if 'primary_symptom' in sources:
            return 'user_input'
        elif 'severity_escalation' in sources:
            return 'rule_based'
        elif 'symptom_combination' in sources:
            return 'rule_based'
        else:
            return 'ai_detected'

    def get_emergency_message(self, detection_result: Dict[str, Any]) -> str:
        """
        Generate emergency message for patient

        Args:
            detection_result: Result from detect()

        Returns:
            Emergency message string
        """
        if not detection_result['has_red_flags']:
            return ""

        if detection_result['emergency_override']:
            return (
                "⚠️ EMERGENCY: Your symptoms indicate you need immediate medical attention. "
                "Please proceed to the nearest emergency facility immediately or call emergency services."
            )
        elif detection_result['highest_severity'] == EmergencySeverity.URGENT.value:
            return (
                "⚠️ URGENT: Your symptoms require urgent medical attention. "
                "Please seek care at a health facility as soon as possible."
            )
        else:
            return (
                "⚠️ WARNING: Your symptoms are concerning. "
                "We recommend seeking medical evaluation soon."
            )

    def get_facility_recommendations(self, detection_result: Dict[str, Any]) -> List[str]:
        """
        Get facility type recommendations based on red flags

        Returns:
            List of recommended facility types
        """
        if detection_result['emergency_override']:
            return ['emergency_department', 'hospital']
        elif detection_result['highest_severity'] == EmergencySeverity.URGENT.value:
            return ['hospital', 'health_center_iv']
        else:
            return ['health_center_iii', 'health_center_iv', 'hospital']


# Convenience function for external use
def detect_red_flags(triage_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Detect red flags in triage data

    Args:
        triage_data: Validated triage intake data

    Returns:
        Detection results dictionary
    """
    tool = RedFlagDetectionTool()
    return tool.detect(triage_data)