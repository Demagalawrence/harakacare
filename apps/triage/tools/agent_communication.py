"""
Tool 8: Agent Communication Tool
Handles communication with other agents in the system
"""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class AgentCommunicationTool:
    """
    Manages communication between Triage Agent and downstream agents
    - Follow-up Agent
    - Facility Matching Agent
    - Notification Agent
    """

    def forward_to_followup(
            self,
            session,
            decision: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Forward case to Follow-up Agent

        Args:
            session: TriageSession instance
            decision: Final triage decision

        Returns:
            Communication result
        """
        # Build payload for Follow-up Agent
        payload = {
            'patient_token': session.patient_token,
            'risk_level': decision['risk_level'],
            'follow_up_priority': decision['follow_up_priority'],
            'follow_up_timeframe': decision.get('follow_up_timeframe', '24 hours'),
            'symptom_summary': session.generate_symptom_summary(),
            'has_red_flags': session.has_red_flags,
            'district': session.district,
            'subcounty': session.subcounty,
            'consent_follow_up': session.consent_follow_up
        }

        # Log communication
        from apps.triage.models import AgentCommunicationLog

        comm_log = AgentCommunicationLog.objects.create(
            triage_session=session,
            target_agent='follow_up',
            payload=payload,
            communication_status='pending'
        )

        try:
            # TODO: Implement actual API call to Follow-up Agent
            # For now, just log
            logger.info(
                f"Would forward to Follow-up Agent: {session.patient_token} "
                f"- Priority: {decision['follow_up_priority']}"
            )

            # Update communication log
            comm_log.communication_status = 'sent'
            comm_log.save()

            return {
                'success': True,
                'agent': 'follow_up',
                'message': 'Case forwarded to Follow-up Agent',
                'payload': payload
            }

        except Exception as e:
            logger.error(f"Error forwarding to Follow-up Agent: {str(e)}")

            comm_log.communication_status = 'failed'
            comm_log.error_message = str(e)
            comm_log.save()

            return {
                'success': False,
                'agent': 'follow_up',
                'error': str(e)
            }

    def forward_to_facility_matching(
            self,
            session,
            decision: Dict[str, Any],
            red_flag_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Forward case to Facility Matching Agent

        Args:
            session: TriageSession instance
            decision: Final triage decision
            red_flag_result: Red flag detection results

        Returns:
            Communication result
        """
        # Build payload for Facility Matching Agent
        payload = {
            'patient_token': session.patient_token,
            'risk_level': decision['risk_level'],
            'facility_type_needed': decision['facility_type'],
            'urgency': decision['follow_up_priority'],
            'is_emergency': red_flag_result.get('emergency_override', False),
            'location': {
                'district': session.district,
                'subcounty': session.subcounty,
                'latitude': session.device_location_lat,
                'longitude': session.device_location_lng
            },
            'required_services': self._determine_required_services(session, decision),
            'symptom_summary': session.generate_symptom_summary(),
            'age_range': session.age_range,
            'pregnancy_status': session.pregnancy_status
        }

        # Log communication
        from apps.triage.models import AgentCommunicationLog

        comm_log = AgentCommunicationLog.objects.create(
            triage_session=session,
            target_agent='facility_matching',
            payload=payload,
            communication_status='pending'
        )

        try:
            # TODO: Implement actual API call to Facility Matching Agent
            # For now, just log
            logger.info(
                f"Would forward to Facility Matching Agent: {session.patient_token} "
                f"- Facility type: {decision['facility_type']}"
            )

            # Update communication log
            comm_log.communication_status = 'sent'
            comm_log.save()

            return {
                'success': True,
                'agent': 'facility_matching',
                'message': 'Case forwarded to Facility Matching Agent',
                'payload': payload
            }

        except Exception as e:
            logger.error(f"Error forwarding to Facility Matching Agent: {str(e)}")

            comm_log.communication_status = 'failed'
            comm_log.error_message = str(e)
            comm_log.save()

            return {
                'success': False,
                'agent': 'facility_matching',
                'error': str(e)
            }

    def _determine_required_services(
            self,
            session,
            decision: Dict[str, Any]
    ) -> list[str]:
        """
        Determine what services the patient will need

        Returns:
            List of required facility services
        """
        services = []

        # Emergency services
        if session.has_red_flags or decision['risk_level'] == 'high':
            services.append('emergency_services')

        # Pregnancy-related
        if session.pregnancy_status == 'yes':
            services.append('maternity_services')

        # Age-specific
        if session.age_range == 'under_5':
            services.append('pediatric_care')

        # Symptom-specific services
        primary = session.primary_symptom

        if primary in ['injury_trauma', 'severe_bleeding']:
            services.append('emergency_services')
            services.append('surgery')

        if primary in ['difficulty_breathing', 'chest_pain']:
            services.append('emergency_services')
            services.append('intensive_care')

        # Lab services for certain symptoms
        if primary in ['fever', 'abdominal_pain', 'vomiting', 'diarrhea']:
            services.append('laboratory')

        # Imaging for certain symptoms
        if primary in ['chest_pain', 'injury_trauma', 'headache']:
            services.append('xray')

        # Default to basic care if no specific services
        if not services:
            services.append('general_consultation')

        return list(set(services))  # Remove duplicates

    def send_notification(
            self,
            session,
            message: str,
            channel: str = 'sms'
    ) -> Dict[str, Any]:
        """
        Send notification to patient via Notification Agent

        Args:
            session: TriageSession instance
            message: Message to send
            channel: Communication channel (sms, whatsapp, etc.)

        Returns:
            Notification result
        """
        # Build payload
        payload = {
            'patient_token': session.patient_token,
            'message': message,
            'channel': channel,
            'priority': 'high' if session.has_red_flags else 'normal'
        }

        # Log communication
        from apps.triage.models import AgentCommunicationLog

        comm_log = AgentCommunicationLog.objects.create(
            triage_session=session,
            target_agent='notification',
            payload=payload,
            communication_status='pending'
        )

        try:
            # TODO: Implement actual API call to Notification Agent
            logger.info(
                f"Would send notification via {channel}: {session.patient_token}"
            )

            comm_log.communication_status = 'sent'
            comm_log.save()

            return {
                'success': True,
                'agent': 'notification',
                'channel': channel,
                'message': 'Notification sent'
            }

        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}")

            comm_log.communication_status = 'failed'
            comm_log.error_message = str(e)
            comm_log.save()

            return {
                'success': False,
                'agent': 'notification',
                'error': str(e)
            }