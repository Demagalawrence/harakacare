"""
Facility Agent Orchestrator
Main orchestrator that coordinates all Facility Agent tools and workflows
Based on: HarakaCare Facility Agent Data Requirements
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction

from ..models import (
    Facility, FacilityRouting, FacilityCandidate, FacilityNotification, FacilityCapacityLog
)
from ..tools.facility_matching import FacilityMatchingTool
from ..tools.prioritization import PrioritizationTool
from ..tools.notification_dispatch import NotificationDispatchTool
from ..tools.logging_monitoring import LoggingMonitoringTool

logger = logging.getLogger(__name__)


class FacilityAgentOrchestrator:
    """
    Main orchestrator for the HarakaCare Facility Agent
    Coordinates routing, matching, prioritization, notification, and logging
    """

    def __init__(self):
        self.matching_tool = FacilityMatchingTool()
        self.prioritization_tool = PrioritizationTool()
        self.notification_tool = NotificationDispatchTool()
        self.logging_tool = LoggingMonitoringTool()

    def process_triage_case(self, triage_data: Dict) -> Dict:
        """
        Process new triage case from Triage Agent
        Complete workflow: intake -> matching -> prioritization -> notification
        
        Args:
            triage_data: Case data from Triage Agent
            
        Returns:
            Processing result with routing information
        """
        try:
            with transaction.atomic():
                # Step 1: Create routing record
                routing = self._create_routing_record(triage_data)
                
                # Step 2: Find matching facilities
                candidates = self.matching_tool.find_candidate_facilities(routing)
                
                if not candidates:
                    self._handle_no_facilities(routing)
                    return {
                        'success': False,
                        'message': 'No suitable facilities found',
                        'routing_id': routing.id,
                    }
                
                # Step 3: Prioritize candidates
                prioritized_candidates = self.prioritization_tool.prioritize_candidates(candidates, routing)
                
                # Step 4: Save candidates
                for candidate in prioritized_candidates:
                    candidate.save()
                
                # Step 5: Determine booking type and get recommendation
                booking_type = self.prioritization_tool.determine_booking_type(routing)
                routing.booking_type = booking_type
                routing.save()
                
                recommendation = self.prioritization_tool.get_booking_recommendation(
                    routing, prioritized_candidates
                )
                
                # Step 6: Log routing decision
                self.logging_tool.log_routing_decision(
                    routing, prioritized_candidates,
                    recommendation.get('recommended_facility'),
                    recommendation.get('reason', '')
                )
                
                # Step 7: Handle automatic booking
                notifications_sent = []
                if booking_type == 'automatic' and recommendation.get('recommended_facility'):
                    notification = self._handle_automatic_booking(
                        routing, recommendation['recommended_facility']
                    )
                    notifications_sent.append(notification)
                
                # Step 8: Notify Follow-up Agent
                self._notify_followup_agent(routing, recommendation)
                
                return {
                    'success': True,
                    'routing_id': routing.id,
                    'patient_token': routing.patient_token,
                    'booking_type': booking_type,
                    'candidates_found': len(prioritized_candidates),
                    'recommendation': recommendation,
                    'notifications_sent': len(notifications_sent),
                }
                
        except Exception as e:
            logger.error(f"Error processing triage case: {str(e)}")
            self.logging_tool.log_system_event(
                'triage_processing_error',
                {'error': str(e), 'triage_data': triage_data},
                'error'
            )
            return {
                'success': False,
                'message': f'Processing error: {str(e)}',
            }

    def handle_facility_response(self, routing_id: int, facility_id: int, 
                              response_data: Dict) -> Dict:
        """
        Handle facility response to notification
        
        Args:
            routing_id: Routing record ID
            facility_id: Facility ID
            response_data: Response from facility
            
        Returns:
            Response processing result
        """
        try:
            with transaction.atomic():
                # Get routing and notification
                routing = FacilityRouting.objects.get(id=routing_id)
                notification = FacilityNotification.objects.get(
                    routing=routing,
                    facility_id=facility_id,
                    notification_type='new_case'
                )
                
                # Update notification with response
                notification.facility_response = response_data
                notification.response_received_at = timezone.now()
                
                response_type = response_data.get('response_type')
                
                if response_type == 'confirm':
                    self._handle_facility_confirmation(routing, notification, response_data)
                elif response_type == 'reject':
                    self._handle_facility_rejection(routing, notification, response_data)
                else:
                    raise ValueError(f"Invalid response type: {response_type}")
                
                notification.save()
                
                # Log facility response
                self.logging_tool.log_facility_response(notification, response_data)
                
                return {
                    'success': True,
                    'routing_status': routing.routing_status,
                    'message': f'Facility response processed: {response_type}',
                }
                
        except Exception as e:
            logger.error(f"Error handling facility response: {str(e)}")
            return {
                'success': False,
                'message': f'Response processing error: {str(e)}',
            }

    def update_facility_capacity(self, facility_id: int, capacity_data: Dict) -> Dict:
        """
        Update facility capacity and log changes
        
        Args:
            facility_id: Facility ID
            capacity_data: Capacity update data
            
        Returns:
            Update result
        """
        try:
            with transaction.atomic():
                facility = Facility.objects.get(id=facility_id)
                
                # Record old capacity
                old_capacity = {
                    'available_beds': facility.available_beds,
                    'staff_count': facility.staff_count,
                    'average_wait_time_minutes': facility.average_wait_time_minutes,
                }
                
                # Update facility
                if 'available_beds' in capacity_data:
                    facility.available_beds = capacity_data['available_beds']
                if 'staff_count' in capacity_data:
                    facility.staff_count = capacity_data['staff_count']
                if 'average_wait_time_minutes' in capacity_data:
                    facility.average_wait_time_minutes = capacity_data['average_wait_time_minutes']
                
                facility.save()
                
                # Calculate change
                beds_change = 0
                if 'available_beds' in capacity_data:
                    beds_change = capacity_data['available_beds'] - old_capacity['available_beds']
                
                # Log capacity change
                self.logging_tool.log_capacity_change(facility, {
                    'beds_change': beds_change,
                    'reason': capacity_data.get('reason', 'manual_update'),
                    'source': capacity_data.get('source', 'api'),
                    'notes': capacity_data.get('notes', ''),
                })
                
                return {
                    'success': True,
                    'facility': facility.name,
                    'old_capacity': old_capacity,
                    'new_capacity': {
                        'available_beds': facility.available_beds,
                        'staff_count': facility.staff_count,
                        'average_wait_time_minutes': facility.average_wait_time_minutes,
                    }
                }
                
        except Exception as e:
            logger.error(f"Error updating facility capacity: {str(e)}")
            return {
                'success': False,
                'message': f'Capacity update error: {str(e)}',
            }

    def get_routing_status(self, patient_token: str) -> Dict:
        """
        Get current status of patient routing
        
        Args:
            patient_token: Patient token
            
        Returns:
            Current routing status
        """
        try:
            routing = FacilityRouting.objects.filter(
                patient_token=patient_token
            ).select_related('assigned_facility').prefetch_related(
                'candidates__facility', 'notifications__facility'
            ).first()
            
            if not routing:
                return {
                    'found': False,
                    'message': 'No routing found for patient token',
                }
            
            # Get latest notification status
            latest_notification = routing.notifications.order_by('-created_at').first()
            
            return {
                'found': True,
                'routing': {
                    'id': routing.id,
                    'patient_token': routing.patient_token,
                    'risk_level': routing.risk_level,
                    'routing_status': routing.routing_status,
                    'booking_type': routing.booking_type,
                    'assigned_facility': routing.assigned_facility.name if routing.assigned_facility else None,
                    'triage_received_at': routing.triage_received_at,
                    'facility_notified_at': routing.facility_notified_at,
                    'facility_confirmed_at': routing.facility_confirmed_at,
                },
                'latest_notification': {
                    'id': latest_notification.id if latest_notification else None,
                    'facility': latest_notification.facility.name if latest_notification else None,
                    'status': latest_notification.notification_status if latest_notification else None,
                    'sent_at': latest_notification.sent_at if latest_notification else None,
                    'response_received_at': latest_notification.response_received_at if latest_notification else None,
                },
                'candidates_count': routing.candidates.count(),
            }
            
        except Exception as e:
            logger.error(f"Error getting routing status: {str(e)}")
            return {
                'found': False,
                'message': f'Error retrieving status: {str(e)}',
            }

    def _create_routing_record(self, triage_data: Dict) -> FacilityRouting:
        """Create routing record from triage data"""
        return FacilityRouting.objects.create(
            patient_token=triage_data['patient_token'],
            triage_session_id=triage_data.get('triage_session_id', ''),
            risk_level=triage_data['risk_level'],
            primary_symptom=triage_data['primary_symptom'],
            secondary_symptoms=triage_data.get('secondary_symptoms', []),
            has_red_flags=triage_data.get('has_red_flags', False),
            chronic_conditions=triage_data.get('chronic_conditions', []),
            patient_district=triage_data['patient_district'],
            patient_location_lat=triage_data.get('patient_location_lat'),
            patient_location_lng=triage_data.get('patient_location_lng'),
        )

    def _handle_automatic_booking(self, routing: FacilityRouting, facility: Facility) -> FacilityNotification:
        """Handle automatic booking for high-risk cases"""
        # Send notification
        notification = self.notification_tool.send_case_notification(routing, facility)
        
        # Update routing
        routing.assigned_facility = facility
        routing.routing_status = FacilityRouting.RoutingStatus.NOTIFIED
        routing.facility_notified_at = timezone.now()
        routing.save()
        
        # Update facility capacity (reserve bed)
        if facility.available_beds and facility.available_beds > 0:
            facility.update_capacity(-1)
        
        return notification

    def _handle_facility_confirmation(self, routing: FacilityRouting, 
                                   notification: FacilityNotification, response_data: Dict):
        """Handle facility confirmation"""
        notification.notification_status = FacilityNotification.NotificationStatus.ACKNOWLEDGED
        notification.acknowledged_at = timezone.now()
        
        routing.routing_status = FacilityRouting.RoutingStatus.CONFIRMED
        routing.facility_confirmed_at = timezone.now()
        routing.save()
        
        # Update capacity if beds were reserved
        beds_reserved = response_data.get('beds_reserved', 0)
        if beds_reserved > 0:
            facility = notification.facility
            facility.update_capacity(-beds_reserved)

    def _handle_facility_rejection(self, routing: FacilityRouting, 
                                 notification: FacilityNotification, response_data: Dict):
        """Handle facility rejection and try alternatives"""
        notification.notification_status = FacilityNotification.NotificationStatus.FAILED
        notification.error_message = f"Facility rejected: {response_data.get('response_message', 'No reason provided')}"
        
        # Try alternative facility
        alternative_candidate = self._find_alternative_facility(routing)
        if alternative_candidate:
            routing.assigned_facility = alternative_candidate.facility
            routing.routing_status = FacilityRouting.RoutingStatus.PENDING
            routing.save()
            
            # Send notification to alternative
            self.notification_tool.send_case_notification(
                routing, alternative_candidate.facility
            )
        else:
            routing.routing_status = FacilityRouting.RoutingStatus.REJECTED
            routing.save()

    def _find_alternative_facility(self, routing: FacilityRouting) -> Optional[FacilityCandidate]:
        """Find alternative facility candidate"""
        candidates = FacilityCandidate.objects.filter(
            routing=routing
        ).exclude(
            facility_id=routing.assigned_facility.id if routing.assigned_facility else None
        ).filter(
            has_capacity=True,
            offers_required_service=True
        ).order_by('-match_score')
        
        return candidates.first()

    def _handle_no_facilities(self, routing: FacilityRouting):
        """Handle case when no suitable facilities are found"""
        routing.routing_status = FacilityRouting.RoutingStatus.CANCELLED
        routing.save()
        
        self.logging_tool.log_system_event(
            'no_facilities_found',
            {
                'routing_id': routing.id,
                'patient_token': routing.patient_token,
                'risk_level': routing.risk_level,
                'district': routing.patient_district,
            },
            'warning'
        )

    def _notify_followup_agent(self, routing: FacilityRouting, recommendation: Dict):
        """Notify Follow-up Agent about routing outcome"""
        # This would integrate with the Follow-up Agent API
        # For now, log the notification
        followup_data = {
            'patient_token': routing.patient_token,
            'routing_id': routing.id,
            'booking_type': routing.booking_type,
            'assigned_facility': recommendation.get('recommended_facility'),
            'requires_followup': True,
            'followup_priority': 'high' if routing.is_emergency else 'medium',
            'timestamp': timezone.now().isoformat(),
        }
        
        self.logging_tool.log_system_event(
            'followup_notification',
            followup_data,
            'info'
        )

    def run_maintenance_tasks(self) -> Dict:
        """
        Run routine maintenance tasks
        Retry failed notifications, check for overdue responses, etc.
        """
        results = {
            'timestamp': timezone.now().isoformat(),
            'tasks_completed': [],
        }
        
        try:
            # Retry failed notifications
            retried_count = self.notification_tool.retry_failed_notifications()
            results['tasks_completed'].append({
                'task': 'retry_failed_notifications',
                'result': f'Retried {retried_count} notifications',
            })
            
            # Check for overdue acknowledgments
            overdue_notifications = self.notification_tool.check_pending_acknowledgments()
            if overdue_notifications:
                for notification in overdue_notifications:
                    self.notification_tool.send_follow_up_reminder(notification)
                
                results['tasks_completed'].append({
                    'task': 'check_overdue_acknowledgments',
                    'result': f'Sent {len(overdue_notifications)} follow-up reminders',
                })
            
            # Log performance metrics
            metrics = self._collect_performance_metrics()
            self.logging_tool.log_performance_metrics(metrics)
            results['tasks_completed'].append({
                'task': 'performance_metrics',
                'result': 'Performance metrics logged',
            })
            
        except Exception as e:
            logger.error(f"Error in maintenance tasks: {str(e)}")
            results['error'] = str(e)
        
        return results

    def _collect_performance_metrics(self) -> Dict:
        """Collect performance metrics for monitoring"""
        last_24h = timezone.now() - timedelta(hours=24)
        
        # Routing metrics
        total_routings = FacilityRouting.objects.filter(
            triage_received_at__gte=last_24h
        ).count()
        
        emergency_routings = FacilityRouting.objects.filter(
            triage_received_at__gte=last_24h,
            risk_level='high'
        ).count()
        
        # Notification metrics
        notification_stats = self.notification_tool.get_notification_statistics(days=1)
        
        # Response time metrics
        avg_response_time = self.notification_tool._calculate_average_response_time(
            FacilityNotification.objects.filter(
                created_at__gte=last_24h,
                response_received_at__isnull=False
            )
        )
        
        return {
            'period_hours': 24,
            'total_routings': total_routings,
            'emergency_routings': emergency_routings,
            'emergency_rate': (emergency_routings / total_routings * 100) if total_routings > 0 else 0,
            'notifications_sent': notification_stats.get('sent', 0),
            'notifications_acknowledged': notification_stats.get('acknowledged', 0),
            'acknowledgment_rate': notification_stats.get('acknowledged', 0) / max(notification_stats.get('sent', 1), 1) * 100,
            'average_response_time_minutes': avg_response_time,
        }
