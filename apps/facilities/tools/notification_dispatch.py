"""
Notification/Dispatch Tool
Sends anonymized case details to facility endpoints and tracks acknowledgments
Based on: HarakaCare Facility Agent Data Requirements - Tool 4.4
"""

import json
import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..models import (
    Facility, FacilityRouting, FacilityNotification, FacilityCandidate
)

logger = logging.getLogger(__name__)


class NotificationDispatchTool:
    """
    Tool for dispatching notifications to healthcare facilities
    Handles multiple notification methods and tracks delivery status
    """

    def __init__(self):
        self.session = self._create_http_session()
        self.max_retries = 3
        self.timeout_seconds = 30

    def _create_http_session(self) -> requests.Session:
        """Create HTTP session with retry strategy"""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session

    def send_case_notification(self, routing: FacilityRouting, facility: Facility, notification_type: str = 'new_case') -> FacilityNotification:
        """
        Send case notification to facility
        
        Args:
            routing: FacilityRouting with case details
            facility: Target facility
            notification_type: Type of notification
            
        Returns:
            FacilityNotification record
        """
        # Create notification record
        notification = FacilityNotification.objects.create(
            routing=routing,
            facility=facility,
            notification_type=notification_type,
            notification_status=FacilityNotification.NotificationStatus.PENDING,
            subject=self._generate_subject(routing, notification_type),
            message=self._generate_message(routing, facility, notification_type),
            payload=self._build_payload(routing, facility)
        )
        
        # Send notification
        try:
            success = self._dispatch_notification(notification)
            if success:
                notification.notification_status = FacilityNotification.NotificationStatus.SENT
                notification.sent_at = timezone.now()
                notification.save()
                logger.info(f"Notification sent to {facility.name} for case {routing.patient_token[:8]}")
            else:
                notification.notification_status = FacilityNotification.NotificationStatus.FAILED
                notification.error_message = "Failed to send notification"
                notification.save()
                logger.error(f"Failed to send notification to {facility.name}")
                
        except Exception as e:
            notification.notification_status = FacilityNotification.NotificationStatus.FAILED
            notification.error_message = str(e)
            notification.save()
            logger.error(f"Error sending notification to {facility.name}: {str(e)}")
        
        return notification

    def _dispatch_notification(self, notification: FacilityNotification) -> bool:
        """
        Dispatch notification using appropriate method
        
        Args:
            notification: FacilityNotification to send
            
        Returns:
            True if successful, False otherwise
        """
        facility = notification.facility
        
        # Try API endpoint first
        if facility.notification_endpoint:
            if self._send_via_api(notification):
                return True
        
        # Fallback to other methods
        if facility.phone_number:
            if self._send_via_sms(notification):
                return True
        
        # Email fallback (if implemented)
        # if facility.email:
        #     return self._send_via_email(notification)
        
        return False

    def _send_via_api(self, notification: FacilityNotification) -> bool:
        """
        Send notification via facility API endpoint
        
        Args:
            notification: FacilityNotification to send
            
        Returns:
            True if successful, False otherwise
        """
        try:
            facility = notification.facility
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'HarakaCare-FacilityAgent/1.0',
                'X-Notification-ID': str(notification.id),
            }
            
            # Add authentication if configured
            if hasattr(settings, 'FACILITY_API_KEY'):
                headers['Authorization'] = f"Bearer {settings.FACILITY_API_KEY}"
            
            response = self.session.post(
                facility.notification_endpoint,
                json=notification.payload,
                headers=headers,
                timeout=self.timeout_seconds
            )
            
            if response.status_code in [200, 201, 202]:
                # Store facility response
                try:
                    response_data = response.json()
                    notification.facility_response = response_data
                    notification.response_received_at = timezone.now()
                    
                    # Check if acknowledgment was received
                    if response_data.get('acknowledged', False):
                        notification.notification_status = FacilityNotification.NotificationStatus.ACKNOWLEDGED
                        notification.acknowledged_at = timezone.now()
                    
                except json.JSONDecodeError:
                    notification.facility_response = {'raw_response': response.text}
                
                return True
            else:
                notification.error_message = f"HTTP {response.status_code}: {response.text}"
                return False
                
        except requests.exceptions.Timeout:
            notification.error_message = "Request timeout"
            return False
        except requests.exceptions.ConnectionError:
            notification.error_message = "Connection error"
            return False
        except Exception as e:
            notification.error_message = f"Unexpected error: {str(e)}"
            return False

    def _send_via_sms(self, notification: FacilityNotification) -> bool:
        """
        Send notification via SMS (placeholder implementation)
        
        Args:
            notification: FacilityNotification to send
            
        Returns:
            True if successful, False otherwise
        """
        # This would integrate with SMS service like Twilio, Africa's Talking, etc.
        # For now, return False to indicate not implemented
        notification.error_message = "SMS notification not implemented"
        return False

    def _generate_subject(self, routing: FacilityRouting, notification_type: str) -> str:
        """Generate notification subject"""
        urgency_prefix = "URGENT" if routing.is_emergency else "NOTICE"
        
        subjects = {
            'new_case': f"{urgency_prefix}: New Patient Case - {routing.patient_token[:8]}",
            'confirmation': f"CONFIRMED: Patient Case - {routing.patient_token[:8]}",
            'cancellation': f"CANCELLED: Patient Case - {routing.patient_token[:8]}",
            'update': f"UPDATE: Patient Case - {routing.patient_token[:8]}",
            'reminder': f"REMINDER: Patient Case - {routing.patient_token[:8]}",
        }
        
        return subjects.get(notification_type, f"Patient Case Notification - {routing.patient_token[:8]}")

    def _generate_message(self, routing: FacilityRouting, facility: Facility, notification_type: str) -> str:
        """Generate human-readable notification message"""
        urgency = "EMERGENCY" if routing.is_emergency else "Routine"
        
        base_info = f"""
Patient Token: {routing.patient_token}
Risk Level: {routing.get_risk_level_display()}
Primary Symptom: {routing.primary_symptom}
Location: {routing.patient_district}
Urgency: {urgency}
"""

        if routing.secondary_symptoms:
            base_info += f"Secondary Symptoms: {', '.join(routing.secondary_symptoms)}\n"

        if routing.has_red_flags:
            base_info += "⚠️ RED FLAGS DETECTED\n"

        messages = {
            'new_case': f"""New patient case assigned to your facility.

{base_info}
Please review and confirm your capacity to handle this case.
Expected response time: 30 minutes for emergencies, 2 hours for routine cases.

Case ID: {routing.id}
Received: {routing.triage_received_at.strftime('%Y-%m-%d %H:%M:%S')}
""",
            'confirmation': f"""Patient case has been confirmed.

{base_info}
Please prepare for patient arrival and update your capacity accordingly.

Case ID: {routing.id}
Confirmed: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}
""",
            'cancellation': f"""Patient case has been cancelled.

{base_info}
No further action required.

Case ID: {routing.id}
Cancelled: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}
""",
        }
        
        return messages.get(notification_type, base_info)

    def _build_payload(self, routing: FacilityRouting, facility: Facility) -> Dict:
        """
        Build JSON payload for facility API
        
        Args:
            routing: FacilityRouting with case details
            facility: Target facility
            
        Returns:
            JSON payload dictionary
        """
        payload = {
            'notification_id': f"notif_{routing.id}_{facility.id}",
            'timestamp': timezone.now().isoformat(),
            'case': {
                'patient_token': routing.patient_token,
                'triage_session_id': routing.triage_session_id,
                'risk_level': routing.risk_level,
                'primary_symptom': routing.primary_symptom,
                'secondary_symptoms': routing.secondary_symptoms,
                'has_red_flags': routing.has_red_flags,
                'chronic_conditions': routing.chronic_conditions,
                'urgency': 'emergency' if routing.is_emergency else 'routine',
            },
            'location': {
                'district': routing.patient_district,
                'latitude': routing.patient_location_lat,
                'longitude': routing.patient_location_lng,
                'distance_to_facility_km': routing.distance_km,
            },
            'facility': {
                'id': facility.id,
                'name': facility.name,
                'address': facility.address,
            },
            'routing': {
                'id': routing.id,
                'booking_type': routing.booking_type,
                'requires_confirmation': routing.requires_manual_confirmation,
                'priority_score': routing.get_priority_score(),
            },
            'response_required': {
                'acknowledge': True,
                'confirm_capacity': routing.requires_manual_confirmation,
                'expected_response_time': '30 minutes' if routing.is_emergency else '2 hours',
                'response_deadline': (timezone.now() + timedelta(minutes=30 if routing.is_emergency else 120)).isoformat(),
            }
        }
        
        return payload

    def send_batch_notifications(self, routing: FacilityRouting, candidates: List[FacilityCandidate]) -> List[FacilityNotification]:
        """
        Send notifications to multiple facilities
        
        Args:
            routing: FacilityRouting with case details
            candidates: List of facility candidates
            
        Returns:
            List of FacilityNotification records
        """
        notifications = []
        
        for candidate in candidates:
            notification = self.send_case_notification(routing, candidate.facility)
            notifications.append(notification)
        
        return notifications

    def retry_failed_notifications(self, max_age_hours: int = 2) -> int:
        """
        Retry failed notifications that are within retry window
        
        Args:
            max_age_hours: Maximum age of notifications to retry
            
        Returns:
            Number of notifications retried
        """
        cutoff_time = timezone.now() - timedelta(hours=max_age_hours)
        
        failed_notifications = FacilityNotification.objects.filter(
            notification_status=FacilityNotification.NotificationStatus.FAILED,
            retry_count__lt=self.max_retries,
            created_at__gte=cutoff_time
        )
        
        retried_count = 0
        for notification in failed_notifications:
            notification.retry_count += 1
            notification.notification_status = FacilityNotification.NotificationStatus.RETRYING
            notification.save()
            
            try:
                success = self._dispatch_notification(notification)
                if success:
                    notification.notification_status = FacilityNotification.NotificationStatus.SENT
                    notification.sent_at = timezone.now()
                    retried_count += 1
                else:
                    notification.notification_status = FacilityNotification.NotificationStatus.FAILED
                    
            except Exception as e:
                notification.notification_status = FacilityNotification.NotificationStatus.FAILED
                notification.error_message = f"Retry {notification.retry_count}: {str(e)}"
            
            notification.save()
        
        return retried_count

    def check_pending_acknowledgments(self, timeout_minutes: int = 30) -> List[FacilityNotification]:
        """
        Check for notifications that haven't been acknowledged within timeout
        
        Args:
            timeout_minutes: Timeout in minutes for acknowledgments
            
        Returns:
            List of overdue notifications
        """
        cutoff_time = timezone.now() - timedelta(minutes=timeout_minutes)
        
        overdue = FacilityNotification.objects.filter(
            notification_status=FacilityNotification.NotificationStatus.SENT,
            sent_at__lt=cutoff_time
        ).select_related('facility', 'routing')
        
        return overdue

    def send_follow_up_reminder(self, notification: FacilityNotification) -> FacilityNotification:
        """
        Send follow-up reminder for unacknowledged notification
        
        Args:
            notification: Original notification to remind
            
        Returns:
            New reminder notification
        """
        reminder = FacilityNotification.objects.create(
            routing=notification.routing,
            facility=notification.facility,
            notification_type=FacilityNotification.NotificationType.REMINDER,
            notification_status=FacilityNotification.NotificationStatus.PENDING,
            subject=f"REMINDER: {notification.subject}",
            message=f"""This is a follow-up reminder for the following notification:

{notification.message}

Original notification sent: {notification.sent_at.strftime('%Y-%m-%d %H:%M:%S')}
Please acknowledge receipt and confirm your capacity.

Case ID: {notification.routing.id}
""",
            payload={
                'type': 'reminder',
                'original_notification_id': notification.id,
                'original_sent_at': notification.sent_at.isoformat() if notification.sent_at else None,
            }
        )
        
        # Send reminder
        try:
            success = self._dispatch_notification(reminder)
            if success:
                reminder.notification_status = FacilityNotification.NotificationStatus.SENT
                reminder.sent_at = timezone.now()
            else:
                reminder.notification_status = FacilityNotification.NotificationStatus.FAILED
        except Exception as e:
            reminder.notification_status = FacilityNotification.NotificationStatus.FAILED
            reminder.error_message = str(e)
        
        reminder.save()
        return reminder

    def get_notification_statistics(self, facility: Optional[Facility] = None, days: int = 7) -> Dict:
        """
        Get notification statistics for monitoring
        
        Args:
            facility: Specific facility (None for all)
            days: Number of days to look back
            
        Returns:
            Statistics dictionary
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        
        queryset = FacilityNotification.objects.filter(created_at__gte=cutoff_date)
        if facility:
            queryset = queryset.filter(facility=facility)
        
        stats = {
            'total_notifications': queryset.count(),
            'sent': queryset.filter(notification_status='sent').count(),
            'acknowledged': queryset.filter(notification_status='acknowledged').count(),
            'failed': queryset.filter(notification_status='failed').count(),
            'pending': queryset.filter(notification_status='pending').count(),
            'average_response_time_minutes': self._calculate_average_response_time(queryset),
            'notification_types': self._get_type_breakdown(queryset),
        }
        
        return stats

    def _calculate_average_response_time(self, queryset) -> Optional[float]:
        """Calculate average response time in minutes"""
        responded = queryset.filter(
            response_received_at__isnull=False,
            sent_at__isnull=False
        )
        
        if not responded.exists():
            return None
        
        total_minutes = 0
        count = 0
        
        for notification in responded:
            response_time = notification.response_received_at - notification.sent_at
            total_minutes += response_time.total_seconds() / 60
            count += 1
        
        return total_minutes / count if count > 0 else None

    def _get_type_breakdown(self, queryset) -> Dict:
        """Get breakdown by notification type"""
        breakdown = {}
        for choice in FacilityNotification.NotificationType.choices:
            type_name = choice[0]
            count = queryset.filter(notification_type=type_name).count()
            breakdown[type_name] = count
        return breakdown
