"""
Tool 6: Decision Synthesis Tool
Combines all tool outputs into final triage decision
"""

from typing import Dict, Any


class DecisionSynthesisTool:
    """
    Synthesizes final triage decision from all tool outputs
    Implements conservative bias for patient safety
    """

    def synthesize(
            self,
            session,
            red_flag_result: Dict[str, Any],
            ai_risk_level: str,
            context_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create final triage decision

        Args:
            session: TriageSession instance
            red_flag_result: Red flag detection results
            ai_risk_level: AI-determined risk level
            context_result: Clinical context adjustments

        Returns:
            Final decision dictionary
        """
        # Determine final risk level with override logic
        final_risk, decision_basis = self._determine_final_risk(
            red_flag_result, ai_risk_level, context_result
        )

        # Determine follow-up priority
        follow_up_priority = self._determine_follow_up_priority(
            final_risk, red_flag_result
        )

        # Generate recommendations
        recommended_action = self._generate_action_recommendation(
            final_risk, red_flag_result, session
        )

        facility_type = self._determine_facility_type(
            final_risk, red_flag_result
        )

        # Build reasoning
        reasoning = self._build_decision_reasoning(
            red_flag_result, ai_risk_level, context_result, final_risk
        )

        # Generate disclaimers
        disclaimers = self._generate_disclaimers(final_risk)

        return {
            'risk_level': final_risk,
            'follow_up_priority': follow_up_priority,
            'decision_basis': decision_basis,
            'recommended_action': recommended_action,
            'facility_type': facility_type,
            'reasoning': reasoning,
            'disclaimers': disclaimers,
            'follow_up_required': follow_up_priority != 'routine',
            'follow_up_timeframe': self._get_follow_up_timeframe(follow_up_priority)
        }

    def _determine_final_risk(
            self,
            red_flag_result: Dict[str, Any],
            ai_risk: str,
            context_result: Dict[str, Any]
    ) -> tuple[str, str]:
        """
        Determine final risk level using override logic

        Returns:
            (risk_level, decision_basis)
        """
        # Rule 1: Red flags ALWAYS override
        if red_flag_result.get('emergency_override'):
            return 'high', 'red_flag_override'

        # Rule 2: Use context-adjusted risk if available
        if 'adjusted_risk_level' in context_result:
            adjusted = context_result['adjusted_risk_level']

            # Apply conservative bias - never downgrade from AI
            if self._risk_level_to_score(adjusted) < self._risk_level_to_score(ai_risk):
                # Conservative: keep AI risk if higher
                return ai_risk, 'conservative_bias'
            else:
                return adjusted, 'clinical_adjustment'

        # Rule 3: Use AI risk
        return ai_risk, 'ai_primary'

    def _risk_level_to_score(self, risk: str) -> int:
        """Convert risk level to numeric score"""
        return {'low': 0, 'medium': 1, 'high': 2}.get(risk, 0)

    def _determine_follow_up_priority(
            self,
            risk_level: str,
            red_flag_result: Dict[str, Any]
    ) -> str:
        """Determine follow-up priority"""
        if red_flag_result.get('emergency_override'):
            return 'immediate'

        if risk_level == 'high':
            return 'urgent'
        elif risk_level == 'medium':
            return 'urgent'
        else:
            return 'routine'

    def _generate_action_recommendation(
            self,
            risk_level: str,
            red_flag_result: Dict[str, Any],
            session
    ) -> str:
        """Generate patient action recommendation"""
        if red_flag_result.get('emergency_override'):
            return (
                "⚠️ SEEK IMMEDIATE EMERGENCY CARE. Your symptoms indicate a "
                "potentially serious condition requiring immediate medical attention. "
                "Go to the nearest emergency facility or call emergency services now."
            )

        if risk_level == 'high':
            return (
                "Seek urgent medical care within the next few hours. "
                "Your symptoms require prompt medical evaluation. "
                "Go to a hospital or health center as soon as possible."
            )

        if risk_level == 'medium':
            return (
                "Schedule a medical consultation within 24-48 hours. "
                "Your symptoms should be evaluated by a healthcare provider. "
                "Monitor your condition and seek care sooner if symptoms worsen."
            )

        # Low risk
        return (
            "Monitor your symptoms and practice self-care. "
            "Rest, stay hydrated, and take over-the-counter medications as appropriate. "
            "Seek medical care if symptoms worsen or persist beyond a few days."
        )

    def _determine_facility_type(
            self,
            risk_level: str,
            red_flag_result: Dict[str, Any]
    ) -> str:
        """Determine recommended facility type"""
        if red_flag_result.get('emergency_override'):
            return 'emergency'

        if risk_level == 'high':
            return 'hospital'
        elif risk_level == 'medium':
            return 'health_center'
        else:
            return 'self_care'

    def _build_decision_reasoning(
            self,
            red_flag_result: Dict[str, Any],
            ai_risk: str,
            context_result: Dict[str, Any],
            final_risk: str
    ) -> str:
        """Build detailed reasoning explanation"""
        parts = []

        # Red flag information
        if red_flag_result.get('has_red_flags'):
            flags = red_flag_result.get('detected_flags', [])
            parts.append(
                f"Emergency red flags detected: {', '.join(flags)}. "
                "This overrides all other assessments."
            )

        # AI assessment
        parts.append(f"AI risk assessment: {ai_risk}")

        # Clinical context
        if context_result.get('adjustment_reasoning'):
            parts.append(context_result['adjustment_reasoning'])

        # Final decision
        parts.append(f"Final risk determination: {final_risk}")

        return " | ".join(parts)

    def _generate_disclaimers(self, risk_level: str) -> list[str]:
        """Generate appropriate disclaimers"""
        disclaimers = [
            "This is NOT a medical diagnosis - it is a preliminary assessment only.",
            "This assessment is based on the information you provided.",
            "Seek immediate medical care if your condition worsens at any time.",
        ]

        if risk_level == 'low':
            disclaimers.append(
                "Even mild symptoms can sometimes indicate serious conditions. "
                "Trust your judgment and seek care if concerned."
            )

        disclaimers.append(
            "This triage system is a decision support tool and does not replace "
            "professional medical judgment."
        )

        return disclaimers

    def _get_follow_up_timeframe(self, priority: str) -> str:
        """Get follow-up timeframe description"""
        timeframes = {
            'immediate': 'Immediately',
            'urgent': 'Within 24 hours',
            'routine': 'Within 3-7 days if symptoms persist'
        }
        return timeframes.get(priority, 'As needed')