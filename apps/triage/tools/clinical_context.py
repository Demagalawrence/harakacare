"""
Tool 5: Clinical Context Tool - UPDATED
Adjusts risk based on patient clinical context
Now includes age-specific, population-based, and complaint-specific modifiers
"""

from typing import Dict, Any, List, Optional


class ClinicalContextTool:
    """
    Adjusts risk classification based on clinical context - UPDATED
    Considers age groups, chronic conditions, pregnancy, immunocompromised status
    Never downgrades risk (conservative bias)
    """

    def __init__(self):
        # ====================================================================
        # Age-specific risk modifiers (based on WHO guidelines)
        # ====================================================================
        self.AGE_MODIFIERS = {
            'newborn': 0.25,      # Newborns - very high risk
            'infant': 0.20,        # Infants - high risk
            'child_1_5': 0.15,     # Young children - moderate risk
            'child_6_12': 0.05,    # School age - slight increase
            'teen': 0.0,           # Teens - baseline
            'adult': 0.0,           # Adults - baseline
            'elderly': 0.20,        # Elderly - high risk
        }

        # ====================================================================
        # Pregnancy modifiers (by severity)
        # ====================================================================
        self.PREGNANCY_MODIFIERS = {
            'confirmed_with_severe': 0.25,
            'confirmed_with_moderate': 0.15,
            'confirmed_mild': 0.10,
            'possible': 0.05,
            'none': 0.0,
        }

        # ====================================================================
        # Chronic condition modifiers
        # ====================================================================
        self.CHRONIC_CONDITION_MODIFIERS = {
            'heart_disease': 0.20,
            'diabetes': 0.15,
            'asthma': 0.15,
            'copd': 0.20,
            'hypertension': 0.10,
            'epilepsy': 0.10,
            'sickle_cell': 0.20,
            'hiv_aids': 0.20,
            'cancer': 0.25,
            'kidney_disease': 0.20,
            'liver_disease': 0.20,
            'other_chronic': 0.10,
        }

        # ====================================================================
        # Immunocompromised modifiers
        # ====================================================================
        self.IMMUNOCOMPROMISED_MODIFIERS = {
            'hiv_aids': 0.25,
            'cancer_treatment': 0.30,
            'transplant': 0.30,
            'steroid_longterm': 0.20,
            'other': 0.15,
        }

        # ====================================================================
        # Medication modifiers
        # ====================================================================
        self.MEDICATION_MODIFIERS = {
            'blood_thinners': 0.15,    # Increased bleeding risk
            'immunosuppressants': 0.20,
            'steroids': 0.10,
            'anticoagulants': 0.15,
            'insulin': 0.05,            # Indicates diabetes
        }

        # ====================================================================
        # Complaint-specific modifiers
        # ====================================================================
        self.COMPLAINT_SPECIFIC_MODIFIERS = {
            'chest_pain': {
                'heart_disease': 0.20,
                'diabetes': 0.10,
                'hypertension': 0.10,
                'elderly': 0.15,
            },
            'breathing': {
                'asthma': 0.15,
                'copd': 0.20,
                'heart_disease': 0.10,
                'child_1_5': 0.10,      # Children at risk for pneumonia
                'elderly': 0.15,
            },
            'fever': {
                'newborn': 0.30,         # Neonatal sepsis risk
                'infant': 0.25,
                'immunocompromised': 0.20,
                'sickle_cell': 0.20,      # Risk of sequestration
            },
            'abdominal': {
                'pregnancy': 0.25,        # Obstetric emergency
                'sickle_cell': 0.20,       # Risk of crisis
                'elderly': 0.15,
            },
            'headache': {
                'hypertension': 0.15,      # Risk of hypertensive emergency
                'pregnancy': 0.20,          # Risk of pre-eclampsia
                'elderly': 0.15,             # Risk of stroke
            },
            'bleeding': {
                'blood_thinners': 0.25,
                'pregnancy': 0.30,
                'liver_disease': 0.20,
            },
        }

    def adjust_risk(
            self,
            session,
            triage_data: Dict[str, Any],
            ai_risk_level: str,
            red_flag_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Adjust risk based on clinical context - UPDATED

        Args:
            session: TriageSession instance
            triage_data: Validated triage data
            ai_risk_level: Risk level from AI
            red_flag_result: Red flag detection results

        Returns:
            Context adjustment results with detailed modifiers
        """
        
        print("\n📊 CLINICAL CONTEXT ADJUSTMENT")
        
        # ====================================================================
        # Extract all relevant data
        # ====================================================================
        age_group = self._get_age_group(session, triage_data)
        complaint_group = self._get_complaint_group(session, triage_data)
        risk_modifiers = self._get_risk_modifiers(session, triage_data)
        pregnancy_status = self._get_pregnancy_status(session, triage_data)
        
        # Get symptom indicators for context
        symptom_indicators = getattr(session, 'symptom_indicators', {}) or {}
        if 'symptom_indicators' in triage_data:
            symptom_indicators.update(triage_data['symptom_indicators'])

        # ====================================================================
        # Calculate individual modifiers
        # ====================================================================
        
        # Age modifier
        age_modifier = self._assess_age_risk(age_group)
        print(f"  • Age modifier ({age_group}): +{age_modifier:.2f}")
        
        # Pregnancy modifier
        pregnancy_modifier = self._assess_pregnancy_risk(
            pregnancy_status, 
            complaint_group, 
            symptom_indicators
        )
        if pregnancy_modifier > 0:
            print(f"  • Pregnancy modifier: +{pregnancy_modifier:.2f}")
        
        # Chronic condition modifiers
        chronic_modifier, chronic_details = self._assess_chronic_conditions(
            risk_modifiers,
            complaint_group
        )
        if chronic_modifier > 0:
            print(f"  • Chronic conditions: +{chronic_modifier:.2f} ({', '.join(chronic_details)})")
        
        # Immunocompromised modifier
        immunocompromised_modifier = self._assess_immunocompromised(risk_modifiers)
        if immunocompromised_modifier > 0:
            print(f"  • Immunocompromised: +{immunocompromised_modifier:.2f}")
        
        # Medication modifier
        medication_modifier = self._assess_medication_risk(
            triage_data,
            risk_modifiers,
            complaint_group
        )
        if medication_modifier > 0:
            print(f"  • Medication risk: +{medication_modifier:.2f}")

        # ====================================================================
        # Calculate total adjustment
        # ====================================================================
        
        # Start with age modifier
        total_adjustment = age_modifier
        
        # Add other modifiers (all positive - never downgrade)
        total_adjustment += pregnancy_modifier
        total_adjustment += chronic_modifier
        total_adjustment += immunocompromised_modifier
        total_adjustment += medication_modifier
        
        # Apply conservative bias - ensure non-negative
        total_adjustment = max(0, total_adjustment)
        
        # Cap at reasonable maximum
        total_adjustment = min(total_adjustment, 0.5)
        
        print(f"  • TOTAL ADJUSTMENT: +{total_adjustment:.2f}")

        # ====================================================================
        # Determine adjusted risk level (with conservative bias)
        # ====================================================================
        
        # Apply adjustment with conservative bias (never downgrade)
        adjusted_risk, bias_applied = self._apply_adjustment(
            ai_risk_level, 
            total_adjustment,
            red_flag_result
        )
        
        # Build reasoning
        reasoning = self._build_reasoning(
            age_group=age_group,
            age_modifier=age_modifier,
            pregnancy_modifier=pregnancy_modifier,
            chronic_modifier=chronic_modifier,
            chronic_details=chronic_details,
            immunocompromised_modifier=immunocompromised_modifier,
            medication_modifier=medication_modifier,
            total_adjustment=total_adjustment,
            bias_applied=bias_applied
        )

        return {
            'age_modifier': age_modifier,
            'pregnancy_modifier': pregnancy_modifier,
            'chronic_condition_modifier': chronic_modifier,
            'immunocompromised_modifier': immunocompromised_modifier,
            'medication_modifier': medication_modifier,
            'total_adjustment': total_adjustment,
            'adjusted_risk_level': adjusted_risk,
            'adjustment_reasoning': reasoning,
            'conservative_bias_applied': bias_applied
        }

    def _get_age_group(self, session, data: Dict[str, Any]) -> str:
        """Extract age group from session or data"""
        return data.get('age_group') or getattr(session, 'age_group', 'adult')

    def _get_complaint_group(self, session, data: Dict[str, Any]) -> str:
        """Extract complaint group from session or data"""
        return data.get('complaint_group') or getattr(session, 'complaint_group', 'other')

    def _get_risk_modifiers(self, session, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract risk modifiers from session or data"""
        modifiers = getattr(session, 'risk_modifiers', {}) or {}
        if 'risk_modifiers' in data:
            modifiers.update(data['risk_modifiers'])
        return modifiers

    def _get_pregnancy_status(self, session, data: Dict[str, Any]) -> str:
        """Extract pregnancy status from session or data"""
        return data.get('pregnancy_status') or getattr(session, 'pregnancy_status', 'not_applicable')

    def _assess_age_risk(self, age_group: str) -> float:
        """Assess age-related risk based on new age groups"""
        return self.AGE_MODIFIERS.get(age_group, 0.0)

    def _assess_pregnancy_risk(
            self, 
            pregnancy_status: str, 
            complaint_group: str,
            symptom_indicators: Dict[str, bool]
    ) -> float:
        """Assess pregnancy-related risk with more granularity"""
        
        if pregnancy_status == 'not_applicable':
            return 0.0
        
        # Check for severe symptoms in pregnancy
        has_severe_pain = symptom_indicators.get('severe_abdominal_pain', False)
        has_bleeding = symptom_indicators.get('vaginal_bleeding', False)
        
        # Determine modifier based on status and symptoms
        if pregnancy_status == 'yes':
            if has_severe_pain or has_bleeding or complaint_group == 'bleeding':
                return self.PREGNANCY_MODIFIERS['confirmed_with_severe']
            elif symptom_indicators.get('moderate_pain', False):
                return self.PREGNANCY_MODIFIERS['confirmed_with_moderate']
            else:
                return self.PREGNANCY_MODIFIERS['confirmed_mild']
        elif pregnancy_status == 'possible':
            return self.PREGNANCY_MODIFIERS['possible']
        
        return 0.0

    def _assess_chronic_conditions(
            self, 
            risk_modifiers: Dict[str, Any],
            complaint_group: str
    ) -> tuple:
        """
        Assess chronic condition impact on risk
        Returns: (modifier, list_of_conditions)
        """
        
        modifier = 0.0
        conditions = []
        
        # Check for chronic conditions list
        chronic_list = risk_modifiers.get('chronic_conditions', [])
        
        # If it's a list of conditions
        if isinstance(chronic_list, list):
            for condition in chronic_list:
                if condition in self.CHRONIC_CONDITION_MODIFIERS:
                    condition_modifier = self.CHRONIC_CONDITION_MODIFIERS[condition]
                    modifier += condition_modifier
                    conditions.append(condition.replace('_', ' ').title())
                    
                    # Check for complaint-specific synergies
                    if complaint_group in self.COMPLAINT_SPECIFIC_MODIFIERS:
                        if condition in self.COMPLAINT_SPECIFIC_MODIFIERS[complaint_group]:
                            synergy = self.COMPLAINT_SPECIFIC_MODIFIERS[complaint_group][condition]
                            modifier += synergy
                            conditions.append(f"{condition}+{complaint_group}")
        
        # Also check boolean flags
        if risk_modifiers.get('has_heart_disease', False):
            modifier += 0.20
            conditions.append('Heart Disease')
        if risk_modifiers.get('has_diabetes', False):
            modifier += 0.15
            conditions.append('Diabetes')
        if risk_modifiers.get('has_asthma', False):
            modifier += 0.15
            conditions.append('Asthma')
        
        # Cap at reasonable maximum
        modifier = min(modifier, 0.4)
        
        return modifier, conditions

    def _assess_immunocompromised(self, risk_modifiers: Dict[str, Any]) -> float:
        """Assess immunocompromised status"""
        
        if risk_modifiers.get('is_immunocompromised', False):
            # Get specific reason if available
            reason = risk_modifiers.get('immunocompromised_reason', 'other')
            return self.IMMUNOCOMPROMISED_MODIFIERS.get(reason, 0.15)
        
        return 0.0

    def _assess_medication_risk(
            self,
            data: Dict[str, Any],
            risk_modifiers: Dict[str, Any],
            complaint_group: str
    ) -> float:
        """Assess medication-related risk"""
        
        modifier = 0.0
        
        # Check if on medication
        if data.get('on_medication', False):
            modifier += 0.05  # Base modifier for any medication
        
        # Check specific medication types
        medications = risk_modifiers.get('medications', [])
        if isinstance(medications, list):
            for med in medications:
                if med in self.MEDICATION_MODIFIERS:
                    modifier += self.MEDICATION_MODIFIERS[med]
        
        # Blood thinners + bleeding complaint = high risk
        if complaint_group == 'bleeding' and 'blood_thinners' in medications:
            modifier += 0.15
        
        return min(modifier, 0.3)

    def _apply_adjustment(self, base_risk: str, adjustment: float, red_flag_result: Dict[str, Any]) -> tuple:
        """
        Apply adjustment to base risk level with conservative bias
        Returns: (adjusted_risk, bias_applied)
        """
        
        # Map risk levels to scores
        risk_scores = {'low': 0, 'medium': 1, 'high': 2}
        current_score = risk_scores.get(base_risk, 0)
        
        bias_applied = False
        
        # Check for red flags - they always force high
        if red_flag_result.get('has_red_flags', False):
            if red_flag_result.get('emergency_override', False):
                return 'high', True
        
        # Convert adjustment to level changes
        # Each 0.15 = approximately one level increase
        level_increase = int(adjustment / 0.15)
        
        if level_increase > 0:
            current_score = min(current_score + level_increase, 2)
            bias_applied = True
        
        # Apply conservative bias: never downgrade
        # If adjustment is negative, ignore it (never downgrade)
        
        # Map back to risk level
        score_to_risk = {0: 'low', 1: 'medium', 2: 'high'}
        adjusted_risk = score_to_risk.get(current_score, base_risk)
        
        return adjusted_risk, bias_applied

    def _build_reasoning(
            self,
            age_group: str,
            age_modifier: float,
            pregnancy_modifier: float,
            chronic_modifier: float,
            chronic_details: List[str],
            immunocompromised_modifier: float,
            medication_modifier: float,
            total_adjustment: float,
            bias_applied: bool
    ) -> str:
        """Build detailed human-readable reasoning"""
        
        reasons = []
        
        # Age reasoning
        if age_modifier > 0:
            age_descriptions = {
                'newborn': 'newborn (extremely vulnerable)',
                'infant': 'infant (high risk)',
                'child_1_5': 'young child (elevated risk)',
                'elderly': 'elderly patient (high risk)',
            }
            age_desc = age_descriptions.get(age_group, age_group)
            reasons.append(f"Age: {age_desc} (+{age_modifier:.2f})")
        
        # Pregnancy reasoning
        if pregnancy_modifier > 0:
            if pregnancy_modifier >= 0.2:
                reasons.append(f"Pregnancy with concerning symptoms (+{pregnancy_modifier:.2f})")
            else:
                reasons.append(f"Pregnancy (+{pregnancy_modifier:.2f})")
        
        # Chronic condition reasoning
        if chronic_modifier > 0 and chronic_details:
            conditions_str = ', '.join(chronic_details[:3])
            if len(chronic_details) > 3:
                conditions_str += f" and {len(chronic_details)-3} others"
            reasons.append(f"Chronic conditions: {conditions_str} (+{chronic_modifier:.2f})")
        
        # Immunocompromised reasoning
        if immunocompromised_modifier > 0:
            reasons.append(f"Immunocompromised (+{immunocompromised_modifier:.2f})")
        
        # Medication reasoning
        if medication_modifier > 0:
            reasons.append(f"Medication risk factors (+{medication_modifier:.2f})")
        
        # Build final reasoning
        if not reasons:
            return "No significant clinical context adjustments"
        
        reasoning = "Risk increased due to: " + "; ".join(reasons)
        
        if bias_applied and total_adjustment > 0:
            reasoning += f". Total adjustment: +{total_adjustment:.2f} (conservative bias applied)"
        
        return reasoning


# Convenience function for external use
def adjust_clinical_context(
        session,
        triage_data: Dict[str, Any],
        ai_risk_level: str,
        red_flag_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Adjust risk based on clinical context
    
    Args:
        session: TriageSession instance
        triage_data: Validated triage data
        ai_risk_level: Risk level from AI
        red_flag_result: Red flag detection results

    Returns:
        Context adjustment results
    """
    tool = ClinicalContextTool()
    return tool.adjust_risk(session, triage_data, ai_risk_level, red_flag_result)