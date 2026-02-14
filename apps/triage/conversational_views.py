"""
Conversational Triage API Views - FIXED VERSION
Properly handles conversation_id to maintain conversation state
"""

from rest_framework import status, views
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from apps.triage.tools.intake_validation import IntakeValidationTool
from apps.triage.services.triage_orchestrator import TriageOrchestrator


from apps.triage.tools.conversational_intake_agent import (
    IntakeValidationTool,
    process_conversational_intake
)


# ============================================================================
# SERIALIZERS
# ============================================================================

class ConversationalIntakeSerializer(serializers.Serializer):
    """Serializer for free-text conversational intake"""
    
    message = serializers.CharField(
        max_length=2000,
        help_text="Patient's free-text description or response"
    )
    
    conversation_id = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="Patient token from previous turn (for continuing conversation)"
    )


class ConversationalResponseSerializer(serializers.Serializer):
    """Serializer for conversational response"""
    
    status = serializers.ChoiceField(
        choices=['incomplete', 'complete'],
        help_text="Whether all required information has been collected"
    )
    
    action = serializers.CharField(
        help_text="Next action: answer_questions or proceed_to_validation"
    )
    
    questions = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Follow-up questions to ask the patient"
    )
    
    structured_data = serializers.DictField(
        required=False,
        help_text="Complete structured data (only when status=complete)"
    )
    
    confidence_scores = serializers.DictField(
        required=False,
        help_text="Confidence scores for extracted information"
    )
    
    extracted_so_far = serializers.DictField(
        required=False,
        help_text="Information extracted so far"
    )
    
    missing_fields = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Fields still missing"
    )
    
    progress = serializers.CharField(
        required=False,
        help_text="Progress indicator (e.g., '3/5 fields collected')"
    )
    
    patient_token = serializers.CharField(
        help_text="Patient token to use for next request"
    )


# ============================================================================
# API VIEWS - FIXED
# ============================================================================

class ConversationalTriageView(views.APIView):
    """
    POST /api/v1/triage/conversational/
    
    Process free-text conversational triage intake
    
    FIXED: Properly handles conversation_id to maintain state
    """
    
    permission_classes = [AllowAny]
    
    @extend_schema(
        request=ConversationalIntakeSerializer,
        responses={200: ConversationalResponseSerializer},
        description="Submit free-text description and receive adaptive questions or structured data"
    )
    def post(self, request):
        """
        Process conversational intake
        
        FLOW:
        1. First message: No conversation_id → starts new conversation
        2. Follow-up: Include conversation_id → continues conversation
        """
        
        print("\n" + "="*70)
        print("📥 CONVERSATIONAL TRIAGE REQUEST")
        print("="*70)
        print(f"Request data: {request.data}")
        
        serializer = ConversationalIntakeSerializer(data=request.data)
        if not serializer.is_valid():
            print(f"❌ Validation failed: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        message = serializer.validated_data['message']
        conversation_id = serializer.validated_data.get('conversation_id')
        
        print(f"Message: {message}")
        print(f"Conversation ID: {conversation_id}")
        
        # CRITICAL FIX: Determine if this is new or continuing
        if conversation_id:
            # CONTINUING existing conversation
            patient_token = conversation_id
            print(f"🔄 CONTINUING conversation with token: {patient_token}")
        else:
            # STARTING new conversation
            patient_token = self._generate_patient_token()
            print(f"🆕 STARTING new conversation with token: {patient_token}")
        
        try:
            # Create intake tool
            tool = IntakeValidationTool()
            
            # Process with conversational agent
            # CRITICAL: Pass conversation_id to trigger continue_conversation
            if conversation_id:
                print(f"   Calling process_intake with conversation_id={conversation_id}")
                result = tool.process_intake(
                    patient_token=patient_token,
                    free_text=message,
                    conversation_id=conversation_id  # This triggers continue_conversation
                )
            else:
                print(f"   Calling process_intake without conversation_id (new conversation)")
                result = tool.process_intake(
                    patient_token=patient_token,
                    free_text=message
                )
            
            print(f"✅ Processing complete")
            print(f"   Status: {result.get('status')}")
            print(f"   Patient token: {result.get('patient_token')}")
            
            # If complete, optionally auto-submit to regular triage
            if result.get('status') == 'complete':
                structured = result['structured_data']

                intake_tool = IntakeValidationTool()
                is_valid, cleaned_data, errors = intake_tool.validate(structured)

                if is_valid:
                    session, decision, red_flags = TriageOrchestrator.run(
                        result['patient_token'],
                        cleaned_data
                    )

                    result['triage_result'] = {
                        'risk_level': session.risk_level,
                        'priority': session.follow_up_priority
                    }

            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            print("="*70 + "\n")
            
            return Response({
                'error': 'Failed to process conversational intake',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _generate_patient_token(self) -> str:
        """Generate patient token"""
        import uuid
        return f"PT-{uuid.uuid4().hex[:16].upper()}"


class HybridTriageView(views.APIView):
    """
    POST /api/v1/triage/hybrid/{patient_token}/
    
    Hybrid endpoint that accepts either:
    - Structured data (original format)
    - Free-text conversational input
    """
    
    permission_classes = [AllowAny]
    
    def post(self, request, patient_token):
        """
        Accept either structured or conversational input
        
        Detects input type and routes to appropriate handler
        """
        
        # Check if it's conversational (has 'message' field)
        if 'message' in request.data:
            # Conversational input
            message = request.data['message']
            
            # Use the token from URL
            tool = IntakeValidationTool()
            result = tool.process_intake(
                patient_token=patient_token,
                free_text=message,
                conversation_id=patient_token  # Use token as conversation_id
            )
            
            return Response(result, status=status.HTTP_200_OK)
        
        else:
            # Structured input - use original validation
            tool = IntakeValidationTool()
            is_valid, cleaned_data, errors = tool.validate(request.data)
            
            if not is_valid:
                return Response({
                    'error': 'Validation failed',
                    'errors': errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                'status': 'complete',
                'structured_data': cleaned_data
            }, status=status.HTTP_200_OK)


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

"""
CORRECT USAGE:

Request 1 (Start):
POST /api/v1/triage/conversational/
{
    "message": "I have fever and headache for 3 days"
}

Response 1:
{
    "status": "incomplete",
    "patient_token": "PT-ABC123",  ← SAVE THIS!
    "questions": ["What is your age?", "Where are you?"],
    ...
}

Request 2 (Continue - USE THE TOKEN):
POST /api/v1/triage/conversational/
{
    "message": "I'm 25 years old in Kampala",
    "conversation_id": "PT-ABC123"  ← USE TOKEN FROM RESPONSE 1!
}

Response 2:
{
    "status": "complete",
    "structured_data": {
        "primary_symptom": "fever",  ← PRESERVED!
        "duration": "1_3_days",      ← PRESERVED!
        "age_range": "18_30",        ← ADDED!
        "district": "Kampala"        ← ADDED!
    }
}


WRONG USAGE (what you were doing):

Request 1:
{
    "message": "I have fever"
}

Request 2 (WRONG - no conversation_id):
{
    "message": "I'm 25 in Kampala"  ← STARTS NEW CONVERSATION!
}

This starts a NEW conversation, losing all previous data!
"""