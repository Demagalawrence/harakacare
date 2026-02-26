from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
import logging

from apps.messaging.ussd.handlers import USSDHandler

logger = logging.getLogger(__name__)

# Initialize USSD handler
ussd_handler = USSDHandler()


@method_decorator(csrf_exempt, name='dispatch')
class USSDCallbackView(View):
    """
    Africa's Talking USSD callback endpoint
    """
    
    def post(self, request):
        """Handle USSD POST request"""
        try:
            # Get Africa's Talking parameters
            session_id = request.POST.get('sessionId')
            phone_number = request.POST.get('phoneNumber')
            text = request.POST.get('text', '')
            
            logger.info(f"USSD Request - Session: {session_id}, Phone: {phone_number}, Text: {text}")
            
            # Handle USSD request
            response = ussd_handler.handle(session_id, phone_number, text)
            
            # Format response for Africa's Talking
            if response['action'] == 'end':
                ussd_response = f"END {response['message']}"
            else:
                ussd_response = f"CON {response['message']}"
            
            logger.info(f"USSD Response: {ussd_response}")
            
            return HttpResponse(ussd_response, content_type='text/plain')
            
        except Exception as e:
            logger.error(f"USSD Error: {e}", exc_info=True)
            return HttpResponse("END System error. Please try again.", content_type='text/plain')
    
    def get(self, request):
        """Handle GET requests"""
        return HttpResponse("USSD endpoint is running. Use POST method.", content_type='text/plain')