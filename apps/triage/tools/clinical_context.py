"""
Tool 5: Clinical Context Tool
Adjusts risk based on patient clinical context
"""

from typing import Dict, Any


class ClinicalContextTool:
    """
    Adjusts risk classification based on clinical context
    Considers chronic conditions, age, pregnancy, etc.
    """

    def adjust_risk(
            self,
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
        # Calculate individual modifiers
        chronic_modifier = self._assess_chronic_conditions(triage_data)
        age_modifier = self._assess_age_risk(triage_data)
        pregnancy_modifier = self._assess_pregnancy_risk(triage_data)
        medication_modifier = self._assess_medication_allergy(triage_data)

        # Total adjustment
        total_adjustment = (
                chronic_modifier +
                age_modifier +
                pregnancy_modifier +
                medication_modifier
        )

        # Determine adjusted risk level
        adjusted_risk = self._apply_adjustment(ai_risk_level, total_adjustment)

        # Build reasoning
        reasoning = self._build_reasoning(
            chronic_modifier, age_modifier,
            pregnancy_modifier, medication_modifier
        )

        return {
            'chronic_condition_modifier': chronic_modifier,
            'age_modifier': age_modifier,
            'pregnancy_modifier': pregnancy_modifier,
            'medication_allergy_modifier': medication_modifier,
            'total_risk_adjustment': total_adjustment,
            'adjusted_risk_level': adjusted_risk,
            'adjustment_reasoning': reasoning
        }

    def _assess_chronic_conditions(self, data: Dict[str, Any]) -> float:
        """Assess chronic condition impact on risk"""
        chronic = data.get('chronic_conditions', [])

        if not chronic or 'none' in chronic:
            return 0.0

        # High-risk chronic conditions
        high_risk = ['heart_disease', 'diabetes', 'asthma']
        has_high_risk = any(c in chronic for c in high_risk)

        if has_high_risk:
            return 0.2  # Increase risk
        elif len(chronic) > 0:
            return 0.1

        return 0.0

    def _assess_age_risk(self, data: Dict[str, Any]) -> float:
        """Assess age-related risk"""
        age = data.get('age_range', '')

        # Very young children
        if age == 'under_5':
            return 0.15

        # Elderly
        if age == '51_plus':
            return 0.1

        # Adolescents and young adults - lower risk
        if age in ['13_17', '18_30']:
            return -0.05

        return 0.0

    def _assess_pregnancy_risk(self, data: Dict[str, Any]) -> float:
        """Assess pregnancy-related risk"""
        pregnancy = data.get('pregnancy_status', 'not_applicable')

        if pregnancy == 'yes':
            # Pregnant women need more careful monitoring
            severity = data.get('symptom_severity', 'mild')
            if severity in ['severe', 'very_severe']:
                return 0.2
            return 0.1

        return 0.0

    def _assess_medication_allergy(self, data: Dict[str, Any]) -> float:
        """Assess medication and allergy considerations"""
        has_allergies = data.get('has_allergies', 'no')
        current_meds = data.get('current_medication', 'no')

        modifier = 0.0

        # Known allergies add complexity
        if has_allergies == 'yes':
            modifier += 0.05

        # On medication - may indicate ongoing condition
        if current_meds == 'yes':
            modifier += 0.05

        return modifier

    def _apply_adjustment(self, base_risk: str, adjustment: float) -> str:
        """Apply adjustment to base risk level"""
        # Map risk levels to scores
        risk_scores = {'low': 0, 'medium': 1, 'high': 2}

        current_score = risk_scores.get(base_risk, 0)

        # Apply adjustment thresholds
        if adjustment >= 0.3:
            # Significant increase - bump up one level
            current_score = min(current_score + 1, 2)
        elif adjustment >= 0.15:
            # Moderate increase - consider bumping up
            if current_score == 0:  # low -> medium
                current_score = 1
        elif adjustment <= -0.1:
            # Decrease - only if very minor case
            if current_score == 1 and adjustment <= -0.15:
                current_score = 0

        # Map back to risk level
        score_to_risk = {0: 'low', 1: 'medium', 2: 'high'}
        return score_to_risk.get(current_score, base_risk)

    def _build_reasoning(
            self,
            chronic: float,
            age: float,
            pregnancy: float,
            medication: float
    ) -> str:
        """Build human-readable reasoning"""
        reasons = []

        if chronic > 0:
            reasons.append(f"chronic conditions (+{chronic:.2f})")

        if age > 0:
            reasons.append(f"age risk factors (+{age:.2f})")
        elif age < 0:
            reasons.append(f"age factors ({age:.2f})")

        if pregnancy > 0:
            reasons.append(f"pregnancy considerations (+{pregnancy:.2f})")

        if medication > 0:
            reasons.append(f"medication/allergy factors (+{medication:.2f})")

        if not reasons:
            return "No significant clinical context adjustments"

        return "Risk adjusted for: " + ", ".join(reasons)