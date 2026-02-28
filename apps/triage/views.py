"""
Triage API Views
REST API endpoints for triage agent
UPDATED FOR COMPLAINT-BASED, AGE-ADAPTIVE TRIAGE
"""

from rest_framework import status, views
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils import timezone
from django.db import transaction
from drf_spectacular.utils import extend_schema, OpenApiParameter
from apps.triage.services.triage_orchestrator import TriageOrchestrator
from django.db import transaction

from apps.triage.models import (
    TriageSession,
    RedFlagDetection,
    RiskClassification,
    TriageDecision,
    AgentCommunicationLog,
    ClinicalContext
)
from apps.triage.serializers import (
    TriageIntakeSerializer,
    TriageSessionSerializer,
    TriageResultSerializer,
    TriageStatusSerializer,
    SymptomIndicatorUpdateSerializer  # NEW
)

# Import tools
from apps.triage.tools.intake_validation import IntakeValidationTool
from apps.triage.tools.red_flag_detection import RedFlagDetectionTool
from apps.triage.tools.risk_classification import RiskClassificationTool
from apps.triage.tools.clinical_context import ClinicalContextTool
from apps.triage.tools.decision_synthesis import DecisionSynthesisTool
from apps.triage.tools.agent_communication import AgentCommunicationTool
from apps.triage.tools.adaptive_questioning import AdaptiveQuestioningTool

import logging

logger = logging.getLogger(__name__)


class StartTriageView(views.APIView):
    """
    POST /api/v1/triage/start/
    Just generate a token, don't create session
    """
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            intake_tool = IntakeValidationTool()
            patient_token = intake_tool._generate_patient_token()
            
            logger.info(f"Token generated: {patient_token}")

            return Response({
                'patient_token': patient_token,
                'message': 'Use this token to submit triage data',
                'expires_in_minutes': 30
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error generating token: {str(e)}")
            return Response({
                'error': 'Failed to generate token',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StartConversationView(views.APIView):
    """
    NEW: POST /api/v1/triage/conversation/start/
    Start a new adaptive conversation with initial complaint
    """
    permission_classes = [AllowAny]

    @extend_schema(
        request=TriageIntakeSerializer,
        responses={201: TriageSessionSerializer},
        description="Start a new triage conversation with initial complaint"
    )
    def post(self, request):
        """
        Start a new triage conversation with initial complaint text
        This creates a session and returns the first question
        """
        try:
            # Validate initial data (minimal - just complaint and demographics)
            serializer = TriageIntakeSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({
                    'error': 'Invalid initial data',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            validated_data = serializer.validated_data

            # Generate patient token if not provided
            if 'patient_token' not in validated_data:
                intake_tool = IntakeValidationTool()
                patient_token = intake_tool._generate_patient_token()
            else:
                patient_token = validated_data['patient_token']

            # Create session with initial data
            with transaction.atomic():
                # Create the session
                session = TriageSession.objects.create(
                    patient_token=patient_token,
                    session_status=TriageSession.SessionStatus.IN_PROGRESS,
                    
                    # Complaint-based fields
                    complaint_text=validated_data.get('complaint_text', ''),
                    complaint_group=validated_data.get('complaint_group'),
                    
                    # Demographics
                    age_group=validated_data.get('age_group'),
                    sex=validated_data.get('sex'),
                    patient_relation=validated_data.get('patient_relation', 'self'),
                    
                    # Location
                    district=validated_data.get('district', ''),
                    subcounty=validated_data.get('subcounty', ''),
                    village=validated_data.get('village', ''),
                    location_consent=validated_data.get('location_consent', False),
                    device_location_lat=validated_data.get('device_location_lat'),
                    device_location_lng=validated_data.get('device_location_lng'),
                    
                    # Consent
                    consent_medical_triage=validated_data.get('consent_medical_triage', False),
                    consent_data_sharing=validated_data.get('consent_data_sharing', False),
                    consent_follow_up=validated_data.get('consent_follow_up', False),
                    
                    # Channel
                    channel=validated_data.get('channel', 'web'),
                    
                    # Initialize empty JSON fields
                    symptom_indicators={},
                    red_flag_indicators={},
                    risk_modifiers={},
                    conversation_turns=1
                )

                # Get first adaptive question based on complaint and age
                adaptive_tool = AdaptiveQuestioningTool()
                next_question = adaptive_tool.get_next_question(
                    session.complaint_group,
                    session.age_group,
                    session.symptom_indicators
                )

            logger.info(f"Conversation started for token: {patient_token}")

            # Return session data with next question
            session_serializer = TriageSessionSerializer(session)
            response_data = session_serializer.data
            response_data['next_question'] = next_question

            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error starting conversation: {str(e)}", exc_info=True)
            return Response({
                'error': 'Failed to start conversation',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UpdateSymptomsView(views.APIView):
    """
    NEW: POST /api/v1/triage/{patient_token}/update/
    Update symptom indicators during conversation
    """
    permission_classes = [AllowAny]

    @extend_schema(
        request=SymptomIndicatorUpdateSerializer,
        responses={200: dict},
        description="Update symptom indicators and get next question"
    )
    def post(self, request, patient_token):
        """
        Update symptom indicators based on user's answer and get next question
        """
        try:
            # Validate update data
            serializer = SymptomIndicatorUpdateSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({
                    'error': 'Invalid update data',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            validated_data = serializer.validated_data

            # Get session
            try:
                session = TriageSession.objects.get(patient_token=patient_token)
            except TriageSession.DoesNotExist:
                return Response({
                    'error': 'Session not found'
                }, status=status.HTTP_404_NOT_FOUND)

            # Update session with new indicators
            with transaction.atomic():
                # Update symptom indicators (merge with existing)
                current_indicators = session.symptom_indicators or {}
                current_indicators.update(validated_data.get('symptom_indicators', {}))
                session.symptom_indicators = current_indicators

                # Update red flag indicators (merge with existing)
                current_red_flags = session.red_flag_indicators or {}
                current_red_flags.update(validated_data.get('red_flag_indicators', {}))
                session.red_flag_indicators = current_red_flags

                # Check if any red flags are now True
                if not session.has_red_flags:
                    for value in current_red_flags.values():
                        if value:
                            session.has_red_flags = True
                            session.red_flag_detected_at_turn = validated_data.get('turn_number')
                            break

                # Increment conversation turns
                session.conversation_turns = validated_data.get('turn_number', session.conversation_turns + 1)
                
                session.save()

                # Check if triage can be completed (enough info gathered)
                adaptive_tool = AdaptiveQuestioningTool()
                
                # Determine if we have enough information
                has_enough_info = adaptive_tool.has_sufficient_information(
                    session.complaint_group,
                    session.age_group,
                    session.symptom_indicators
                )

                if has_enough_info or session.has_red_flags:
                    # We have enough info or red flags - complete the triage
                    # Run the orchestrator to get final decision
                    final_decision = self._complete_triage(session)
                    
                    return Response({
                        'status': 'complete',
                        'patient_token': patient_token,
                        'risk_level': final_decision['risk_level'],
                        'has_red_flags': session.has_red_flags,
                        'result': final_decision,
                        'conversation_turns': session.conversation_turns
                    }, status=status.HTTP_200_OK)
                else:
                    # Get next question
                    next_question = adaptive_tool.get_next_question(
                        session.complaint_group,
                        session.age_group,
                        session.symptom_indicators
                    )

                    return Response({
                        'status': 'in_progress',
                        'patient_token': patient_token,
                        'next_question': next_question,
                        'conversation_turns': session.conversation_turns,
                        'has_red_flags': session.has_red_flags
                    }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error updating symptoms for {patient_token}: {str(e)}", exc_info=True)
            return Response({
                'error': 'Failed to update symptoms',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _complete_triage(self, session):
        """Complete the triage process and return final decision"""
        # Prepare data for orchestrator
        triage_data = {
            'complaint_text': session.complaint_text,
            'complaint_group': session.complaint_group,
            'age_group': session.age_group,
            'sex': session.sex,
            'patient_relation': session.patient_relation,
            'symptom_indicators': session.symptom_indicators,
            'red_flag_indicators': session.red_flag_indicators,
            'district': session.district,
            'subcounty': session.subcounty,
            'village': session.village,
            'consent_medical_triage': session.consent_medical_triage,
            'consent_data_sharing': session.consent_data_sharing,
            'consent_follow_up': session.consent_follow_up,
            'channel': session.channel
        }

        # Run orchestrator
        with transaction.atomic():
            session, final_decision, red_flag_result = TriageOrchestrator.run(
                session.patient_token,
                triage_data
            )

        return final_decision


class SubmitTriageView(views.APIView):
    """
    POST /api/v1/triage/{patient_token}/submit/
    Submit complete triage data and receive risk assessment
    
    Note: This endpoint is being phased out in favor of the conversation-based flow
    Kept for backward compatibility
    """

    permission_classes = [AllowAny]

    @extend_schema(
        request=TriageIntakeSerializer,
        responses={200: TriageResultSerializer},
        description="Submit triage data and receive AI-powered risk assessment"
    )
    def post(self, request, patient_token):
        """
        Process complete triage submission
        """

        print("\n" + "="*70)
        print(f"🚀 TRIAGE SUBMISSION - Token: {patient_token}")
        print("="*70)

        try:
            # ------------------------------------------------------------
            # STEP 1: Validate request body (API validation)
            # ------------------------------------------------------------
            serializer = TriageIntakeSerializer(data=request.data)
            if not serializer.is_valid():
                print("❌ Validation failed:", serializer.errors)
                return Response({
                    'error': 'Invalid triage data',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            validated_data = serializer.validated_data

            # ------------------------------------------------------------
            # STEP 2: Medical intake validation (clinical validation)
            # ------------------------------------------------------------
            intake_tool = IntakeValidationTool()
            is_valid, cleaned_data, errors = intake_tool.validate(validated_data)

            if not is_valid:
                print("❌ Intake validation failed:", errors)
                return Response({
                    'error': 'Clinical validation failed',
                    'errors': errors
                }, status=status.HTTP_400_BAD_REQUEST)

            print("✅ Intake validation passed")
            print("Cleaned data:", cleaned_data)

            # ------------------------------------------------------------
            # STEP 3: Run the medical triage engine (THE ORCHESTRATOR)
            # ------------------------------------------------------------
            with transaction.atomic():
                session, final_decision, red_flag_result = TriageOrchestrator.run(
                    patient_token,
                    cleaned_data
                )

            print("✅ Orchestrator completed")
            print("Risk:", final_decision['risk_level'])

            # ------------------------------------------------------------
            # STEP 4: Build API response
            # ------------------------------------------------------------
            response_data = {
                'patient_token': patient_token,
                'risk_level': final_decision['risk_level'],
                'risk_confidence': session.risk_confidence,
                'follow_up_priority': final_decision['follow_up_priority'],
                'has_red_flags': red_flag_result['has_red_flags'],
                'red_flag_indicators': session.red_flag_indicators,  # Updated
                'red_flags': red_flag_result.get('detected_flags', []),  # Keep for backward compat
                'emergency_message': self._get_emergency_message(red_flag_result.get('detected_flags', [])),
                'recommended_action': final_decision['recommended_action'],
                'recommended_facility_type': final_decision['facility_type'],
                'symptom_summary': session.generate_symptom_summary(),
                'disclaimers': final_decision['disclaimers'],
                'assessment_completed_at': session.assessment_completed_at,
                'follow_up_required': final_decision['follow_up_required'],
                'follow_up_timeframe': final_decision.get('follow_up_timeframe', '24 hours'),
                # New fields
                'complaint_group': session.complaint_group,
                'age_group': session.age_group,
                'conversation_turns': session.conversation_turns
            }

            print("="*70)
            print("✅ TRIAGE COMPLETED SUCCESSFULLY")
            print("="*70 + "\n")

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            import traceback
            traceback.print_exc()

            logger.error(f"✗ Triage error for {patient_token}: {str(e)}", exc_info=True)

            return Response({
                'error': 'Triage processing failed',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _get_emergency_message(self, detected_flags):
        """Generate emergency message based on detected flags"""
        if not detected_flags:
            return ""
        
        if len(detected_flags) == 1:
            return f"⚠️ EMERGENCY: {detected_flags[0]} detected. Seek immediate care!"
        else:
            flags_list = ", ".join(detected_flags[:-1]) + " and " + detected_flags[-1]
            return f"⚠️ EMERGENCY: Multiple danger signs detected: {flags_list}. Seek immediate care!"


class TriageResultView(views.APIView):
    """
    GET /api/v1/triage/{patient_token}/
    Retrieve triage results - UPDATED
    """

    permission_classes = [AllowAny]

    @extend_schema(
        responses={200: TriageResultSerializer},
        description="Retrieve triage assessment results"
    )
    def get(self, request, patient_token):
        """
        Get triage results for a patient token
        """
        try:
            session = TriageSession.objects.get(patient_token=patient_token)

            if session.session_status != TriageSession.SessionStatus.COMPLETED:
                return Response({
                    'error': 'Assessment not completed',
                    'session_status': session.session_status,
                    'message': 'Triage assessment is still in progress or not started'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Get decision
            try:
                decision = session.triage_decision
            except TriageDecision.DoesNotExist:
                return Response({
                    'error': 'No decision found for this session'
                }, status=status.HTTP_404_NOT_FOUND)

            # Get red flag detection
            try:
                red_flags = session.red_flag_detection
                detected_flags = red_flags.get_detected_flag_names() if red_flags else []
            except RedFlagDetection.DoesNotExist:
                detected_flags = []

            response_data = {
                'patient_token': patient_token,
                'risk_level': session.risk_level,
                'risk_confidence': session.risk_confidence,
                'follow_up_priority': session.follow_up_priority,
                'has_red_flags': session.has_red_flags,
                'red_flag_indicators': session.red_flag_indicators,  # Updated
                'red_flags': detected_flags,  # Keep for backward compatibility
                'emergency_message': self._get_emergency_message(detected_flags),
                'recommended_action': decision.recommended_action,
                'recommended_facility_type': decision.facility_type_recommendation,
                'symptom_summary': session.generate_symptom_summary(),
                'disclaimers': decision.disclaimers,
                'assessment_completed_at': session.assessment_completed_at,
                'follow_up_required': session.consent_follow_up,
                'follow_up_timeframe': '24 hours',
                # New fields
                'complaint_group': session.complaint_group,
                'age_group': session.age_group,
                'conversation_turns': session.conversation_turns
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except TriageSession.DoesNotExist:
            return Response({
                'error': 'Session not found'
            }, status=status.HTTP_404_NOT_FOUND)

    def _get_emergency_message(self, detected_flags):
        """Generate emergency message based on detected flags"""
        if not detected_flags:
            return ""
        
        if len(detected_flags) == 1:
            return f"⚠️ EMERGENCY: {detected_flags[0]} detected. Seek immediate care!"
        else:
            flags_list = ", ".join(detected_flags[:-1]) + " and " + detected_flags[-1]
            return f"⚠️ EMERGENCY: Multiple danger signs detected: {flags_list}. Seek immediate care!"


class TriageStatusView(views.APIView):
    """
    GET /api/v1/triage/{patient_token}/status/
    Check triage session status - UPDATED
    """

    permission_classes = [AllowAny]

    @extend_schema(
        responses={200: TriageStatusSerializer},
        description="Check triage session status"
    )
    def get(self, request, patient_token):
        """
        Check status of triage session
        """
        try:
            session = TriageSession.objects.get(patient_token=patient_token)

            response_data = {
                'patient_token': patient_token,
                'session_status': session.session_status,
                'complaint_group': session.complaint_group,  # New
                'age_group': session.age_group,  # New
                'risk_level': session.risk_level,
                'has_red_flags': session.has_red_flags,
                'assessment_completed': session.session_status == TriageSession.SessionStatus.COMPLETED,
                'created_at': session.created_at,
                'assessment_completed_at': session.assessment_completed_at,
                'conversation_turns': session.conversation_turns  # New
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except TriageSession.DoesNotExist:
            return Response({
                'error': 'Session not found'
            }, status=status.HTTP_404_NOT_FOUND)


class GetNextQuestionView(views.APIView):
    """
    NEW: GET /api/v1/triage/{patient_token}/next-question/
    Get the next question in the adaptive conversation
    """
    permission_classes = [AllowAny]

    def get(self, request, patient_token):
        """
        Get the next question for an in-progress conversation
        """
        try:
            session = TriageSession.objects.get(patient_token=patient_token)

            if session.session_status != TriageSession.SessionStatus.IN_PROGRESS:
                return Response({
                    'error': 'Session not in progress',
                    'session_status': session.session_status
                }, status=status.HTTP_400_BAD_REQUEST)

            # Get next question
            adaptive_tool = AdaptiveQuestioningTool()
            next_question = adaptive_tool.get_next_question(
                session.complaint_group,
                session.age_group,
                session.symptom_indicators
            )

            return Response({
                'patient_token': patient_token,
                'next_question': next_question,
                'conversation_turns': session.conversation_turns,
                'has_red_flags': session.has_red_flags
            }, status=status.HTTP_200_OK)

        except TriageSession.DoesNotExist:
            return Response({
                'error': 'Session not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error getting next question for {patient_token}: {str(e)}", exc_info=True)
            return Response({
                'error': 'Failed to get next question',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
# Add these to your apps/triage/views.py file, after the existing imports and before the view classes

class TriageHealthCheckView(views.APIView):
    """
    GET /api/v1/triage/health/
    
    Health check endpoint to verify the triage service is running
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Return health status of triage service"""
        from django.db import connection
        from django.db.utils import OperationalError
        
        # Check database connection
        db_status = "healthy"
        try:
            connection.ensure_connection()
        except OperationalError:
            db_status = "unhealthy"
        
        # Check if essential tools are available
        tools_status = {}
        try:
            from apps.triage.tools.intake_validation import IntakeValidationTool
            tools_status['intake_validation'] = 'available'
        except ImportError:
            tools_status['intake_validation'] = 'unavailable'
            
        try:
            from apps.triage.tools.red_flag_detection import RedFlagDetectionTool
            tools_status['red_flag_detection'] = 'available'
        except ImportError:
            tools_status['red_flag_detection'] = 'unavailable'
            
        try:
            from apps.triage.tools.risk_classification import RiskClassificationTool
            tools_status['risk_classification'] = 'available'
        except ImportError:
            tools_status['risk_classification'] = 'unavailable'
            
        try:
            from apps.triage.tools.clinical_context import ClinicalContextTool
            tools_status['clinical_context'] = 'available'
        except ImportError:
            tools_status['clinical_context'] = 'unavailable'
            
        try:
            from apps.triage.tools.decision_synthesis import DecisionSynthesisTool
            tools_status['decision_synthesis'] = 'available'
        except ImportError:
            tools_status['decision_synthesis'] = 'unavailable'
        
        return Response({
            'status': 'healthy' if db_status == 'healthy' else 'unhealthy',
            'timestamp': timezone.now(),
            'database': db_status,
            'tools': tools_status,
            'version': '2.0.0',  # New version for complaint-based model
            'features': {
                'complaint_based': True,
                'age_adaptive': True,
                'conversational': True,
                'who_abcd_red_flags': True
            }
        }, status=status.HTTP_200_OK)


class TriageOptionsView(views.APIView):
    """
    GET /api/v1/triage/options/
    
    Get available form options for frontend dropdowns
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Return all valid choices for form fields"""
        
        options = {
            # Complaint groups (NEW)
            'complaint_groups': [
                {'value': 'fever', 'label': 'Fever / feeling hot'},
                {'value': 'breathing', 'label': 'Breathing or cough problem'},
                {'value': 'injury', 'label': 'Injury or accident'},
                {'value': 'abdominal', 'label': 'Abdominal pain / vomiting / diarrhea'},
                {'value': 'headache', 'label': 'Headache / confusion / weakness'},
                {'value': 'chest_pain', 'label': 'Chest pain'},
                {'value': 'pregnancy', 'label': 'Pregnancy concern'},
                {'value': 'skin', 'label': 'Skin problem'},
                {'value': 'feeding', 'label': 'Feeding problem / general weakness'},
                {'value': 'bleeding', 'label': 'Bleeding / blood loss'},
                {'value': 'mental_health', 'label': 'Mental health / emotional crisis'},
                {'value': 'other', 'label': 'Other'},
            ],
            
            # Age groups (NEW - 7 categories)
            'age_groups': [
                {'value': 'newborn', 'label': 'Newborn (0-2 months)'},
                {'value': 'infant', 'label': 'Infant (2-12 months)'},
                {'value': 'child_1_5', 'label': 'Child (1-5 years)'},
                {'value': 'child_6_12', 'label': 'Child (6-12 years)'},
                {'value': 'teen', 'label': 'Teen (13-17 years)'},
                {'value': 'adult', 'label': 'Adult (18-64 years)'},
                {'value': 'elderly', 'label': 'Elderly (65+ years)'},
            ],
            
            # Sex
            'sex': [
                {'value': 'male', 'label': 'Male'},
                {'value': 'female', 'label': 'Female'},
                {'value': 'other', 'label': 'Other / Prefer not to say'},
            ],
            
            # Patient relation (NEW)
            'patient_relations': [
                {'value': 'self', 'label': 'For myself'},
                {'value': 'child', 'label': 'For my child'},
                {'value': 'family', 'label': 'For family member'},
                {'value': 'other', 'label': 'For someone else'},
            ],
            
            # Symptom severity (UPDATED with descriptions)
            'symptom_severities': [
                {'value': 'mild', 'label': 'Mild - can do normal activities'},
                {'value': 'moderate', 'label': 'Moderate - some difficulty with activities'},
                {'value': 'severe', 'label': 'Severe - unable to do normal activities'},
                {'value': 'very_severe', 'label': 'Very severe - unable to move/talk/function'},
            ],
            
            # Symptom duration (EXPANDED)
            'symptom_durations': [
                {'value': 'less_than_1_hour', 'label': 'Less than 1 hour'},
                {'value': '1_6_hours', 'label': '1-6 hours'},
                {'value': '6_24_hours', 'label': '6-24 hours'},
                {'value': '1_3_days', 'label': '1-3 days'},
                {'value': '4_7_days', 'label': '4-7 days'},
                {'value': 'more_than_1_week', 'label': 'More than 1 week'},
                {'value': 'more_than_1_month', 'label': 'More than 1 month'},
            ],
            
            # Progression status (NEW - replaces symptom pattern)
            'progression_statuses': [
                {'value': 'sudden', 'label': 'Sudden onset'},
                {'value': 'getting_worse', 'label': 'Getting worse'},
                {'value': 'staying_same', 'label': 'Staying the same'},
                {'value': 'getting_better', 'label': 'Getting better'},
                {'value': 'comes_and_goes', 'label': 'Comes and goes'},
            ],
            
            # Pregnancy status (UPDATED)
            'pregnancy_statuses': [
                {'value': 'yes', 'label': 'Yes, confirmed pregnant'},
                {'value': 'possible', 'label': 'Possibly pregnant'},
                {'value': 'no', 'label': 'No'},
                {'value': 'not_applicable', 'label': 'Not applicable'},
            ],
            
            # Channels
            'channels': [
                {'value': 'ussd', 'label': 'USSD'},
                {'value': 'sms', 'label': 'SMS'},
                {'value': 'whatsapp', 'label': 'WhatsApp'},
                {'value': 'web', 'label': 'Web'},
                {'value': 'mobile_app', 'label': 'Mobile App'},
            ],
            
            # Risk levels
            'risk_levels': [
                {'value': 'low', 'label': 'Low Risk'},
                {'value': 'medium', 'label': 'Medium Risk'},
                {'value': 'high', 'label': 'High Risk'},
            ],
            
            # Follow-up priorities
            'follow_up_priorities': [
                {'value': 'routine', 'label': 'Routine'},
                {'value': 'urgent', 'label': 'Urgent'},
                {'value': 'immediate', 'label': 'Immediate'},
            ],
            
            # Session statuses
            'session_statuses': [
                {'value': 'started', 'label': 'Started'},
                {'value': 'in_progress', 'label': 'In Progress'},
                {'value': 'completed', 'label': 'Completed'},
                {'value': 'escalated', 'label': 'Escalated'},
                {'value': 'cancelled', 'label': 'Cancelled'},
            ],
            
            # WHO ABCD red flag categories (NEW)
            'red_flag_categories': [
                {'category': 'airway', 'label': 'Airway (A)'},
                {'category': 'breathing', 'label': 'Breathing (B)'},
                {'category': 'circulation', 'label': 'Circulation (C)'},
                {'category': 'disability', 'label': 'Disability (D)'},
                {'category': 'age_specific', 'label': 'Age Specific'},
                {'category': 'pregnancy', 'label': 'Pregnancy'},
            ],
            
            # Facility types
            'facility_types': [
                {'value': 'emergency', 'label': 'Emergency Department - IMMEDIATE'},
                {'value': 'hospital', 'label': 'Hospital - Urgent'},
                {'value': 'health_center', 'label': 'Health Center - Soon'},
                {'value': 'clinic', 'label': 'Clinic - Routine'},
                {'value': 'self_care', 'label': 'Self-care with monitoring'},
            ],
        }
        
        return Response(options, status=status.HTTP_200_OK)