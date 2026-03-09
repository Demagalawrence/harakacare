"""
Facility Bridge Service
Handles communication between Triage Agent and Facility Agent
Routes patient cases to appropriate healthcare facilities
"""

import logging
from typing import Dict, Any, Optional
from django.conf import settings
from apps.facilities.services.facility_agent_orchestrator import FacilityAgentOrchestrator
from apps.triage.models import TriageSession

logger = logging.getLogger(__name__)


def dispatch(session: TriageSession, decision: Dict[str, Any], red_flag_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dispatch triage case to facility agent for matching and assignment
    
    Args:
        session: TriageSession object with patient data
        decision: Final triage decision with risk level and recommendations
        red_flag_result: Red flag detection results
        
    Returns:
        Dictionary with facility assignment results
    """
    try:
        # Build triage data for facility agent
        triage_data = _build_triage_data(session, decision, red_flag_result)
        
        # Process through facility agent
        orchestrator = FacilityAgentOrchestrator()
        result = orchestrator.process_triage_case(triage_data)
        
        # Send patient confirmation if facility was assigned
        if result.get('success') and result.get('recommendation'):
            _send_patient_confirmation(session, result)
        
        return {
            'success': result.get('success', False),
            'assigned_facility': result.get('recommendation', {}).get('recommended_facility'),
            'booking_type': result.get('recommendation', {}).get('booking_type'),
            'facility_match_score': result.get('recommendation', {}).get('match_score'),
            'distance_km': result.get('recommendation', {}).get('distance_km'),
            'patient_message': result.get('patient_message'),
            'routing_id': result.get('routing_id'),
            'error': result.get('error')
        }
        
    except Exception as e:
        logger.error(f"Facility bridge dispatch failed for {session.patient_token}: {e}")
        return {
            'success': False,
            'error': f'Facility dispatch error: {str(e)}',
            'assigned_facility': None,
            'booking_type': None
        }


def _build_triage_data(session: TriageSession, decision: Dict[str, Any], red_flag_result: Dict[str, Any]) -> Dict[str, Any]:
    """Build triage data structure for facility agent"""
    return {
        'patient_token': session.patient_token,
        'triage_session_id': str(session.id),
        'risk_level': decision.get('risk_level', 'low'),
        'primary_symptom': session.primary_symptom or session.complaint_group or 'general',
        'secondary_symptoms': session.secondary_symptoms,
        'has_red_flags': bool(red_flag_result.get('detected_flags', [])) if red_flag_result else False,
        'chronic_conditions': session.chronic_conditions,
        'patient_district': session.district,
        'patient_location_lat': session.device_location_lat,
        'patient_location_lng': session.device_location_lng,
        'complaint_text': session.complaint_text,
        'age_group': session.age_group,
        'sex': session.sex,
        'is_emergency': decision.get('risk_level') == 'high' or bool(red_flag_result.get('detected_flags', [])),
        'patient_phone_number': getattr(session, 'patient_phone_number', None),
        'source_channel': getattr(session, 'channel', 'web')
    }


def _send_patient_confirmation(session: TriageSession, result: Dict[str, Any]) -> None:
    """Send confirmation message to patient"""
    try:
        recommendation = result.get('recommendation', {})
        facility = recommendation.get('recommended_facility')
        booking_type = recommendation.get('booking_type')
        
        if not facility:
            logger.warning(f"No facility assigned for {session.patient_token}")
            return
        
        # Build confirmation message
        message = _build_patient_message(session, facility, booking_type)
        
        # Send via appropriate channel
        phone = getattr(session, 'patient_phone_number', None)
        channel = getattr(session, 'channel', 'sms')
        
        if phone:
            if channel == 'whatsapp':
                _send_whatsapp(phone, message)
            else:
                _send_sms(phone, message)
            
            logger.info(f"Patient confirmation sent to {phone} via {channel}")
        else:
            logger.warning(f"No phone number available for {session.patient_token}")
            
    except Exception as e:
        logger.error(f"Failed to send patient confirmation: {e}")


def _build_patient_message(session: TriageSession, facility: Any, booking_type: str) -> str:
    """Build patient-friendly confirmation message"""
    facility_name = getattr(facility, 'name', 'Healthcare Facility')
    
    if booking_type == 'automatic':
        return f"""BOOKING CONFIRMED 🏥

Facility: {facility_name}
Patient Token: {session.patient_token[:8]}...
Risk Level: {session.risk_level}
Status: Your bed has been automatically reserved

Please arrive at the facility within 2 hours.
Bring this token and any identification documents.

For emergencies, call: {getattr(facility, 'phone_number', 'Emergency line')}
"""
    else:
        return f"""REFERRAL NOTIFICATION 🏥

Facility: {facility_name}
Patient Token: {session.patient_token[:8]}...
Risk Level: {session.risk_level}
Status: Please call ahead to schedule your visit

Contact: {getattr(facility, 'phone_number', 'Facility phone')}
Address: {getattr(facility, 'address', 'Facility address')}

Please mention this patient token when you call.
"""


def _send_whatsapp(phone: str, message: str) -> None:
    """Send WhatsApp message"""
    try:
        from apps.messaging.whatsapp.whatsapp_client import DialogClient
        client = DialogClient()
        client.send_message(phone, message)
    except Exception as e:
        logger.error(f"WhatsApp send failed to {phone}: {e}")


def _send_sms(phone: str, message: str) -> None:
    """Send SMS message"""
    try:
        # Implement SMS service integration here
        # For now, just log the message
        logger.info(f"SMS would be sent to {phone}: {message[:100]}...")
    except Exception as e:
        logger.error(f"SMS send failed to {phone}: {e}")


def update_triage_with_facility_response(routing_id: str, facility_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update triage session with facility response
    
    Args:
        routing_id: Facility routing ID
        facility_response: Response from facility
        
    Returns:
        Updated routing information
    """
    try:
        from apps.facilities.models import FacilityRouting
        routing = FacilityRouting.objects.get(id=routing_id)
        
        # Update routing with facility response
        routing.facility_response = facility_response.get('response', '')
        routing.response_received_at = timezone.now()
        
        if facility_response.get('acknowledged'):
            routing.routing_status = 'confirmed'
            routing.facility_confirmed_at = timezone.now()
        else:
            routing.routing_status = 'rejected'
        
        routing.save()
        
        return {
            'success': True,
            'routing_status': routing.routing_status,
            'facility_confirmed_at': routing.facility_confirmed_at
        }
        
    except Exception as e:
        logger.error(f"Failed to update routing {routing_id}: {e}")
        return {
            'success': False,
            'error': str(e)
        }
