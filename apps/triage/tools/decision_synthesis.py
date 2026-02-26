"""
Tool 6: Decision Synthesis Tool - UPDATED
Combines all tool outputs into final triage decision
Now incorporates complaint groups, age groups, and WHO guidelines
"""

from typing import Dict, Any, List, Tuple


class DecisionSynthesisTool:
    """
    Synthesizes final triage decision from all tool outputs - UPDATED
    Implements WHO/ICRC triage principles with conservative bias
    """

    def __init__(self):
        # ====================================================================
        # Decision basis priorities (higher number = higher priority)
        # ====================================================================
        self.DECISION_PRIORITIES = {
            'red_flag_override': 100,      # Highest - WHO ABCD danger signs
            'age_risk_modifier': 80,        # Age-specific risk (newborn, elderly)
            'clinical_adjustment': 70,       # Clinical context factors
            'complaint_specific': 60,         # Complaint group rules
            'ai_primary': 50,                  # Base AI assessment
            'conservative_bias': 40,            # Conservative safety net
        }

        # ====================================================================
        # Risk level to facility type mapping
        # ====================================================================
        self.FACILITY_MAPPING = {
            'high': {
                'with_red_flags': 'emergency',
                'without_red_flags': 'hospital'
            },
            'medium': {
                'with_red_flags': 'hospital',
                'without_red_flags': 'health_center'
            },
            'low': {
                'with_red_flags': 'health_center',  # Even low risk with red flags needs care
                'without_red_flags': 'self_care'
            }
        }

        # ====================================================================
        # Complaint-specific action templates
        # ====================================================================
        self.COMPLAINT_ACTIONS = {
            'fever': {
                'high': "URGENT: High fever requires immediate evaluation. Go to the nearest hospital.",
                'medium': "Visit a health center within 24 hours for fever assessment. Monitor temperature.",
                'low': "Monitor fever at home. Rest, hydrate, and use fever reducers if appropriate."
            },
            'breathing': {
                'high': "EMERGENCY: Breathing difficulty requires immediate care. Go to emergency facility NOW.",
                'medium': "URGENT: Breathing problems need evaluation today. Visit hospital or health center.",
                'low': "Monitor breathing. If wheezing or shortness of breath persists, seek care."
            },
            'injury': {
                'high': "EMERGENCY: Serious injury requires immediate trauma care. Call ambulance or go to emergency.",
                'medium': "Seek care within 24 hours for injury assessment. Go to health center or hospital.",
                'low': "For minor injuries: rest, ice, compression. Seek care if not improving."
            },
            'abdominal': {
                'high': "EMERGENCY: Severe abdominal pain needs immediate evaluation. Go to emergency.",
                'medium': "URGENT: Abdominal pain requires assessment within 24 hours.",
                'low': "Monitor abdominal symptoms. Seek care if pain persists or worsens."
            },
            'headache': {
                'high': "EMERGENCY: Severe headache with neurological symptoms requires immediate care.",
                'medium': "URGENT: Headache needs evaluation. Go to hospital if severe.",
                'low': "Rest and hydrate. Seek care if headache persists or worsens."
            },
            'chest_pain': {
                'high': "EMERGENCY: Chest pain is a potential cardiac emergency. Seek care IMMEDIATELY.",
                'medium': "URGENT: Chest pain requires prompt evaluation within hours.",
                'low': "Monitor chest discomfort. Seek immediate care if pain worsens."
            },
            'pregnancy': {
                'high': "EMERGENCY: Pregnancy complication suspected. Seek obstetric care IMMEDIATELY.",
                'medium': "URGENT: Pregnancy concern needs evaluation within 24 hours.",
                'low': "Monitor pregnancy symptoms. Contact maternal health provider if concerned."
            },
            'skin': {
                'high': "URGENT: Severe skin condition requires prompt evaluation.",
                'medium': "Seek care within 24-48 hours for skin assessment.",
                'low': "Monitor skin condition. Use topical treatments if appropriate."
            },
            'bleeding': {
                'high': "EMERGENCY: Bleeding requires immediate attention. Go to emergency NOW.",
                'medium': "URGENT: Bleeding needs evaluation within hours.",
                'low': "Monitor for continued bleeding. Seek care if persistent."
            },
            'mental_health': {
                'high': "EMERGENCY: Mental health crisis - seek immediate support. Call crisis line or go to ER.",
                'medium': "URGENT: Mental health concern needs evaluation within 24 hours.",
                'low': "Mental health support recommended. Contact counselor or support line."
            }
        }

        # ====================================================================
        # Age-specific action notes
        # ====================================================================
        self.AGE_SPECIFIC_NOTES = {
            'newborn': "⚠️ NEWBORN: Any illness in first 2 months requires urgent pediatric evaluation.",
            'infant': "⚠️ INFANT: Infants deteriorate quickly - seek care if concerned.",
            'child_1_5': "👶 CHILD: Young children need careful monitoring and low threshold for seeking care.",
            'child_6_12': "🧒 CHILD: Monitor closely and seek care if symptoms persist.",
            'teen': "👤 TEEN: Standard monitoring applies.",
            'adult': "👤 ADULT: Standard monitoring applies.",
            'elderly': "⚠️ ELDERLY: Older adults are at higher risk - seek care early."
        }

    def synthesize(
            self,
            session,
            red_flag_result: Dict[str, Any],
            ai_risk_level: str,
            context_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create final triage decision - UPDATED

        Args:
            session: TriageSession instance
            red_flag_result: Red flag detection results
            ai_risk_level: AI-determined risk level
            context_result: Clinical context adjustments

        Returns:
            Final decision dictionary
        """
        
        print("\n🎯 DECISION SYNTHESIS")
        
        # Get session data
        age_group = getattr(session, 'age_group', 'adult')
        complaint_group = getattr(session, 'complaint_group', 'other')
        has_red_flags = red_flag_result.get('has_red_flags', False)
        
        # ====================================================================
        # Step 1: Determine final risk level with priority-based logic
        # ====================================================================
        final_risk, decision_basis, priority = self._determine_final_risk(
            red_flag_result, 
            ai_risk_level, 
            context_result,
            complaint_group,
            age_group
        )
        
        print(f"  • Final risk: {final_risk}")
        print(f"  • Decision basis: {decision_basis} (priority: {priority})")

        # ====================================================================
        # Step 2: Determine follow-up priority
        # ====================================================================
        follow_up_priority = self._determine_follow_up_priority(
            final_risk, 
            red_flag_result,
            age_group
        )
        
        print(f"  • Follow-up: {follow_up_priority}")

        # ====================================================================
        # Step 3: Generate recommendations (complaint-specific)
        # ====================================================================
        recommended_action = self._generate_action_recommendation(
            final_risk, 
            red_flag_result, 
            session,
            complaint_group,
            age_group
        )

        facility_type = self._determine_facility_type(
            final_risk, 
            red_flag_result,
            complaint_group
        )
        
        print(f"  • Facility: {facility_type}")

        # ====================================================================
        # Step 4: Build reasoning and disclaimers
        # ====================================================================
        reasoning = self._build_decision_reasoning(
            red_flag_result, 
            ai_risk_level, 
            context_result, 
            final_risk,
            decision_basis,
            complaint_group,
            age_group
        )

        disclaimers = self._generate_disclaimers(final_risk, age_group, complaint_group)

        # ====================================================================
        # Step 5: Determine follow-up requirements
        # ====================================================================
        follow_up_required, follow_up_timeframe = self._determine_follow_up(
            follow_up_priority,
            final_risk,
            has_red_flags,
            age_group
        )

        return {
            'risk_level': final_risk,
            'follow_up_priority': follow_up_priority,
            'decision_basis': decision_basis,
            'recommended_action': recommended_action,
            'facility_type': facility_type,
            'reasoning': reasoning,
            'disclaimers': disclaimers,
            'follow_up_required': follow_up_required,
            'follow_up_timeframe': follow_up_timeframe,
            'age_specific_note': self.AGE_SPECIFIC_NOTES.get(age_group, "")
        }

    def _determine_final_risk(
            self,
            red_flag_result: Dict[str, Any],
            ai_risk: str,
            context_result: Dict[str, Any],
            complaint_group: str,
            age_group: str
    ) -> Tuple[str, str, int]:
        """
        Determine final risk level using priority-based override logic
        Returns: (risk_level, decision_basis, priority_score)
        """
        
        # ====================================================================
        # Priority 1: Red flags ALWAYS override - WHO ABCD danger signs
        # ====================================================================
        if red_flag_result.get('emergency_override'):
            return 'high', 'red_flag_override', self.DECISION_PRIORITIES['red_flag_override']
        
        if red_flag_result.get('has_red_flags'):
            # Any red flags force at least medium, but usually high
            if red_flag_result.get('highest_severity') == 'critical':
                return 'high', 'red_flag_override', self.DECISION_PRIORITIES['red_flag_override']
            else:
                # Urgent flags might keep at medium but with red flag basis
                return 'medium', 'red_flag_override', self.DECISION_PRIORITIES['red_flag_override']

        # ====================================================================
        # Priority 2: Age-specific risk modifiers
        # ====================================================================
        if age_group in ['newborn', 'infant']:
            # Newborns/infants with any symptoms are at least medium risk
            if ai_risk == 'low':
                return 'medium', 'age_risk_modifier', self.DECISION_PRIORITIES['age_risk_modifier']
        
        if age_group == 'elderly' and complaint_group in ['chest_pain', 'breathing', 'headache']:
            # Elderly with certain complaints get bumped up
            if ai_risk == 'low':
                return 'medium', 'age_risk_modifier', self.DECISION_PRIORITIES['age_risk_modifier']

        # ====================================================================
        # Priority 3: Clinical context adjustments
        # ====================================================================
        if 'adjusted_risk_level' in context_result:
            adjusted = context_result['adjusted_risk_level']
            
            # Apply conservative bias - never downgrade from AI
            if self._risk_level_to_score(adjusted) < self._risk_level_to_score(ai_risk):
                # Conservative: keep AI risk if higher
                return ai_risk, 'conservative_bias', self.DECISION_PRIORITIES['conservative_bias']
            elif adjusted != ai_risk:
                return adjusted, 'clinical_adjustment', self.DECISION_PRIORITIES['clinical_adjustment']

        # ====================================================================
        # Priority 4: Complaint-specific rules
        # ====================================================================
        if complaint_group == 'chest_pain' and ai_risk == 'low':
            # Chest pain is never truly low risk
            return 'medium', 'complaint_specific', self.DECISION_PRIORITIES['complaint_specific']
        
        if complaint_group == 'bleeding' and ai_risk == 'low':
            # Bleeding is never truly low risk
            return 'medium', 'complaint_specific', self.DECISION_PRIORITIES['complaint_specific']

        # ====================================================================
        # Priority 5: Use AI risk
        # ====================================================================
        return ai_risk, 'ai_primary', self.DECISION_PRIORITIES['ai_primary']

    def _risk_level_to_score(self, risk: str) -> int:
        """Convert risk level to numeric score"""
        return {'low': 0, 'medium': 1, 'high': 2}.get(risk, 0)

    def _determine_follow_up_priority(
            self,
            risk_level: str,
            red_flag_result: Dict[str, Any],
            age_group: str
    ) -> str:
        """Determine follow-up priority with age considerations"""
        
        # Emergency override always immediate
        if red_flag_result.get('emergency_override'):
            return 'immediate'
        
        # Any red flags require at least urgent
        if red_flag_result.get('has_red_flags'):
            if red_flag_result.get('highest_severity') == 'critical':
                return 'immediate'
            return 'urgent'
        
        # Age-based escalation
        if age_group in ['newborn', 'infant']:
            if risk_level == 'medium':
                return 'urgent'  # Infants with medium risk need urgent care
        
        # Standard mapping
        if risk_level == 'high':
            return 'urgent'
        elif risk_level == 'medium':
            return 'urgent'  # Medium risk gets urgent follow-up
        else:
            return 'routine'

    def _generate_action_recommendation(
            self,
            risk_level: str,
            red_flag_result: Dict[str, Any],
            session,
            complaint_group: str,
            age_group: str
    ) -> str:
        """Generate patient action recommendation - complaint-specific"""
        
        # Emergency override - highest priority
        if red_flag_result.get('emergency_override'):
            base_message = (
                "🚨 IMMEDIATE EMERGENCY ACTION REQUIRED 🚨\n\n"
                "Your symptoms indicate a LIFE-THREATENING EMERGENCY.\n\n"
                "• Call emergency services (911) IMMEDIATELY\n"
                "• Go to the nearest emergency facility RIGHT NOW\n"
                "• Do NOT wait - every minute matters\n"
                "• If possible, have someone drive you - do not drive yourself"
            )
            
            # Add specific emergency guidance
            if complaint_group == 'breathing':
                base_message += "\n\n• Keep patient in a comfortable position, usually sitting up"
            elif complaint_group == 'bleeding':
                base_message += "\n\n• Apply direct pressure to any bleeding wounds"
            elif complaint_group == 'chest_pain':
                base_message += "\n\n• Have patient rest and stay calm"
            
            return base_message
        
        # Get complaint-specific template if available
        if complaint_group in self.COMPLAINT_ACTIONS:
            template = self.COMPLAINT_ACTIONS[complaint_group].get(risk_level, "")
            if template:
                action = template
            else:
                action = self._get_general_action(risk_level)
        else:
            action = self._get_general_action(risk_level)
        
        # Add red flag context if present
        if red_flag_result.get('has_red_flags'):
            flags = red_flag_result.get('detected_flags', [])
            if flags:
                action = f"⚠️ DANGER SIGNS DETECTED: {', '.join(flags)}\n\n{action}"
        
        # Add age-specific note
        age_note = self.AGE_SPECIFIC_NOTES.get(age_group, "")
        if age_note:
            action = f"{age_note}\n\n{action}"
        
        return action

    def _get_general_action(self, risk_level: str) -> str:
        """Get general action recommendation"""
        if risk_level == 'high':
            return (
                "URGENT CARE REQUIRED: Your symptoms suggest a potentially serious condition.\n\n"
                "• Go to a hospital or health center TODAY\n"
                "• Do not delay seeking care\n"
                "• Bring a list of your symptoms and any medications\n"
                "• If symptoms worsen on the way, go to the nearest emergency facility"
            )
        elif risk_level == 'medium':
            return (
                "MEDICAL ATTENTION RECOMMENDED: Your symptoms should be evaluated.\n\n"
                "• Visit a health center within 24-48 hours\n"
                "• Monitor your symptoms closely\n"
                "• Seek URGENT care if symptoms worsen\n"
                "• Rest and avoid strenuous activity"
            )
        else:
            return (
                "SELF-CARE RECOMMENDED: Your symptoms appear mild at this time.\n\n"
                "• Rest and monitor your symptoms\n"
                "• Stay hydrated and eat nourishing food\n"
                "• Use over-the-counter remedies as appropriate\n"
                "• Seek care if symptoms persist beyond 3-5 days or worsen"
            )

    def _determine_facility_type(
            self,
            risk_level: str,
            red_flag_result: Dict[str, Any],
            complaint_group: str
    ) -> str:
        """Determine recommended facility type with complaint awareness"""
        
        has_red_flags = red_flag_result.get('has_red_flags', False)
        
        # Emergency override
        if red_flag_result.get('emergency_override'):
            return 'emergency'
        
        # Get base mapping
        if has_red_flags:
            facility = self.FACILITY_MAPPING.get(risk_level, {}).get('with_red_flags', 'hospital')
        else:
            facility = self.FACILITY_MAPPING.get(risk_level, {}).get('without_red_flags', 'self_care')
        
        # Complaint-specific overrides
        if complaint_group == 'pregnancy' and risk_level in ['medium', 'high']:
            return 'hospital'  # Pregnancy always needs hospital if concerning
        
        if complaint_group == 'chest_pain' and risk_level in ['medium']:
            return 'hospital'  # Chest pain always needs hospital even if medium
        
        return facility

    def _build_decision_reasoning(
            self,
            red_flag_result: Dict[str, Any],
            ai_risk: str,
            context_result: Dict[str, Any],
            final_risk: str,
            decision_basis: str,
            complaint_group: str,
            age_group: str
    ) -> str:
        """Build detailed reasoning explanation"""
        parts = []
        
        # Red flag information
        if red_flag_result.get('has_red_flags'):
            flags = red_flag_result.get('detected_flags', [])
            flags_readable = [f.replace('_', ' ').title() for f in flags[:3]]
            if len(flags) > 3:
                flags_readable.append(f"{len(flags)-3} more")
            
            parts.append(
                f"⚠️ EMERGENCY DANGER SIGNS: {', '.join(flags_readable)}. "
                "This requires immediate medical attention regardless of other factors."
            )
        
        # Decision basis explanation
        basis_explanations = {
            'red_flag_override': "Red flag symptoms override all other assessments.",
            'age_risk_modifier': f"Age group ({age_group}) significantly increases risk.",
            'clinical_adjustment': "Clinical context factors modify the risk assessment.",
            'complaint_specific': f"Complaint type ({complaint_group}) warrants elevated concern.",
            'ai_primary': "Based on primary AI risk assessment.",
            'conservative_bias': "Conservative safety bias applied (never downgrade risk)."
        }
        
        if decision_basis in basis_explanations:
            parts.append(f"Decision basis: {basis_explanations[decision_basis]}")
        
        # AI assessment
        parts.append(f"AI risk assessment: {ai_risk}")
        
        # Clinical context
        if context_result.get('adjustment_reasoning'):
            context_text = context_result['adjustment_reasoning']
            # Clean up context text
            if context_text != "No significant clinical context adjustments":
                parts.append(f"Clinical factors: {context_text}")
        
        # Final decision
        parts.append(f"Final risk determination: {final_risk.upper()}")
        
        return " | ".join(parts)

    def _generate_disclaimers(self, risk_level: str, age_group: str, complaint_group: str) -> List[str]:
        """Generate appropriate disclaimers"""
        
        # Base disclaimers always shown
        disclaimers = [
            "⚠️ This is NOT a medical diagnosis - it is a preliminary assessment only.",
            "📋 This assessment is based on the information you provided.",
            "🆘 Seek immediate medical care if your condition worsens at any time.",
        ]
        
        # Risk-specific disclaimers
        if risk_level == 'high':
            disclaimers.append(
                "🔴 HIGH RISK: This assessment suggests you need prompt medical attention. "
                "Do not delay seeking care based on this assessment."
            )
        elif risk_level == 'medium':
            disclaimers.append(
                "🟡 MEDIUM RISK: While not immediately life-threatening, your symptoms "
                "warrant professional evaluation soon."
            )
        else:
            disclaimers.append(
                "🟢 LOW RISK: Even mild symptoms can sometimes indicate serious conditions. "
                "Trust your judgment and seek care if concerned."
            )
        
        # Age-specific disclaimer
        if age_group in ['newborn', 'infant', 'elderly']:
            disclaimers.append(
                f"👤 Age consideration: {self.AGE_SPECIFIC_NOTES.get(age_group, '')}"
            )
        
        # General disclaimer
        disclaimers.append(
            "⚕️ This triage system is a decision support tool and does not replace "
            "professional medical judgment. Always follow the advice of healthcare providers."
        )
        
        return disclaimers

    def _determine_follow_up(
            self,
            follow_up_priority: str,
            risk_level: str,
            has_red_flags: bool,
            age_group: str
    ) -> Tuple[bool, str]:
        """Determine if follow-up is needed and timeframe"""
        
        # Timeframes by priority
        timeframes = {
            'immediate': "IMMEDIATE - within minutes",
            'urgent': "Within 24 hours",
            'routine': "Within 3-7 days if symptoms persist"
        }
        
        # Determine if follow-up required
        follow_up_required = follow_up_priority != 'routine' or has_red_flags or age_group in ['newborn', 'infant']
        
        # Get timeframe
        timeframe = timeframes.get(follow_up_priority, "As needed")
        
        # Age-specific adjustments
        if age_group in ['newborn', 'infant'] and follow_up_priority == 'routine':
            timeframe = "Within 24-48 hours (infants need closer monitoring)"
        
        return follow_up_required, timeframe


# Convenience function for external use
def synthesize_decision(
        session,
        red_flag_result: Dict[str, Any],
        ai_risk_level: str,
        context_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Synthesize final triage decision
    
    Args:
        session: TriageSession instance
        red_flag_result: Red flag detection results
        ai_risk_level: AI-determined risk level
        context_result: Clinical context adjustments

    Returns:
        Final decision dictionary
    """
    tool = DecisionSynthesisTool()
    return tool.synthesize(session, red_flag_result, ai_risk_level, context_result)