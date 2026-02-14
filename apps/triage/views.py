"""
Triage API Views
REST API endpoints for triage agent
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
    TriageStatusSerializer
)

# Import tools
from apps.triage.tools.intake_validation import IntakeValidationTool
from apps.triage.tools.red_flag_detection import RedFlagDetectionTool
from apps.triage.tools.risk_classification import RiskClassificationTool
from apps.triage.tools.clinical_context import ClinicalContextTool
from apps.triage.tools.decision_synthesis import DecisionSynthesisTool
from apps.triage.tools.agent_communication import AgentCommunicationTool

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
            
            # DO NOT create session here
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
        
"""
FIXED SubmitTriageView - Replace the entire class in views.py
This version handles database saves explicitly to prevent rollback issues
"""

class SubmitTriageView(views.APIView):
    """
    POST /api/v1/triage/{patient_token}/submit/
    Submit complete triage data and receive risk assessment
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
                'red_flags': red_flag_result['detected_flags'],
                'recommended_action': final_decision['recommended_action'],
                'recommended_facility_type': final_decision['facility_type'],
                'symptom_summary': session.generate_symptom_summary(),
                'disclaimers': final_decision['disclaimers'],
                'assessment_completed_at': session.assessment_completed_at,
                'follow_up_required': final_decision['follow_up_required'],
                'follow_up_timeframe': final_decision.get('follow_up_timeframe', '24 hours')
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
    

class TriageResultView(views.APIView):
    """
    GET /api/v1/triage/{patient_token}/

    Retrieve triage results
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

            response_data = {
                'patient_token': patient_token,
                'risk_level': session.risk_level,
                'risk_confidence': session.risk_confidence,
                'follow_up_priority': session.follow_up_priority,
                'has_red_flags': session.has_red_flags,
                'red_flags': session.red_flags,
                'emergency_message': '',  # Add if needed
                'recommended_action': decision.recommended_action,
                'recommended_facility_type': decision.facility_type_recommendation,
                'symptom_summary': session.generate_symptom_summary(),
                'disclaimers': decision.disclaimers,
                'assessment_completed_at': session.assessment_completed_at,
                'follow_up_required': session.consent_follow_up,
                'follow_up_timeframe': '24 hours'
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except TriageSession.DoesNotExist:
            return Response({
                'error': 'Session not found'
            }, status=status.HTTP_404_NOT_FOUND)


class TriageStatusView(views.APIView):
    """
    GET /api/v1/triage/{patient_token}/status/

    Check triage session status
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
                'risk_level': session.risk_level,
                'has_red_flags': session.has_red_flags,
                'assessment_completed': session.session_status == TriageSession.SessionStatus.COMPLETED,
                'created_at': session.created_at,
                'assessment_completed_at': session.assessment_completed_at
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except TriageSession.DoesNotExist:
            return Response({
                'error': 'Session not found'
            }, status=status.HTTP_404_NOT_FOUND)