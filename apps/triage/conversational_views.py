"""
Conversational Triage API Views - UPDATED FOR COMPLAINT-BASED MODEL
Properly handles conversation_id to maintain conversation state
Now supports age-adaptive, complaint-based triage flow
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
# SERIALIZERS - UPDATED for complaint-based model
# ============================================================================

class ConversationalIntakeSerializer(serializers.Serializer):
    """Serializer for free-text conversational intake - UPDATED"""
    
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
    
    channel = serializers.ChoiceField(
        choices=['whatsapp', 'sms', 'ussd', 'web', 'mobile_app'],
        default='whatsapp',
        required=False,
        help_text="Communication channel"
    )


class ConversationalResponseSerializer(serializers.Serializer):
    """Serializer for conversational response - UPDATED"""
    
    status = serializers.ChoiceField(
        choices=['incomplete', 'complete'],
        help_text="Whether all required information has been collected"
    )
    
    action = serializers.CharField(
        help_text="Next action: answer_questions or proceed_to_triage"
    )
    
    intent = serializers.ChoiceField(
        choices=['routine', 'emergency', 'follow_up'],
        required=False,
        help_text="Detected conversation intent"
    )
    
    message = serializers.CharField(
        required=False,
        help_text="Natural language response/message for the patient"
    )
    
    questions = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Follow-up questions to ask the patient (backward compatibility)"
    )
    
    structured_data = serializers.DictField(
        required=False,
        help_text="Complete structured data (only when status=complete)"
    )
    
    # NEW: Red flag information
    red_flags_detected = serializers.BooleanField(
        required=False,
        help_text="Whether red flags have been detected"
    )
    
    red_flag_message = serializers.CharField(
        required=False,
        help_text="Emergency message if red flags detected"
    )
    
    # Extracted information
    extracted_so_far = serializers.DictField(
        required=False,
        help_text="Information extracted so far including complaint_group, age_group, etc."
    )
    
    missing_fields = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Fields still missing"
    )
    
    # NEW: Complaint-specific fields
    complaint_group = serializers.CharField(
        required=False,
        help_text="Detected complaint group"
    )
    
    age_group = serializers.CharField(
        required=False,
        help_text="Detected age group"
    )
    
    # Progress tracking
    progress = serializers.CharField(
        required=False,
        help_text="Progress indicator (e.g., '3/7 fields collected')"
    )
    
    conversation_turns = serializers.IntegerField(
        required=False,
        help_text="Number of conversation turns so far"
    )
    
    patient_token = serializers.CharField(
        help_text="Patient token to use for next request"
    )
    
    # NEW: Clinical suggestions
    clinical_suggestions = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        help_text="Clinical suggestions based on symptoms"
    )
    
    # NEW: Confidence scores
    confidence_scores = serializers.DictField(
        required=False,
        help_text="Confidence scores for extracted information"
    )


class HybridTriageResponseSerializer(serializers.Serializer):
    """Serializer for hybrid triage response - UPDATED"""
    
    status = serializers.CharField()
    structured_data = serializers.DictField(required=False)
    message = serializers.CharField(required=False)
    patient_token = serializers.CharField()
    red_flags_detected = serializers.BooleanField(required=False)
    triage_result = serializers.DictField(required=False)


# ============================================================================
# API VIEWS - UPDATED
# ============================================================================

class ConversationalTriageView(views.APIView):
    """
    POST /api/v1/triage/conversational/
    
    Process free-text conversational triage intake - UPDATED
    Now supports complaint-based, age-adaptive triage
    
    FLOW:
    1. First message: No conversation_id → starts new conversation
    2. Follow-up: Include conversation_id → continues conversation
    3. Emergency detected: Returns red flag warnings immediately
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
        
        NEW FEATURES:
        - Complaint group detection (fever, breathing, chest_pain, etc.)
        - Age group detection (newborn to elderly)
        - Red flag detection (WHO ABCD danger signs)
        - Clinical suggestions
        - Confidence scores
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
        channel = serializer.validated_data.get('channel', 'whatsapp')
        
        print(f"Message: {message[:100]}...")
        print(f"Conversation ID: {conversation_id}")
        print(f"Channel: {channel}")
        
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
            
            # Add channel to result
            result['channel'] = channel
            
            print(f"✅ Processing complete")
            print(f"   Status: {result.get('status')}")
            print(f"   Intent: {result.get('intent')}")
            print(f"   Patient token: {result.get('patient_token')}")
            
            # Check for red flags
            if result.get('red_flags_detected'):
                print(f"   🚩 RED FLAGS DETECTED!")
            
            # If complete, optionally auto-submit to regular triage
            # If complete, optionally auto-submit to regular triage
            if result.get('status') == 'complete':
                structured = result['structured_data']
                
                # Check if triage_result is already in the result (from agent)
                if 'triage_result' in result:
                    print(f"   ✅ Triage already completed by agent: {result['triage_result'].get('risk_level')}")
                else:
                    # Fallback: validate and submit manually
                    intake_tool = IntakeValidationTool()
                    is_valid, cleaned_data, errors = intake_tool.validate(structured)
                    
                    if is_valid:
                        print(f"   🎯 Auto-submitting to triage orchestrator")
                        session, decision, red_flags = TriageOrchestrator.run(
                            result['patient_token'],
                            cleaned_data
                        )
                        
                        # Add triage result to response
                        result['triage_result'] = {
                            'risk_level': session.risk_level,
                            'priority': session.follow_up_priority,
                            'decision_basis': decision.get('decision_basis'),
                            'facility_type': decision.get('facility_type')
                        }
                        
                        print(f"   Triage result: {session.risk_level}")
                    else:
                        print(f"   ❌ Validation failed: {errors}")
                        result['validation_errors'] = errors            
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


class ConversationalStatusView(views.APIView):
    """
    GET /api/v1/triage/conversational/{patient_token}/status/
    
    Get current status of a conversation
    NEW: Check progress, red flags, and extracted info
    """
    
    permission_classes = [AllowAny]
    
    def get(self, request, patient_token):
        """Get conversation status"""
        
        try:
            from apps.conversations.models import Conversation
            
            conversation = Conversation.objects.get(patient_token=patient_token)
            
            # Get extracted state
            extracted_state = conversation.extracted_state or {}
            
            # Calculate progress
            required_fields = [
                "complaint_group", "age_group", "sex", "severity", 
                "duration", "location"
            ]
            
            collected = sum(1 for field in required_fields if extracted_state.get(field))
            total = len(required_fields)
            progress = f"{collected}/{total} fields collected"
            
            # Check for red flags
            red_flags_detected = bool(extracted_state.get('red_flag_indicators'))
            
            # Get last message
            last_message = conversation.messages.last()
            
            return Response({
                'patient_token': patient_token,
                'status': 'in_progress' if not conversation.completed else 'completed',
                'completed': conversation.completed,
                'intent': conversation.intent,
                'red_flags_detected': red_flags_detected,
                'extracted_so_far': extracted_state,
                'progress': progress,
                'conversation_turns': conversation.turn_number,
                'last_message': last_message.content if last_message else None,
                'last_message_time': last_message.created_at if last_message else None
            }, status=status.HTTP_200_OK)
            
        except Conversation.DoesNotExist:
            return Response({
                'error': 'Conversation not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ConversationalHistoryView(views.APIView):
    """
    GET /api/v1/triage/conversational/{patient_token}/history/
    
    Get full conversation history
    NEW: View complete conversation transcripta
    """
    
    permission_classes = [AllowAny]
    
    def get(self, request, patient_token):
        """Get conversation history"""
        
        try:
            from apps.conversations.models import Conversation
            
            conversation = Conversation.objects.get(patient_token=patient_token)
            messages = conversation.messages.all().order_by('turn')
            
            history = [
                {
                    'turn': msg.turn,
                    'role': msg.role,
                    'content': msg.content,
                    'time': msg.created_at
                }
                for msg in messages
            ]
            
            return Response({
                'patient_token': patient_token,
                'intent': conversation.intent,
                'completed': conversation.completed,
                'total_turns': conversation.turn_number,
                'history': history,
                'extracted_state': conversation.extracted_state
            }, status=status.HTTP_200_OK)
            
        except Conversation.DoesNotExist:
            return Response({
                'error': 'Conversation not found'
            }, status=status.HTTP_404_NOT_FOUND)


class ConversationalResetView(views.APIView):
    """
    POST /api/v1/triage/conversational/{patient_token}/reset/
    
    Reset a conversation and start fresh
    NEW: Clear conversation state
    """
    
    permission_classes = [AllowAny]
    
    def post(self, request, patient_token):
        """Reset conversation"""
        
        try:
            from apps.conversations.models import Conversation
            from apps.conversations.models import Message
            
            # Delete all messages
            conversation = Conversation.objects.get(patient_token=patient_token)
            Message.objects.filter(conversation=conversation).delete()
            
            # Reset conversation
            conversation.turn_number = 0
            conversation.intent = 'routine'
            conversation.completed = False
            conversation.extracted_state = {}
            conversation.save()
            
            return Response({
                'status': 'reset',
                'patient_token': patient_token,
                'message': 'Conversation reset successfully'
            }, status=status.HTTP_200_OK)
            
        except Conversation.DoesNotExist:
            return Response({
                'error': 'Conversation not found'
            }, status=status.HTTP_404_NOT_FOUND)


class HybridTriageView(views.APIView):
    """
    POST /api/v1/triage/hybrid/{patient_token}/
    
    Hybrid endpoint that accepts either:
    - Structured data (original format)
    - Free-text conversational input
    
    UPDATED: Now supports new complaint-based fields
    """
    
    permission_classes = [AllowAny]
    
    @extend_schema(
        request={
            'application/json': {
                'oneOf': [
                    {
                        'type': 'object',
                        'properties': {
                            'message': {'type': 'string'},
                            'channel': {'type': 'string'}
                        }
                    },
                    {
                        'type': 'object',
                        'properties': {
                            'complaint_group': {'type': 'string'},
                            'age_group': {'type': 'string'},
                            'sex': {'type': 'string'},
                            'symptom_severity': {'type': 'string'},
                            'symptom_duration': {'type': 'string'},
                            'district': {'type': 'string'}
                        }
                    }
                ]
            }
        },
        responses={200: HybridTriageResponseSerializer}
    )
    def post(self, request, patient_token):
        """
        Accept either structured or conversational input
        
        Detects input type and routes to appropriate handler
        """
        
        print(f"\n🔄 HYBRID TRIAGE - Token: {patient_token}")
        
        # Check if it's conversational (has 'message' field)
        if 'message' in request.data:
            # Conversational input
            message = request.data['message']
            channel = request.data.get('channel', 'web')
            
            print(f"   Conversational mode: {message[:50]}...")
            
            # Use the token from URL
            tool = IntakeValidationTool()
            result = tool.process_intake(
                patient_token=patient_token,
                free_text=message,
                conversation_id=patient_token  # Use token as conversation_id
            )
            
            # If complete, auto-submit to triage
            if result.get('status') == 'complete':
                structured = result['structured_data']
                
                intake_tool = IntakeValidationTool()
                is_valid, cleaned_data, errors = intake_tool.validate(structured)
                
                if is_valid:
                    session, decision, red_flags = TriageOrchestrator.run(
                        patient_token,
                        cleaned_data
                    )
                    
                    result['triage_result'] = {
                        'risk_level': session.risk_level,
                        'priority': session.follow_up_priority
                    }
            
            return Response(result, status=status.HTTP_200_OK)
        
        else:
            # Structured input - use original validation
            print(f"   Structured mode: {list(request.data.keys())}")
            
            tool = IntakeValidationTool()
            is_valid, cleaned_data, errors = tool.validate(request.data)
            
            if not is_valid:
                print(f"   ❌ Validation failed: {errors}")
                return Response({
                    'error': 'Validation failed',
                    'errors': errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Auto-submit to triage
            print(f"   ✅ Valid, submitting to orchestrator")
            session, decision, red_flags = TriageOrchestrator.run(
                patient_token,
                cleaned_data
            )
            
            return Response({
                'status': 'complete',
                'structured_data': cleaned_data,
                'patient_token': patient_token,
                'red_flags_detected': red_flags.get('has_red_flags', False),
                'triage_result': {
                    'risk_level': session.risk_level,
                    'priority': session.follow_up_priority
                }
            }, status=status.HTTP_200_OK)


# ============================================================================
# USAGE EXAMPLES - UPDATED
# ============================================================================

"""
CORRECT USAGE WITH NEW MODEL:

Request 1 (Start):
POST /api/v1/triage/conversational/
{
    "message": "My 2-year-old child has fever and is coughing for 2 days"
}

Response 1:
{
    "status": "incomplete",
    "patient_token": "PT-ABC123",  ← SAVE THIS!
    "intent": "routine",
    "complaint_group": "fever",
    "age_group": "child_1_5",
    "extracted_so_far": {
        "complaint_group": "fever",
        "age_group": "child_1_5",
        "severity": "moderate",
        "duration": "1_3_days",
        "patient_relation": "child"
    },
    "message": "Is your child able to drink fluids normally?",
    "missing_fields": ["severity", "location", "consents"],
    "progress": "3/7 fields collected",
    "conversation_turns": 1
}

Request 2 (Continue - USE THE TOKEN):
POST /api/v1/triage/conversational/
{
    "message": "Yes, he's drinking well. We are in Kampala",
    "conversation_id": "PT-ABC123"  ← USE TOKEN FROM RESPONSE 1!
}

Response 2:
{
    "status": "incomplete",
    "patient_token": "PT-ABC123",
    "message": "Has he had any difficulty breathing or chest indrawing?",
    "extracted_so_far": {
        "complaint_group": "fever",
        "age_group": "child_1_5",
        "severity": "moderate",
        "duration": "1_3_days",
        "location": "Kampala",
        "symptom_indicators": {
            "cough": true,
            "can_drink": true
        }
    },
    "missing_fields": ["consents"],
    "progress": "6/7 fields collected",
    "conversation_turns": 2
}

Request 3 (Final):
POST /api/v1/triage/conversational/
{
    "message": "No breathing difficulty. Yes I consent to proceed",
    "conversation_id": "PT-ABC123"
}

Response 3:
{
    "status": "complete",
    "patient_token": "PT-ABC123",
    "structured_data": {
        "complaint_text": "My 2-year-old child has fever and is coughing for 2 days",
        "complaint_group": "fever",
        "age_group": "child_1_5",
        "sex": null,
        "patient_relation": "child",
        "symptom_indicators": {
            "cough": true,
            "can_drink": true
        },
        "symptom_severity": "moderate",
        "symptom_duration": "1_3_days",
        "district": "Kampala"
    },
    "triage_result": {
        "risk_level": "medium",
        "priority": "urgent"
    }
}


EMERGENCY DETECTION EXAMPLE:

POST /api/v1/triage/conversational/
{
    "message": "My baby is struggling to breathe and is very sleepy"
}

Response (Immediate):
{
    "status": "complete",
    "patient_token": "PT-EMERG123",
    "red_flags_detected": true,
    "red_flag_message": "🚨 EMERGENCY: Severe breathing difficulty detected. This is life-threatening. Please go to the nearest emergency facility IMMEDIATELY!",
    "structured_data": {
        "complaint_group": "breathing",
        "age_group": "infant",
        "red_flag_indicators": {
            "severe_breathing_difficulty": true,
            "lethargic_floppy": true
        }
    }
}
"""

