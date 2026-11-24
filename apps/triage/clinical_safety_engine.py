"""
Clinical Safety Rules Engine - Phase 3 AI Upgrade

Deterministic safety engine that checks for clinician-approved emergency indicators.
Emergency indicators are checked BEFORE routine ML recommendations.
A critical red flag must NEVER be downgraded by a low-risk ML prediction.

Based on WHO ABCD guidelines and IMCI (Integrated Management of Childhood Illness).
Sources: WHO Pocket Book of Hospital Care for Children, WHO IMCI guidelines.

This is a clinical decision-support tool - it applies safety rules,
it does NOT make medical diagnoses.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SafetyLevel(Enum):
    """Safety escalation levels"""
    SAFE = "safe"              # No safety concerns
    CAUTION = "caution"        # Monitor, routine care
    URGENT = "urgent"          # Needs urgent clinical review
    EMERGENCY = "emergency"    # Immediate emergency care required


@dataclass
class SafetyRule:
    """A single clinical safety rule"""
    rule_id: str
    name: str
    description: str
    condition: str  # Human-readable description of when rule triggers
    safety_level: SafetyLevel
    action_required: str
    source: str  # Clinical guideline source (e.g., "WHO IMCI 2023")
    applies_to_age_groups: List[str]  # Empty = all ages
    always_escalates: bool = True  # If True, ML cannot downgrade


@dataclass
class SafetyEngineResult:
    """Result of safety engine evaluation"""
    is_safe: bool
    safety_level: SafetyLevel
    triggered_rules: List[SafetyRule]
    emergency_message: Optional[str]
    ml_override_applied: bool  # True if safety rules overruled ML
    reasoning: str
    recommended_action: str
    requires_human_review: bool


class ClinicalSafetyEngine:
    """
    Deterministic clinical safety rules engine.
    
    Rules are based on WHO ABCD guidelines and IMCI protocols.
    Emergency rules always take precedence over ML predictions.
    """
    
    # ========================================================================
    # CLINICAL SAFETY RULES (WHO ABCD + IMCI)
    # ========================================================================
    
    SAFETY_RULES = [
        # === AIRWAY (A) ===
        SafetyRule(
            rule_id='AIRWAY_001',
            name='Airway Obstruction',
            description='Patient cannot speak, choking, stridor, or severe difficulty swallowing',
            condition='airway_obstruction == True',
            safety_level=SafetyLevel.EMERGENCY,
            action_required='IMMEDIATE: Clear airway, call emergency services, go to nearest hospital',
            source='WHO ABCD - Airway',
            applies_to_age_groups=[],  # All ages
            always_escalates=True,
        ),
        SafetyRule(
            rule_id='AIRWAY_002',
            name='Severe Difficulty Swallowing',
            description='Cannot swallow saliva, drooling, unable to drink',
            condition='unable_to_drink == True AND age_group in [newborn, infant, child_1_5]',
            safety_level=SafetyLevel.EMERGENCY,
            action_required='IMMEDIATE: Child needs urgent assessment for airway compromise',
            source='WHO IMCI - Unable to drink/breastfeed',
            applies_to_age_groups=['newborn', 'infant', 'child_1_5'],
            always_escalates=True,
        ),
        
        # === BREATHING (B) ===
        SafetyRule(
            rule_id='BREATHING_001',
            name='Severe Breathing Difficulty',
            description='Struggling to breathe, gasping, blue lips, severe respiratory distress',
            condition='severe_breathing_difficulty == True',
            safety_level=SafetyLevel.EMERGENCY,
            action_required='IMMEDIATE: Emergency oxygen and care required',
            source='WHO ABCD - Breathing',
            applies_to_age_groups=[],
            always_escalates=True,
        ),
        SafetyRule(
            rule_id='BREATHING_002',
            name='Chest Indrawing (Children)',
            description='Visible chest wall indrawing during breathing in children',
            condition='chest_indrawing == True AND age_group in [newborn, infant, child_1_5]',
            safety_level=SafetyLevel.EMERGENCY,
            action_required='IMMEDIATE: Child needs urgent assessment for pneumonia/severe respiratory infection',
            source='WHO IMCI - Chest indrawing',
            applies_to_age_groups=['newborn', 'infant', 'child_1_5'],
            always_escalates=True,
        ),
        SafetyRule(
            rule_id='BREATHING_003',
            name='Fast Breathing (Children)',
            description='Respiratory rate above age-specific threshold',
            condition='fast_breathing == True AND age_group in [newborn, infant, child_1_5, child_6_12]',
            safety_level=SafetyLevel.URGENT,
            action_required='URGENT: Clinical assessment within 2 hours',
            source='WHO IMCI - Fast breathing',
            applies_to_age_groups=['newborn', 'infant', 'child_1_5', 'child_6_12'],
            always_escalates=True,
        ),
        
        # === CIRCULATION (C) ===
        SafetyRule(
            rule_id='CIRCULATION_001',
            name='Severe Bleeding',
            description='Heavy bleeding, hemorrhage, blood loss that cannot be controlled',
            condition='severe_bleeding == True',
            safety_level=SafetyLevel.EMERGENCY,
            action_required='IMMEDIATE: Control bleeding, emergency care',
            source='WHO ABCD - Circulation',
            applies_to_age_groups=[],
            always_escalates=True,
        ),
        SafetyRule(
            rule_id='CIRCULATION_002',
            name='Signs of Shock',
            description='Very pale, cold extremities, weak pulse, altered consciousness',
            condition='signs_of_shock == True',
            safety_level=SafetyLevel.EMERGENCY,
            action_required='IMMEDIATE: Emergency care for shock',
            source='WHO ABCD - Circulation - Shock',
            applies_to_age_groups=[],
            always_escalates=True,
        ),
        
        # === DISABILITY (D) ===
        SafetyRule(
            rule_id='DISABILITY_001',
            name='Unconsciousness',
            description='Unconscious, unresponsive, cannot be woken',
            condition='unconscious == True',
            safety_level=SafetyLevel.EMERGENCY,
            action_required='IMMEDIATE: Emergency care, assess ABCD',
            source='WHO ABCD - Disability',
            applies_to_age_groups=[],
            always_escalates=True,
        ),
        SafetyRule(
            rule_id='DISABILITY_002',
            name='Convulsions/Seizures',
            description='Active convulsions, seizures, or fitting',
            condition='convulsions == True',
            safety_level=SafetyLevel.EMERGENCY,
            action_required='IMMEDIATE: Emergency care for seizures',
            source='WHO ABCD - Disability - Convulsions',
            applies_to_age_groups=[],
            always_escalates=True,
        ),
        SafetyRule(
            rule_id='DISABILITY_003',
            name='Confusion/Disorientation',
            description='New confusion, disorientation, altered mental status',
            condition='confusion == True',
            safety_level=SafetyLevel.URGENT,
            action_required='URGENT: Clinical assessment for stroke, infection, or other causes',
            source='WHO ABCD - Disability',
            applies_to_age_groups=['teen', 'adult', 'elderly'],
            always_escalates=True,
        ),
        SafetyRule(
            rule_id='DISABILITY_004',
            name='Stroke Symptoms',
            description='Face droop, arm weakness, speech difficulty, sudden onset',
            condition='stroke_symptoms == True',
            safety_level=SafetyLevel.EMERGENCY,
            action_required='IMMEDIATE: Possible stroke - emergency care immediately',
            source='WHO Stroke Guidelines',
            applies_to_age_groups=['adult', 'elderly'],
            always_escalates=True,
        ),
        
        # === AGE-SPECIFIC (IMCI) ===
        SafetyRule(
            rule_id='AGE_001',
            name='Lethargic Infant',
            description='Infant unusually sleepy, floppy, difficult to wake',
            condition='lethargic_floppy == True AND age_group in [newborn, infant]',
            safety_level=SafetyLevel.EMERGENCY,
            action_required='IMMEDIATE: Infant needs urgent assessment',
            source='WHO IMCI - Lethargy',
            applies_to_age_groups=['newborn', 'infant'],
            always_escalates=True,
        ),
        SafetyRule(
            rule_id='AGE_002',
            name='Vomits Everything (Child)',
            description='Child vomits everything given, cannot keep fluids down',
            condition='vomits_everything == True AND age_group in [newborn, infant, child_1_5]',
            safety_level=SafetyLevel.URGENT,
            action_required='URGENT: Risk of dehydration - clinical assessment',
            source='WHO IMCI - Vomits everything',
            applies_to_age_groups=['newborn', 'infant', 'child_1_5'],
            always_escalates=True,
        ),
        
        # === PREGNANCY ===
        SafetyRule(
            rule_id='PREGNANCY_001',
            name='Pregnancy Emergency',
            description='Heavy vaginal bleeding, severe abdominal pain in pregnancy',
            condition='pregnancy_emergency == True',
            safety_level=SafetyLevel.EMERGENCY,
            action_required='IMMEDIATE: Emergency obstetric care',
            source='WHO Pregnancy Guidelines',
            applies_to_age_groups=['teen', 'adult'],
            always_escalates=True,
        ),
        SafetyRule(
            rule_id='PREGNANCY_002',
            name='Severe Abdominal Pain in Pregnancy',
            description='Severe abdominal pain in pregnant patient',
            condition='severe_pain == True AND is_pregnant == True',
            safety_level=SafetyLevel.URGENT,
            action_required='URGENT: Obstetric assessment',
            source='WHO Pregnancy Guidelines',
            applies_to_age_groups=['teen', 'adult'],
            always_escalates=True,
        ),
        
        # === GENERAL ===
        SafetyRule(
            rule_id='GENERAL_001',
            name='Severe Uncontrolled Pain',
            description='Worst pain ever experienced, unbearable pain',
            condition='severe_pain == True',
            safety_level=SafetyLevel.URGENT,
            action_required='URGENT: Pain assessment and management',
            source='WHO Pain Guidelines',
            applies_to_age_groups=[],
            always_escalates=False,  # Can be assessed by clinician
        ),
    ]
    
    # Rule lookup by ID
    RULES_BY_ID = {rule.rule_id: rule for rule in SAFETY_RULES}
    
    def __init__(self):
        self.rules = self.SAFETY_RULES
        logger.info(f"Clinical Safety Engine initialized with {len(self.rules)} rules")
    
    def evaluate(self, triage_data: Dict[str, Any],
                 ml_risk_level: Optional[str] = None,
                 ml_confidence: Optional[float] = None) -> SafetyEngineResult:
        """
        Evaluate clinical safety rules against triage data.
        
        Safety rules are checked BEFORE ML recommendations.
        A critical red flag must NEVER be downgraded by ML.
        
        Args:
            triage_data: Dictionary containing triage assessment data including
                        red_flag_indicators, age_group, sex, etc.
            ml_risk_level: ML-predicted risk level (for override comparison)
            ml_confidence: ML confidence score
            
        Returns SafetyEngineResult with safety determination and any overrides
        """
        red_flags = triage_data.get('red_flag_indicators', {})
        if not isinstance(red_flags, dict):
            red_flags = {}
        
        age_group = triage_data.get('age_group', '')
        is_pregnant = triage_data.get('pregnancy_status', '') in ['yes', 'possible']
        has_chronic = triage_data.get('has_chronic_conditions', False)
        
        triggered_rules = []
        max_safety_level = SafetyLevel.SAFE
        ml_override_applied = False
        
        # Evaluate each rule
        for rule in self.rules:
            if self._rule_triggers(rule, red_flags, age_group, is_pregnant, has_chronic, triage_data):
                triggered_rules.append(rule)
                
                # Escalate safety level
                if rule.safety_level.value == 'emergency':
                    max_safety_level = SafetyLevel.EMERGENCY
                elif rule.safety_level.value == 'urgent' and max_safety_level not in [SafetyLevel.EMERGENCY]:
                    max_safety_level = SafetyLevel.URGENT
                elif rule.safety_level.value == 'caution' and max_safety_level == SafetyLevel.SAFE:
                    max_safety_level = SafetyLevel.CAUTION
        
        # Determine if ML should be overridden
        # Safety: Emergency rules always override ML
        if max_safety_level == SafetyLevel.EMERGENCY:
            if ml_risk_level and ml_risk_level != 'high':
                ml_override_applied = True
                final_risk = 'high'
            else:
                final_risk = ml_risk_level or 'high'
            requires_human_review = True
            is_safe = False
        elif max_safety_level == SafetyLevel.URGENT:
            if ml_risk_level and ml_risk_level == 'low':
                ml_override_applied = True
                final_risk = 'medium'
            else:
                final_risk = ml_risk_level or 'medium'
            requires_human_review = True
            is_safe = False
        elif max_safety_level == SafetyLevel.CAUTION:
            final_risk = ml_risk_level or 'medium'
            requires_human_review = False
            is_safe = True
        else:
            final_risk = ml_risk_level or 'low'
            requires_human_review = False
            is_safe = True
        
        # Generate emergency message
        emergency_message = None
        if max_safety_level == SafetyLevel.EMERGENCY:
            emergency_message = (
                "EMERGENCY: Danger signs detected. Seek immediate medical attention. "
                "Do not wait - go to the nearest hospital or call emergency services."
            )
        elif max_safety_level == SafetyLevel.URGENT:
            emergency_message = (
                "URGENT: Concerning symptoms detected. Seek medical care within a few hours. "
                "Do not delay seeking care."
            )
        
        # Generate reasoning
        reasoning_parts = []
        if triggered_rules:
            rule_names = [r.name for r in triggered_rules]
            reasoning_parts.append(f"Safety rules triggered: {', '.join(rule_names)}")
        
        if ml_override_applied:
            reasoning_parts.append(
                f"ML prediction ({ml_risk_level}) overridden by safety rules "
                f"to {final_risk} due to emergency indicators."
            )
        elif ml_risk_level:
            if ml_confidence:
                reasoning_parts.append(f"ML prediction: {ml_risk_level} (confidence: {ml_confidence:.1%})")
            else:
                reasoning_parts.append(f"ML prediction: {ml_risk_level}")
        
        if not triggered_rules and not ml_risk_level:
            reasoning_parts.append("No safety concerns identified.")
        
        reasoning = ". ".join(reasoning_parts)
        
        # Recommended action
        if max_safety_level == SafetyLevel.EMERGENCY:
            recommended_action = "EMERGENCY: Immediate medical care required. Go to nearest hospital."
        elif max_safety_level == SafetyLevel.URGENT:
            recommended_action = "URGENT: Clinical review within 2-4 hours recommended."
        elif max_safety_level == SafetyLevel.CAUTION:
            recommended_action = "CAUTION: Monitor symptoms, seek care if worsening."
        else:
            recommended_action = "ROUTINE: Routine care, follow up as needed."
        
        return SafetyEngineResult(
            is_safe=is_safe,
            safety_level=max_safety_level,
            triggered_rules=triggered_rules,
            emergency_message=emergency_message,
            ml_override_applied=ml_override_applied,
            reasoning=reasoning,
            recommended_action=recommended_action,
            requires_human_review=requires_human_review,
        )
    
    def _rule_triggers(self, rule: SafetyRule, red_flags: Dict[str, bool],
                        age_group: str, is_pregnant: bool,
                        has_chronic: bool, triage_data: Dict[str, Any]) -> bool:
        """Check if a specific safety rule triggers"""
        
        # Check age group applicability
        if rule.applies_to_age_groups and age_group not in rule.applies_to_age_groups:
            return False
        
        # Map rule conditions to data checks
        condition_checks = {
            'airway_obstruction': red_flags.get('airway_obstruction', False),
            'severe_breathing_difficulty': red_flags.get('severe_breathing_difficulty', False),
            'chest_indrawing': red_flags.get('chest_indrawing', False),
            'fast_breathing': triage_data.get('fast_breathing', False),
            'severe_bleeding': red_flags.get('severe_bleeding', False),
            'signs_of_shock': red_flags.get('signs_of_shock', False),
            'unconscious': red_flags.get('unconscious', False),
            'convulsions': red_flags.get('convulsions', False),
            'confusion': red_flags.get('confusion', False),
            'stroke_symptoms': red_flags.get('stroke_symptoms', False),
            'lethargic_floppy': red_flags.get('lethargic_floppy', False),
            'vomits_everything': red_flags.get('vomits_everything', False),
            'pregnancy_emergency': red_flags.get('pregnancy_emergency', False),
            'severe_pain': red_flags.get('severe_pain', False),
            'is_pregnant': is_pregnant,
            'has_chronic_conditions': has_chronic,
        }
        
        # Parse the condition string (simple evaluation)
        condition = rule.condition
        
        # Normalize boolean operators to Python syntax (conditions use AND/OR words)
        condition = condition.replace(" AND ", " and ").replace(" AND", " and ")
        condition = condition.replace(" OR ", " or ").replace(" OR", " or ")
        
        # Replace variable names with boolean values
        for var, val in condition_checks.items():
            condition = condition.replace(var, str(val))
        
        # Replace age_group references
        condition = condition.replace(
            f"age_group in {rule.applies_to_age_groups}",
            "True" if age_group in rule.applies_to_age_groups else "False"
        )
        
        try:
            return eval(condition)
        except Exception as e:
            logger.error(f"Error evaluating rule {rule.rule_id}: {e}")
            return False
    
    def get_rule_documentation(self) -> List[Dict[str, str]]:
        """Return documentation for all safety rules"""
        return [
            {
                'rule_id': rule.rule_id,
                'name': rule.name,
                'description': rule.description,
                'condition': rule.condition,
                'safety_level': rule.safety_level.value,
                'action_required': rule.action_required,
                'source': rule.source,
                'applies_to_age_groups': rule.applies_to_age_groups,
                'always_escalates': rule.always_escalates,
            }
            for rule in self.rules
        ]


# Global safety engine instance
safety_engine = ClinicalSafetyEngine()
