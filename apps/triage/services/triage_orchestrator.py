"""
Triage Orchestrator - UPDATED FOR COMPLAINT-BASED, AGE-ADAPTIVE TRIAGE
Coordinates all triage tools and manages the session lifecycle
"""

from django.utils import timezone
from apps.triage.models import (
    TriageSession,
    RedFlagDetection,
    RiskClassification,
    TriageDecision,
    ClinicalContext
)

# Import tools - only the ones we need for now
from apps.triage.tools.red_flag_detection import RedFlagDetectionTool
from apps.triage.tools.risk_classification import RiskClassificationTool
from apps.triage.tools.clinical_context import ClinicalContextTool
from apps.triage.tools.decision_synthesis import DecisionSynthesisTool

import logging

logger = logging.getLogger(__name__)


class TriageOrchestrator:
    """
    Triage Orchestrator - Coordinates all triage tools
    NO AGENT COMMUNICATION - Just saves to database
    """

    @staticmethod
    def run(patient_token: str, cleaned_data: dict, conversation_mode: bool = False):
        """
        Run the complete triage orchestration
        
        Args:
            patient_token: Anonymous patient identifier
            cleaned_data: Validated triage data
            conversation_mode: If True, updates existing session instead of creating new
        """
        from apps.triage.models import TriageSession
        from django.utils import timezone
        
        print("\n" + "="*70)
        print(f"🔄 TRIAGE ORCHESTRATOR - Token: {patient_token}")
        print("="*70)

        # Remove fields that shouldn't be set directly
        cleaned_data.pop("session_status", None)
        cleaned_data.pop("patient_token", None)
        cleaned_data.pop("assessment_completed_at", None)

        # ====================================================================
        # STEP 1: Get or create session with new model fields
        # ====================================================================
        
        # Handle deprecated fields mapping
        cleaned_data = TriageOrchestrator._map_deprecated_fields(cleaned_data)
        
        # Default values for new required fields if not present
        defaults = {
            "session_status": TriageSession.SessionStatus.IN_PROGRESS,
            "symptom_indicators": cleaned_data.get('symptom_indicators', {}),
            "red_flag_indicators": cleaned_data.get('red_flag_indicators', {}),
            "risk_modifiers": cleaned_data.get('risk_modifiers', {}),
            "conversation_turns": cleaned_data.get('conversation_turns', 1)
        }

        # Add demographic defaults if present
        if 'age_group' in cleaned_data:
            defaults['age_group'] = cleaned_data['age_group']
        if 'sex' in cleaned_data:
            defaults['sex'] = cleaned_data['sex']
        if 'patient_relation' in cleaned_data:
            defaults['patient_relation'] = cleaned_data.get('patient_relation', 'self')
        if 'complaint_text' in cleaned_data:
            defaults['complaint_text'] = cleaned_data['complaint_text']
        if 'complaint_group' in cleaned_data:
            defaults['complaint_group'] = cleaned_data['complaint_group']

        # Get or create session
        if conversation_mode:
            # In conversation mode, update existing session
            try:
                session = TriageSession.objects.get(patient_token=patient_token)
                created = False
                print(f"📝 Updating existing session (turns: {session.conversation_turns})")
            except TriageSession.DoesNotExist:
                # Fall back to create if doesn't exist
                session, created = TriageSession.objects.get_or_create(
                    patient_token=patient_token,
                    defaults=defaults
                )
                print(f"🆕 Created new session for conversation")
        else:
            # Traditional mode - get or create
            session, created = TriageSession.objects.get_or_create(
                patient_token=patient_token,
                defaults=defaults
            )
            print(f"{'🆕 Created new session' if created else '📝 Using existing session'}")

        # ====================================================================
        # STEP 2: Update session with all provided data
        # ====================================================================
        
        # Update all fields from cleaned_data
        update_fields = []
        for field, value in cleaned_data.items():
            if hasattr(session, field) and value is not None:
                # Handle special cases
                if field == 'symptom_indicators' and session.symptom_indicators:
                    # Merge symptom indicators instead of replace
                    current = session.symptom_indicators or {}
                    current.update(value)
                    setattr(session, field, current)
                elif field == 'red_flag_indicators' and session.red_flag_indicators:
                    # Merge red flag indicators
                    current = session.red_flag_indicators or {}
                    current.update(value)
                    setattr(session, field, current)
                elif field == 'risk_modifiers' and session.risk_modifiers:
                    # Merge risk modifiers
                    current = session.risk_modifiers or {}
                    current.update(value)
                    setattr(session, field, current)
                else:
                    setattr(session, field, value)
                
                update_fields.append(field)

        # Always update these fields
        session.session_status = TriageSession.SessionStatus.IN_PROGRESS
        update_fields.append('session_status')
        
        # Increment conversation turns if in conversation mode
        if conversation_mode:
            session.conversation_turns += 1
            update_fields.append('conversation_turns')

        if update_fields:
            session.save(update_fields=update_fields)
            print(f"✅ Session updated with {len(update_fields)} fields")
        else:
            print("✅ No fields to update")

        # ====================================================================
        # STEP 3: RED FLAG DETECTION (WHO ABCD)
        # ====================================================================
        
        try:
            red_flag_tool = RedFlagDetectionTool()
            red_flag_result = red_flag_tool.detect(session, cleaned_data)
        except Exception as e:
            print(f"⚠️ Red flag detection failed: {e}, using default")
            red_flag_result = {
                'has_red_flags': False,
                'emergency_override': False,
                'detected_flags': [],
                'red_flag_indicators': {},
                'highest_severity': None,
                'flags_with_context': []
            }

        # Update session with red flag results
        session.has_red_flags = red_flag_result.get('has_red_flags', False)
        session.red_flag_indicators = red_flag_result.get('red_flag_indicators', session.red_flag_indicators)
        
        # Set detection turn if first time
        if red_flag_result.get('has_red_flags', False) and not session.red_flag_detected_at_turn:
            session.red_flag_detected_at_turn = session.conversation_turns
        
        session.save(update_fields=['has_red_flags', 'red_flag_indicators', 'red_flag_detected_at_turn'])
        
        print(f"🚩 Red flags detected: {red_flag_result.get('has_red_flags', False)}")

        # ====================================================================
        # STEP 4: RISK CLASSIFICATION
        # ====================================================================
        
        if red_flag_result.get('emergency_override', False):
            # Emergency override - always high risk
            ai_risk_level = 'high'
            risk_confidence = 1.0
            risk_result = {
                'risk_level': 'high',
                'confidence': 1.0,
                'model_name': 'emergency_override',
                'model_version': '1.0',
                'raw_score': 1.0,
                'feature_importance': None
            }
            print("⚠️ EMERGENCY OVERRIDE - Risk set to HIGH")
        else:
            try:
                # Normal risk classification
                risk_tool = RiskClassificationTool()
                risk_result = risk_tool.classify(session, cleaned_data)
                ai_risk_level = risk_result['risk_level']
                risk_confidence = risk_result['confidence']
                
                # Save risk classification record
                RiskClassification.objects.update_or_create(
                    triage_session=session,
                    defaults={
                        'raw_risk_score': risk_result.get('raw_score', 0.5),
                        'ai_risk_level': ai_risk_level,
                        'confidence_score': risk_confidence,
                        'model_name': risk_result.get('model_name', 'default_model'),
                        'model_version': risk_result.get('model_version', '1.0'),
                        'inference_time_ms': risk_result.get('inference_time_ms'),
                        'feature_importance': risk_result.get('feature_importance'),
                        'complaint_embedding': risk_result.get('complaint_embedding')
                    }
                )
            except Exception as e:
                print(f"⚠️ Risk classification failed: {e}, using default")
                ai_risk_level = 'medium'
                risk_confidence = 0.5
                risk_result = {
                    'risk_level': 'medium',
                    'confidence': 0.5,
                    'model_name': 'fallback',
                    'model_version': '1.0',
                    'raw_score': 0.5,
                    'feature_importance': None
                }
            
            print(f"🤖 AI Risk: {ai_risk_level} (confidence: {risk_confidence:.2f})")

        # ====================================================================
        # STEP 5: CLINICAL CONTEXT
        # ====================================================================
        
        try:
            context_tool = ClinicalContextTool()
            context_result = context_tool.adjust_risk(
                session, cleaned_data, ai_risk_level, red_flag_result
            )
        except Exception as e:
            print(f"⚠️ Clinical context failed: {e}, using default")
            context_result = {
                'age_modifier': 0.0,
                'pregnancy_modifier': 0.0,
                'chronic_condition_modifier': 0.0,
                'immunocompromised_modifier': 0.0,
                'medication_modifier': 0.0,
                'total_adjustment': 0.0,
                'adjusted_risk_level': ai_risk_level,
                'adjustment_reasoning': 'No clinical context applied',
                'conservative_bias_applied': False
            }

        # Save clinical context record
        try:
            ClinicalContext.objects.update_or_create(
                triage_session=session,
                defaults={
                    'age_modifier': context_result.get('age_modifier', 0.0),
                    'pregnancy_modifier': context_result.get('pregnancy_modifier', 0.0),
                    'chronic_condition_modifier': context_result.get('chronic_condition_modifier', 0.0),
                    'immunocompromised_modifier': context_result.get('immunocompromised_modifier', 0.0),
                    'medication_modifier': context_result.get('medication_modifier', 0.0),
                    'total_risk_adjustment': context_result.get('total_adjustment', 0.0),
                    'adjustment_reasoning': context_result.get('adjustment_reasoning', ''),
                    'adjusted_risk_level': context_result.get('adjusted_risk_level', ai_risk_level),
                    'conservative_bias_applied': context_result.get('conservative_bias_applied', False)
                }
            )
        except Exception as e:
            print(f"⚠️ Failed to save clinical context: {e}")
        
        print(f"📊 Clinical adjustment: {context_result.get('total_adjustment', 0.0):+.2f}")

        # ====================================================================
        # STEP 6: DECISION SYNTHESIS
        # ====================================================================
        
        try:
            decision_tool = DecisionSynthesisTool()
            final_decision = decision_tool.synthesize(
                session=session,
                red_flag_result=red_flag_result,
                ai_risk_level=ai_risk_level,
                context_result=context_result
            )
        except Exception as e:
            print(f"⚠️ Decision synthesis failed: {e}, using default")
            final_decision = {
                'risk_level': ai_risk_level,
                'follow_up_priority': 'urgent' if ai_risk_level == 'high' else 'routine',
                'decision_basis': 'fallback',
                'recommended_action': 'Please seek medical attention at your nearest health facility.',
                'facility_type': 'hospital' if ai_risk_level == 'high' else 'health_center',
                'reasoning': 'Based on automated assessment.',
                'disclaimers': ['This is not a medical diagnosis.'],
                'follow_up_required': ai_risk_level != 'low',
                'follow_up_timeframe': '24 hours' if ai_risk_level == 'high' else '3-5 days'
            }

        # Save triage decision record
        try:
            TriageDecision.objects.update_or_create(
                triage_session=session,
                defaults={
                    'final_risk_level': final_decision['risk_level'],
                    'follow_up_priority': final_decision['follow_up_priority'],
                    'decision_basis': final_decision.get('decision_basis', 'ai_primary'),
                    'recommended_action': final_decision['recommended_action'],
                    'facility_type_recommendation': final_decision.get('facility_type'),
                    'decision_reasoning': final_decision.get('reasoning', ''),
                    'disclaimers': final_decision.get('disclaimers', []),
                }
            )
        except Exception as e:
            print(f"⚠️ Failed to save triage decision: {e}")

        # ====================================================================
        # STEP 7: Update session with final results
        # ====================================================================
        
        session.risk_level = final_decision['risk_level']
        session.risk_confidence = risk_confidence
        session.follow_up_priority = final_decision['follow_up_priority']
        session.assessment_completed_at = timezone.now()
        session.session_status = TriageSession.SessionStatus.COMPLETED
        
        # Update risk modifiers based on context
        if 'risk_modifiers' not in session.risk_modifiers:
            session.risk_modifiers = session.risk_modifiers or {}
            session.risk_modifiers.update({
                'age_modifier': context_result.get('age_modifier', 0.0),
                'pregnancy_modifier': context_result.get('pregnancy_modifier', 0.0),
                'chronic_modifier': context_result.get('chronic_condition_modifier', 0.0),
                'total_adjustment': context_result.get('total_adjustment', 0.0)
            })
        
        session.save()

        print("\n" + "="*70)
        print(f"✅ TRIAGE COMPLETE - Final Risk: {final_decision['risk_level']}")
        print(f"   Decision basis: {final_decision.get('decision_basis', 'unknown')}")
        print(f"   Conversation turns: {session.conversation_turns}")
        print("="*70 + "\n")

        return session, final_decision, red_flag_result

    @staticmethod
    def _map_deprecated_fields(cleaned_data: dict) -> dict:
        """
        Map deprecated fields to new field names for backward compatibility
        """
        # Create a copy to avoid modifying original
        data = cleaned_data.copy()
        
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
        
        # Map chronic_conditions list to has_chronic_conditions boolean
        if 'chronic_conditions' in data and 'has_chronic_conditions' not in data:
            chronic_list = data.get('chronic_conditions', [])
            # Check if any chronic condition (excluding 'none' and 'prefer_not_to_say')
            has_chronic = any(c not in ['none', 'prefer_not_to_say'] for c in chronic_list)
            data['has_chronic_conditions'] = has_chronic
            
            # Also add to risk_modifiers
            if 'risk_modifiers' not in data:
                data['risk_modifiers'] = {}
            if has_chronic:
                data['risk_modifiers']['chronic_conditions'] = chronic_list
        
        return data

    @staticmethod
    def run_conversation_turn(patient_token: str, turn_data: dict):
        """
        Run a single conversation turn in adaptive mode
        This is used by the conversation API for incremental updates
        """
        # Extract turn number
        turn_number = turn_data.pop('turn_number', 1)
        
        # Add conversation mode flag
        return TriageOrchestrator.run(
            patient_token=patient_token,
            cleaned_data=turn_data,
            conversation_mode=True
        )

    @staticmethod
    def get_session_status(patient_token: str):
        """
        Get current session status without running triage
        """
        try:
            session = TriageSession.objects.get(patient_token=patient_token)
            return {
                'exists': True,
                'session_status': session.session_status,
                'complaint_group': session.complaint_group,
                'age_group': session.age_group,
                'has_red_flags': session.has_red_flags,
                'conversation_turns': session.conversation_turns,
                'risk_level': session.risk_level,
                'completed': session.session_status == TriageSession.SessionStatus.COMPLETED
            }
        except TriageSession.DoesNotExist:
            return {
                'exists': False,
                'session_status': None
            }


# For backward compatibility, keep the original function signature
def run_triage_orchestrator(patient_token: str, cleaned_data: dict):
    """Legacy wrapper for backward compatibility"""
    return TriageOrchestrator.run(patient_token, cleaned_data)