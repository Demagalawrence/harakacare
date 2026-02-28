"""
Tool 3: Red-Flag Detection Tool - UPDATED
Implements WHO ABCD danger signs for age-adaptive triage
Immediately identifies emergency indicators and triggers override
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class EmergencySeverity(Enum):
    """Emergency severity levels - based on WHO guidelines"""
    CRITICAL = "critical"      # Life-threatening - immediate action
    URGENT = "urgent"           # Needs urgent attention (within hours)
    WARNING = "warning"         # Concerning but not immediate


class RedFlagCategory(Enum):
    """WHO ABCD categories"""
    AIRWAY = "airway"           # A - Airway
    BREATHING = "breathing"     # B - Breathing
    CIRCULATION = "circulation" # C - Circulation
    DISABILITY = "disability"   # D - Disability
    AGE_SPECIFIC = "age_specific"  # Special for pediatrics/geriatrics
    PREGNANCY = "pregnancy"     # Obstetric emergencies


@dataclass
class RedFlag:
    """Red flag symptom definition - WHO aligned"""
    name: str
    category: RedFlagCategory
    severity: EmergencySeverity
    description: str
    action_required: str
    age_groups: List[str]  # Which age groups this applies to
    keywords: List[str]     # Keywords to detect in text


class RedFlagDetectionTool:
    """
    Detects emergency red-flag symptoms - UPDATED
    Implements WHO ABCD danger signs and age-adaptive detection
    """

    # ========================================================================
    # WHO ABCD DANGER SIGNS (complete set)
    # ========================================================================
    
    RED_FLAGS = {
        # === AIRWAY (A) ===
        'airway_obstruction': RedFlag(
            name='airway_obstruction',
            category=RedFlagCategory.AIRWAY,
            severity=EmergencySeverity.CRITICAL,
            description='Choking, stridor, cannot speak, difficulty swallowing',
            action_required='IMMEDIATE: Clear airway, emergency care',
            age_groups=['newborn', 'infant', 'child_1_5', 'child_6_12', 'teen', 'adult', 'elderly'],
            keywords=['choking', 'cannot breathe', 'can\'t breathe', 'stridor', 'gasping', 'cannot speak']
        ),
        
        # === BREATHING (B) ===
        'severe_breathing_difficulty': RedFlag(
            name='severe_breathing_difficulty',
            category=RedFlagCategory.BREATHING,
            severity=EmergencySeverity.CRITICAL,
            description='Struggling to breathe, very fast breathing, blue lips',
            action_required='IMMEDIATE: Emergency oxygen/care required',
            age_groups=['newborn', 'infant', 'child_1_5', 'child_6_12', 'teen', 'adult', 'elderly'],
            keywords=['struggling to breathe', 'can\'t breathe', 'gasping', 'blue lips', 'turning blue']
        ),
        
        'chest_indrawing': RedFlag(
            name='chest_indrawing',
            category=RedFlagCategory.BREATHING,
            severity=EmergencySeverity.CRITICAL,
            description='Visible chest pulling in with breathing (children)',
            action_required='IMMEDIATE: Child needs urgent care',
            age_groups=['newborn', 'infant', 'child_1_5'],
            keywords=['chest pulling', 'ribs show', 'difficulty breathing']
        ),
        
        'fast_breathing': RedFlag(
            name='fast_breathing',
            category=RedFlagCategory.BREATHING,
            severity=EmergencySeverity.URGENT,
            description='Abnormally fast breathing rate',
            action_required='URGENT: Assess for pneumonia/sepsis',
            age_groups=['newborn', 'infant', 'child_1_5', 'child_6_12'],
            keywords=['fast breathing', 'breathing fast', 'panting']
        ),
        
        # === CIRCULATION (C) ===
        'severe_bleeding': RedFlag(
            name='severe_bleeding',
            category=RedFlagCategory.CIRCULATION,
            severity=EmergencySeverity.CRITICAL,
            description='Heavy bleeding, blood loss',
            action_required='IMMEDIATE: Control bleeding, emergency care',
            age_groups=['newborn', 'infant', 'child_1_5', 'child_6_12', 'teen', 'adult', 'elderly'],
            keywords=['heavy bleeding', 'bleeding a lot', 'blood pouring', 'hemorrhage']
        ),
        
        'signs_of_shock': RedFlag(
            name='signs_of_shock',
            category=RedFlagCategory.CIRCULATION,
            severity=EmergencySeverity.CRITICAL,
            description='Very pale/weak, collapse, cold extremities, weak pulse',
            action_required='IMMEDIATE: Shock management, emergency care',
            age_groups=['newborn', 'infant', 'child_1_5', 'child_6_12', 'teen', 'adult', 'elderly'],
            keywords=['very pale', 'cold hands and feet', 'collapsed', 'weak', 'fainted']
        ),
        
        # === DISABILITY (D) ===
        'unconscious': RedFlag(
            name='unconscious',
            category=RedFlagCategory.DISABILITY,
            severity=EmergencySeverity.CRITICAL,
            description='Unconscious, unresponsive, cannot be woken',
            action_required='IMMEDIATE: Emergency resuscitation',
            age_groups=['newborn', 'infant', 'child_1_5', 'child_6_12', 'teen', 'adult', 'elderly'],
            keywords=['unconscious', 'passed out', 'not waking', 'unresponsive', 'coma']
        ),
        
        'convulsions': RedFlag(
            name='convulsions',
            category=RedFlagCategory.DISABILITY,
            severity=EmergencySeverity.CRITICAL,
            description='Seizures, convulsions, fitting',
            action_required='IMMEDIATE: Seizure management, emergency care',
            age_groups=['newborn', 'infant', 'child_1_5', 'child_6_12', 'teen', 'adult', 'elderly'],
            keywords=['convulsions', 'seizure', 'fitting', 'shaking uncontrollably', 'epilepsy']
        ),
        
        'confusion': RedFlag(
            name='confusion',
            category=RedFlagCategory.DISABILITY,
            severity=EmergencySeverity.URGENT,
            description='Confusion, disorientation, cannot recognize people',
            action_required='URGENT: Neurological assessment',
            age_groups=['teen', 'adult', 'elderly'],
            keywords=['confused', 'disoriented', 'not making sense', 'doesn\'t know where they are']
        ),
        
        'stroke_symptoms': RedFlag(
            name='stroke_symptoms',
            category=RedFlagCategory.DISABILITY,
            severity=EmergencySeverity.CRITICAL,
            description='Face droop, arm weakness, speech difficulty, sudden onset',
            action_required='IMMEDIATE: Stroke protocol, emergency care',
            age_groups=['adult', 'elderly'],
            keywords=['face drooping', 'one sided weakness', 'slurred speech', 'cannot smile']
        ),
        
        # === PEDIATRIC SPECIFIC (WHO IMCI) ===
        'unable_to_drink': RedFlag(
            name='unable_to_drink',
            category=RedFlagCategory.AGE_SPECIFIC,
            severity=EmergencySeverity.URGENT,
            description='Child unable to drink or breastfeed',
            action_required='URGENT: Assess for severe illness',
            age_groups=['newborn', 'infant', 'child_1_5'],
            keywords=['not drinking', 'refusing to drink', 'cannot breastfeed', 'not feeding']
        ),
        
        'vomits_everything': RedFlag(
            name='vomits_everything',
            category=RedFlagCategory.AGE_SPECIFIC,
            severity=EmergencySeverity.URGENT,
            description='Child vomits everything given',
            action_required='URGENT: Assess for dehydration/sepsis',
            age_groups=['newborn', 'infant', 'child_1_5'],
            keywords=['vomits everything', 'cannot keep down', 'throws up everything']
        ),
        
        'lethargic_floppy': RedFlag(
            name='lethargic_floppy',
            category=RedFlagCategory.AGE_SPECIFIC,
            severity=EmergencySeverity.CRITICAL,
            description='Baby unusually sleepy, floppy, difficult to wake',
            action_required='IMMEDIATE: Neonatal emergency',
            age_groups=['newborn', 'infant'],
            keywords=['floppy', 'very sleepy', 'difficult to wake', 'limp', 'not moving']
        ),
        
        # === PREGNANCY SPECIFIC ===
        'pregnancy_emergency': RedFlag(
            name='pregnancy_emergency',
            category=RedFlagCategory.PREGNANCY,
            severity=EmergencySeverity.CRITICAL,
            description='Heavy vaginal bleeding, severe abdominal pain in pregnancy',
            action_required='IMMEDIATE: Obstetric emergency',
            age_groups=['teen', 'adult'],
            keywords=['pregnancy bleeding', 'vaginal bleeding', 'pregnant and bleeding']
        ),
        
        # === OTHER CRITICAL ===
        'severe_pain': RedFlag(
            name='severe_pain',
            category=RedFlagCategory.DISABILITY,
            severity=EmergencySeverity.URGENT,
            description='Severe uncontrolled pain',
            action_required='URGENT: Pain management, assess cause',
            age_groups=['child_6_12', 'teen', 'adult', 'elderly'],
            keywords=['worst pain', 'unbearable pain', 'screaming in pain']
        ),
    }

    # Age group hierarchy for inheritance
    AGE_HIERARCHY = {
        'newborn': ['newborn', 'infant'],
        'infant': ['infant', 'child_1_5'],
        'child_1_5': ['child_1_5', 'child_6_12'],
        'child_6_12': ['child_6_12', 'teen'],
        'teen': ['teen', 'adult'],
        'adult': ['adult'],
        'elderly': ['elderly', 'adult'],
    }

    def __init__(self):
        self.detected_flags = []
        self.emergency_override = False
        self.detection_turn = None

    def detect(self, session, triage_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect red flags in triage data - UPDATED

        Args:
            session: TriageSession object (to check existing flags)
            triage_data: Validated triage intake data

        Returns:
            Dictionary with detection results
        """
        self.detected_flags = []
        self.emergency_override = False
        
        # Get age group from session or data
        age_group = getattr(session, 'age_group', triage_data.get('age_group', 'adult'))
        sex = getattr(session, 'sex', triage_data.get('sex', 'other'))
        
        print(f"\n🔍 RED FLAG DETECTION - Age: {age_group}, Sex: {sex}")

        # ====================================================================
        # Check all detection sources
        # ====================================================================
        
        # 1. Check structured symptom indicators (from adaptive questions)
        self._check_symptom_indicators(session, triage_data, age_group)
        
        # 2. Check complaint text for keywords (if available)
        self._check_complaint_text(session, triage_data, age_group)
        
        # 3. Check severity and duration combinations
        self._check_severity_duration(session, triage_data, age_group, sex)
        
        # 4. Check age-specific red flags
        self._check_age_specific_flags(session, triage_data, age_group)
        
        # 5. Check pregnancy-specific flags (if applicable)
        if sex == 'female':
            self._check_pregnancy_flags(session, triage_data)
        
        # 6. Check for existing red flags in session
        self._check_existing_red_flags(session)

        # ====================================================================
        # Determine emergency override and build result
        # ====================================================================
        
        self._determine_emergency_override()
        
        # Update detection turn if new flags detected
        if self.detected_flags and not getattr(session, 'red_flag_detected_at_turn', None):
            self.detection_turn = getattr(session, 'conversation_turns', 1) + 1

        return self._build_detection_result(session)

    def _check_symptom_indicators(self, session, data: Dict[str, Any], age_group: str) -> None:
        """Check structured symptom indicators for red flags"""
        symptom_indicators = getattr(session, 'symptom_indicators', {}) or {}
        
        # If new indicators in data, merge them
        if 'symptom_indicators' in data:
            symptom_indicators.update(data['symptom_indicators'])
        
        # Mapping from indicator keys to red flag names
        indicator_mapping = {
            'breathing_difficulty': 'severe_breathing_difficulty',
            'chest_indrawing': 'chest_indrawing',
            'unconscious': 'unconscious',
            'convulsions': 'convulsions',
            'confusion': 'confusion',
            'bleeding': 'severe_bleeding',
            'pale': 'signs_of_shock',
            'weak': 'signs_of_shock',
            'vomiting_all': 'vomits_everything',
            'not_drinking': 'unable_to_drink',
            'lethargic': 'lethargic_floppy',
        }
        
        for indicator, flag_name in indicator_mapping.items():
            if symptom_indicators.get(indicator, False):
                if flag_name in self.RED_FLAGS:
                    flag = self.RED_FLAGS[flag_name]
                    
                    # Check if applicable to this age group
                    if self._is_applicable_to_age(flag, age_group):
                        self._add_detected_flag(
                            flag=flag,
                            source='symptom_indicator',
                            confidence=1.0,
                            context={'indicator': indicator}
                        )
                        print(f"  ⚠️ Red flag from indicator: {flag_name}")

    def _check_complaint_text(self, session, data: Dict[str, Any], age_group: str) -> None:
        """Check complaint text for red flag keywords"""
        complaint_text = data.get('complaint_text', '') or getattr(session, 'complaint_text', '')
        
        if not complaint_text:
            return
        
        complaint_text = complaint_text.lower()
        
        for flag_name, flag in self.RED_FLAGS.items():
            # Skip if already detected
            if any(f['flag'].name == flag_name for f in self.detected_flags):
                continue
            
            # Check if applicable to age group
            if not self._is_applicable_to_age(flag, age_group):
                continue
            
            # Check for keywords
            for keyword in flag.keywords:
                if keyword in complaint_text:
                    self._add_detected_flag(
                        flag=flag,
                        source='keyword_detection',
                        confidence=0.8,
                        context={'keyword': keyword}
                    )
                    print(f"  ⚠️ Red flag from keyword '{keyword}': {flag_name}")
                    break

    def _check_severity_duration(self, session, data: Dict[str, Any], age_group: str, sex: str) -> None:
        """Check severity and duration combinations for red flags"""
        severity = data.get('symptom_severity') or getattr(session, 'symptom_severity', None)
        duration = data.get('symptom_duration') or getattr(session, 'symptom_duration', None)
        complaint_group = data.get('complaint_group') or getattr(session, 'complaint_group', None)
        
        if not severity or not complaint_group:
            return
        
        # Very severe symptoms are always concerning
        if severity == 'very_severe':
            # Map complaint groups to potential red flags
            severity_flags = {
                'breathing': 'severe_breathing_difficulty',
                'chest_pain': 'airway_obstruction',  # Severe chest pain can indicate airway
                'headache': 'stroke_symptoms',       # Severe headache could be stroke
                'abdominal': 'severe_pain',
            }
            
            if complaint_group in severity_flags:
                flag_name = severity_flags[complaint_group]
                if flag_name in self.RED_FLAGS:
                    flag = self.RED_FLAGS[flag_name]
                    if self._is_applicable_to_age(flag, age_group):
                        self._add_detected_flag(
                            flag=flag,
                            source='severity_escalation',
                            confidence=0.9,
                            context={'severity': severity, 'complaint': complaint_group}
                        )
                        print(f"  ⚠️ Severity escalation: {flag_name}")
        
        # Prolonged severe symptoms
        if severity in ['severe', 'very_severe'] and duration in ['more_than_1_week', 'more_than_1_month']:
            # Any prolonged severe symptom is concerning
            self._add_detected_flag(
                flag=RedFlag(
                    name='prolonged_severe_illness',
                    category=RedFlagCategory.WARNING,
                    severity=EmergencySeverity.URGENT,
                    description=f'Prolonged severe {complaint_group} symptoms',
                    action_required='URGENT: Medical evaluation needed',
                    age_groups=['newborn', 'infant', 'child_1_5', 'child_6_12', 'teen', 'adult', 'elderly'],
                    keywords=[]
                ),
                source='prolonged_severe',
                confidence=0.85,
                context={'duration': duration, 'severity': severity}
            )
            print(f"  ⚠️ Prolonged severe symptoms")

    def _check_age_specific_flags(self, session, data: Dict[str, Any], age_group: str) -> None:
        """Check age-specific red flags (WHO IMCI)"""
        
        # Infants and young children
        if age_group in ['newborn', 'infant', 'child_1_5']:
            symptom_indicators = getattr(session, 'symptom_indicators', {}) or {}
            
            # Check for fast breathing (pneumonia risk)
            if symptom_indicators.get('fast_breathing', False):
                self._add_detected_flag(
                    flag=self.RED_FLAGS['fast_breathing'],
                    source='age_specific',
                    confidence=0.9,
                    context={'age_group': age_group}
                )
            
            # Check for inability to drink
            if symptom_indicators.get('not_drinking', False):
                self._add_detected_flag(
                    flag=self.RED_FLAGS['unable_to_drink'],
                    source='age_specific',
                    confidence=0.9,
                    context={'age_group': age_group}
                )
        
        # Elderly patients
        if age_group == 'elderly':
            symptom_indicators = getattr(session, 'symptom_indicators', {}) or {}
            
            # Check for confusion (often infection in elderly)
            if symptom_indicators.get('confusion', False):
                self._add_detected_flag(
                    flag=self.RED_FLAGS['confusion'],
                    source='age_specific',
                    confidence=0.85,
                    context={'age_group': 'elderly'}
                )

    def _check_pregnancy_flags(self, session, data: Dict[str, Any]) -> None:
        """Check pregnancy-specific red flags"""
        pregnancy_status = data.get('pregnancy_status') or getattr(session, 'pregnancy_status', None)
        symptom_indicators = getattr(session, 'symptom_indicators', {}) or {}
        
        if pregnancy_status in ['yes', 'possible']:
            # Check for bleeding in pregnancy
            if symptom_indicators.get('vaginal_bleeding', False):
                self._add_detected_flag(
                    flag=self.RED_FLAGS['pregnancy_emergency'],
                    source='pregnancy_specific',
                    confidence=1.0,
                    context={'pregnancy_status': pregnancy_status}
                )
            
            # Check for severe abdominal pain in pregnancy
            if symptom_indicators.get('severe_abdominal_pain', False):
                self._add_detected_flag(
                    flag=self.RED_FLAGS['pregnancy_emergency'],
                    source='pregnancy_specific',
                    confidence=0.9,
                    context={'pregnancy_status': pregnancy_status}
                )

    def _check_existing_red_flags(self, session) -> None:
        """Check for existing red flags in session"""
        existing_indicators = getattr(session, 'red_flag_indicators', {}) or {}
        
        for flag_name, is_detected in existing_indicators.items():
            if is_detected and flag_name in self.RED_FLAGS:
                flag = self.RED_FLAGS[flag_name]
                # Check if already added
                if not any(f['flag'].name == flag_name for f in self.detected_flags):
                    self._add_detected_flag(
                        flag=flag,
                        source='existing_session',
                        confidence=1.0,
                        context={'from_session': True}
                    )

    def _is_applicable_to_age(self, flag: RedFlag, age_group: str) -> bool:
        """Check if a red flag is applicable to given age group"""
        # Get applicable age groups for this flag
        applicable = flag.age_groups
        
        # Expand based on hierarchy
        expanded = []
        for age in applicable:
            expanded.extend(self.AGE_HIERARCHY.get(age, [age]))
        
        return age_group in expanded

    def _add_detected_flag(self, flag: RedFlag, source: str, confidence: float, context: dict) -> None:
        """Add a detected flag with metadata"""
        self.detected_flags.append({
            'flag': flag,
            'source': source,
            'confidence': confidence,
            'context': context
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

    def _build_detection_result(self, session) -> Dict[str, Any]:
        """Build final detection result with WHO ABCD categories"""
        
        # Build flag details dictionary for session update
        flag_details = {}
        for flag_name in self.RED_FLAGS.keys():
            flag_details[flag_name] = any(
                f['flag'].name == flag_name for f in self.detected_flags
            )
        
        # Count by category
        category_counts = {
            'airway': 0,
            'breathing': 0,
            'circulation': 0,
            'disability': 0,
            'age_specific': 0,
            'pregnancy': 0
        }
        
        for flag_data in self.detected_flags:
            category = flag_data['flag'].category.value
            if category in category_counts:
                category_counts[category] += 1
        
        # Get detected flag names
        detected_names = [f['flag'].name for f in self.detected_flags]
        
        # Determine highest severity
        highest_severity = None
        if self.detected_flags:
            severities = [f['flag'].severity for f in self.detected_flags]
            if EmergencySeverity.CRITICAL in severities:
                highest_severity = EmergencySeverity.CRITICAL
            elif EmergencySeverity.URGENT in severities:
                highest_severity = EmergencySeverity.URGENT
            else:
                highest_severity = EmergencySeverity.WARNING
        
        # Build detailed flags list
        flags_with_context = [
            {
                'name': f['flag'].name,
                'category': f['flag'].category.value,
                'severity': f['flag'].severity.value,
                'description': f['flag'].description,
                'action_required': f['flag'].action_required,
                'source': f['source'],
                'confidence': f['confidence']
            }
            for f in self.detected_flags
        ]
        
        result = {
            'has_red_flags': len(self.detected_flags) > 0,
            'detected_flags_count': len(self.detected_flags),
            'detected_flags': detected_names,
            'red_flag_indicators': flag_details,  # For session update
            'category_counts': category_counts,
            'emergency_override': self.emergency_override,
            'highest_severity': highest_severity.value if highest_severity else None,
            'detection_turn_number': self.detection_turn,
            'flags_with_context': flags_with_context,
            'requires_immediate_action': self.emergency_override,
            'recommended_facility_type': 'emergency' if self.emergency_override else 
                                        ('hospital' if highest_severity == EmergencySeverity.URGENT else 'health_center'),
            'detection_method': self._get_detection_method()
        }
        
        return result

    def _get_detection_method(self) -> str:
        """Determine primary detection method"""
        if not self.detected_flags:
            return 'none'
        
        sources = [f['source'] for f in self.detected_flags]
        
        if 'symptom_indicator' in sources:
            return 'adaptive_question'
        elif 'keyword_detection' in sources:
            return 'user_keywords'
        elif 'severity_escalation' in sources:
            return 'rule_based'
        else:
            return 'continuous_monitoring'

    def get_emergency_message(self, detection_result: Dict[str, Any]) -> str:
        """
        Generate emergency message for patient
        """
        if not detection_result['has_red_flags']:
            return ""

        # Get critical/urgent flags
        critical_flags = []
        urgent_flags = []
        
        for flag in detection_result['flags_with_context']:
            if flag['severity'] == 'critical':
                critical_flags.append(flag['description'])
            elif flag['severity'] == 'urgent':
                urgent_flags.append(flag['description'])
        
        if critical_flags:
            flags_text = ", ".join(critical_flags[:2])
            if len(critical_flags) > 2:
                flags_text += f" and {len(critical_flags)-2} other danger signs"
            
            return (
                f"🚨 EMERGENCY: {flags_text}. "
                f"THIS IS A LIFE-THREATENING EMERGENCY. "
                f"Please go to the nearest emergency facility IMMEDIATELY or call an ambulance."
            )
        
        elif urgent_flags:
            flags_text = ", ".join(urgent_flags[:2])
            if len(urgent_flags) > 2:
                flags_text += f" and {len(urgent_flags)-2} other concerns"
            
            return (
                f"⚠️ URGENT: {flags_text}. "
                f"You need urgent medical attention. "
                f"Please go to a hospital or health center TODAY."
            )
        
        else:
            return (
                f"⚠️ ATTENTION: We have identified some concerning symptoms. "
                f"Please seek medical evaluation soon."
            )

    def get_facility_recommendations(self, detection_result: Dict[str, Any]) -> List[str]:
        """
        Get facility type recommendations based on red flags
        """
        if detection_result['emergency_override']:
            return ['emergency', 'hospital']
        elif detection_result['highest_severity'] == EmergencySeverity.URGENT.value:
            return ['hospital', 'health_center']
        else:
            return ['health_center', 'clinic']


# Convenience function for external use
def detect_red_flags(session, triage_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Detect red flags in triage data - UPDATED

    Args:
        session: TriageSession object
        triage_data: Validated triage intake data

    Returns:
        Detection results dictionary
    """
    tool = RedFlagDetectionTool()
    return tool.detect(session, triage_data)