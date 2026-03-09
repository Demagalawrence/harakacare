"""
API Views for Chat Interface
Provides endpoints for conversational agent integration
"""

import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View

from apps.triage.tools.conversational_intake_agent import ConversationalIntakeAgent

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class ChatStartView(View):
    """
    Start a new conversation with the conversational agent
    """
    
    def post(self, request):
        """Start new conversation"""
        try:
            data = json.loads(request.body)
            message = data.get('message', '')
            patient_token = data.get('patient_token')
            
            if not message:
                return JsonResponse({
                    'error': 'Message is required',
                    'status': 'error'
                }, status=400)
            
            # Initialize conversational agent
            agent = ConversationalIntakeAgent()
            
            # Start conversation
            response = agent.start_conversation(
                token=patient_token or f"PT-{message[:10].upper()}",
                message=message
            )
            
            return JsonResponse({
                'status': response.get('status', 'incomplete'),
                'completed': response.get('status') == 'complete',
                'message': response.get('message', ''),
                'action': response.get('action', ''),
                'active_menu_field': response.get('active_menu_field'),
                'extracted_so_far': response.get('extracted_so_far', {}),
                'missing_fields': response.get('missing_fields', []),
                'progress': response.get('progress', ''),
                'patient_token': response.get('patient_token'),
                'red_flags_detected': response.get('red_flags_detected', False),
                'intent': response.get('intent', 'routine')
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Invalid JSON',
                'status': 'error'
            }, status=400)
        except Exception as e:
            logger.error(f"Chat start error: {e}", exc_info=True)
            return JsonResponse({
                'error': 'Internal server error',
                'status': 'error'
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class ChatContinueView(View):
    """
    Continue an existing conversation
    """
    
    def post(self, request, patient_token):
        """Continue conversation"""
        try:
            data = json.loads(request.body)
            message = data.get('message', '')
            
            if not message:
                return JsonResponse({
                    'error': 'Message is required',
                    'status': 'error'
                }, status=400)
            
            # Initialize conversational agent
            agent = ConversationalIntakeAgent()
            
            # Continue conversation
            response = agent.continue_conversation(
                token=patient_token,
                message=message
            )
            
            return JsonResponse({
                'status': response.get('status', 'incomplete'),
                'completed': response.get('status') == 'complete',
                'message': response.get('message', ''),
                'action': response.get('action', ''),
                'active_menu_field': response.get('active_menu_field'),
                'extracted_so_far': response.get('extracted_so_far', {}),
                'missing_fields': response.get('missing_fields', []),
                'progress': response.get('progress', ''),
                'red_flags_detected': response.get('red_flags_detected', False),
                'intent': response.get('intent', 'routine')
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Invalid JSON',
                'status': 'error'
            }, status=400)
        except Exception as e:
            logger.error(f"Chat continue error: {e}", exc_info=True)
            return JsonResponse({
                'error': 'Internal server error',
                'status': 'error'
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class ChatStatusView(View):
    """
    Get conversation status
    """
    
    def get(self, request, patient_token):
        """Get conversation status"""
        try:
            # Initialize conversational agent
            agent = ConversationalIntakeAgent()
            
            # Get conversation state (this would need to be implemented in the agent)
            # For now, return a basic status
            return JsonResponse({
                'status': 'active',
                'patient_token': patient_token,
                'message': 'Conversation is active'
            })
            
        except Exception as e:
            logger.error(f"Chat status error: {e}", exc_info=True)
            return JsonResponse({
                'error': 'Internal server error',
                'status': 'error'
            }, status=500)
