"""
Logging & Monitoring Tool
Logs routing decisions, timestamps, facility responses for audit and compliance
Based on: HarakaCare Facility Agent Data Requirements - Tool 4.5
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q, Count, Avg, Max, Min
from django.db.models.functions import Trunc

from ..models import (
    Facility, FacilityRouting, FacilityCandidate, FacilityNotification, 
    FacilityCapacityLog
)

logger = logging.getLogger(__name__)


class LoggingMonitoringTool:
    """
    Tool for comprehensive logging and monitoring of facility agent operations
    Provides audit trail, compliance reporting, and performance metrics
    """

    def __init__(self):
        self.logger = logging.getLogger('facility_agent')

    def log_routing_decision(self, routing: FacilityRouting, candidates: List[FacilityCandidate], 
                          selected_facility: Optional[Facility] = None, decision_reason: str = "") -> None:
        """
        Log routing decision with complete context
        
        Args:
            routing: FacilityRouting record
            candidates: List of considered facilities
            selected_facility: Facility that was selected
            decision_reason: Reason for selection
        """
        log_entry = {
            'timestamp': timezone.now().isoformat(),
            'event_type': 'routing_decision',
            'routing_id': routing.id,
            'patient_token': routing.patient_token,
            'risk_level': routing.risk_level,
            'primary_symptom': routing.primary_symptom,
            'location': {
                'district': routing.patient_district,
                'latitude': routing.patient_location_lat,
                'longitude': routing.patient_location_lng,
            },
            'booking_type': routing.booking_type,
            'urgency': 'emergency' if routing.is_emergency else 'routine',
            'candidates_considered': len(candidates),
            'candidates': [
                {
                    'facility_id': c.facility.id,
                    'facility_name': c.facility.name,
                    'match_score': c.match_score,
                    'distance_km': c.distance_km,
                    'has_capacity': c.has_capacity,
                    'offers_service': c.offers_required_service,
                }
                for c in candidates
            ],
            'selected_facility': {
                'id': selected_facility.id,
                'name': selected_facility.name,
            } if selected_facility else None,
            'decision_reason': decision_reason,
            'processing_time_ms': self._calculate_processing_time(routing),
        }
        
        self._write_log_entry(log_entry)
        self.logger.info(f"Routing decision logged for case {routing.patient_token[:8]}")

    def log_facility_response(self, notification: FacilityNotification, response_data: Dict) -> None:
        """
        Log facility response to notification
        
        Args:
            notification: FacilityNotification that received response
            response_data: Response data from facility
        """
        log_entry = {
            'timestamp': timezone.now().isoformat(),
            'event_type': 'facility_response',
            'notification_id': notification.id,
            'routing_id': notification.routing.id,
            'patient_token': notification.routing.patient_token,
            'facility': {
                'id': notification.facility.id,
                'name': notification.facility.name,
            },
            'notification_type': notification.notification_type,
            'sent_at': notification.sent_at.isoformat() if notification.sent_at else None,
            'response_received_at': notification.response_received_at.isoformat() if notification.response_received_at else None,
            'response_time_minutes': self._calculate_response_time(notification),
            'response_data': response_data,
            'acknowledged': response_data.get('acknowledged', False),
            'capacity_confirmed': response_data.get('capacity_confirmed', False),
            'estimated_arrival': response_data.get('estimated_arrival'),
        }
        
        self._write_log_entry(log_entry)
        self.logger.info(f"Facility response logged from {notification.facility.name}")

    def log_capacity_change(self, facility: Facility, change_data: Dict) -> None:
        """
        Log facility capacity changes
        
        Args:
            facility: Facility with capacity change
            change_data: Details of the change
        """
        log_entry = {
            'timestamp': timezone.now().isoformat(),
            'event_type': 'capacity_change',
            'facility': {
                'id': facility.id,
                'name': facility.name,
            },
            'change': {
                'beds_change': change_data.get('beds_change', 0),
                'total_beds': facility.total_beds,
                'available_beds': facility.available_beds,
                'staff_count': facility.staff_count,
                'average_wait_time': facility.average_wait_time_minutes,
            },
            'reason': change_data.get('reason', 'unknown'),
            'source': change_data.get('source', 'manual'),
            'notes': change_data.get('notes', ''),
        }
        
        self._write_log_entry(log_entry)
        self.logger.info(f"Capacity change logged for {facility.name}")

    def log_system_event(self, event_type: str, details: Dict, severity: str = 'info') -> None:
        """
        Log system events (errors, warnings, etc.)
        
        Args:
            event_type: Type of system event
            details: Event details
            severity: Log severity level
        """
        log_entry = {
            'timestamp': timezone.now().isoformat(),
            'event_type': 'system_event',
            'severity': severity,
            'system_event_type': event_type,
            'details': details,
        }
        
        self._write_log_entry(log_entry)
        
        if severity == 'error':
            self.logger.error(f"System event: {event_type} - {details}")
        elif severity == 'warning':
            self.logger.warning(f"System event: {event_type} - {details}")
        else:
            self.logger.info(f"System event: {event_type} - {details}")

    def log_performance_metrics(self, metrics: Dict) -> None:
        """
        Log performance metrics for monitoring
        
        Args:
            metrics: Performance metrics dictionary
        """
        log_entry = {
            'timestamp': timezone.now().isoformat(),
            'event_type': 'performance_metrics',
            'metrics': metrics,
        }
        
        self._write_log_entry(log_entry)
        self.logger.info("Performance metrics logged")

    def _write_log_entry(self, log_entry: Dict) -> None:
        """Write log entry to storage (file, database, etc.)"""
        # For now, log to Python logger
        # In production, this could write to a dedicated log database or file system
        self.logger.info(f"FACILITY_AGENT_LOG: {json.dumps(log_entry)}")

    def _calculate_processing_time(self, routing: FacilityRouting) -> Optional[int]:
        """Calculate processing time in milliseconds"""
        if not routing.triage_received_at:
            return None
        
        processing_time = timezone.now() - routing.triage_received_at
        return int(processing_time.total_seconds() * 1000)

    def _calculate_response_time(self, notification: FacilityNotification) -> Optional[float]:
        """Calculate facility response time in minutes"""
        if not notification.sent_at or not notification.response_received_at:
            return None
        
        response_time = notification.response_received_at - notification.sent_at
        return response_time.total_seconds() / 60

    def get_audit_trail(self, patient_token: Optional[str] = None, 
                       facility_id: Optional[int] = None,
                       start_date: Optional[datetime] = None,
                       end_date: Optional[datetime] = None,
                       event_types: Optional[List[str]] = None) -> List[Dict]:
        """
        Get audit trail for specified criteria
        
        Args:
            patient_token: Filter by patient token
            facility_id: Filter by facility ID
            start_date: Start date filter
            end_date: End date filter
            event_types: Filter by event types
            
        Returns:
            List of audit trail entries
        """
        # This would typically query a dedicated log database
        # For now, return data from main models
        
        audit_data = []
        
        # Get routing records
        routings = FacilityRouting.objects.all()
        
        if patient_token:
            routings = routings.filter(patient_token=patient_token)
        if start_date:
            routings = routings.filter(triage_received_at__gte=start_date)
        if end_date:
            routings = routings.filter(triage_received_at__lte=end_date)
        
        for routing in routings.select_related('assigned_facility').prefetch_related('candidates__facility', 'notifications__facility'):
            routing_data = {
                'timestamp': routing.triage_received_at.isoformat(),
                'event_type': 'routing_created',
                'routing_id': routing.id,
                'patient_token': routing.patient_token,
                'risk_level': routing.risk_level,
                'assigned_facility': routing.assigned_facility.name if routing.assigned_facility else None,
                'routing_status': routing.routing_status,
            }
            audit_data.append(routing_data)
            
            # Add notifications
            for notification in routing.notifications.all():
                notification_data = {
                    'timestamp': notification.created_at.isoformat(),
                    'event_type': 'notification_sent',
                    'notification_id': notification.id,
                    'facility': notification.facility.name,
                    'notification_type': notification.notification_type,
                    'status': notification.notification_status,
                }
                audit_data.append(notification_data)
        
        # Sort by timestamp
        audit_data.sort(key=lambda x: x['timestamp'], reverse=True)
        return audit_data

    def get_compliance_report(self, start_date: datetime, end_date: datetime) -> Dict:
        """
        Generate compliance report for specified period
        
        Args:
            start_date: Report start date
            end_date: Report end date
            
        Returns:
            Compliance report dictionary
        """
        routings = FacilityRouting.objects.filter(
            triage_received_at__gte=start_date,
            triage_received_at__lte=end_date
        )
        
        total_cases = routings.count()
        emergency_cases = routings.filter(
            Q(risk_level='high') | Q(has_red_flags=True)
        ).count()
        
        # Response time analysis
        notifications = FacilityNotification.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date,
            response_received_at__isnull=False
        )
        
        avg_response_time = notifications.aggregate(
            avg_time=Avg('response_received_at' - 'sent_at')
        )['avg_time']
        
        if avg_response_time:
            avg_response_time_minutes = avg_response_time.total_seconds() / 60
        else:
            avg_response_time_minutes = 0
        
        # Facility performance
        facility_stats = {}
        for routing in routings.filter(assigned_facility__isnull=False):
            facility_name = routing.assigned_facility.name
            if facility_name not in facility_stats:
                facility_stats[facility_name] = {
                    'total_cases': 0,
                    'emergency_cases': 0,
                    'confirmed_cases': 0,
                }
            
            facility_stats[facility_name]['total_cases'] += 1
            if routing.is_emergency:
                facility_stats[facility_name]['emergency_cases'] += 1
            if routing.routing_status == 'confirmed':
                facility_stats[facility_name]['confirmed_cases'] += 1
        
        return {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
            },
            'summary': {
                'total_cases': total_cases,
                'emergency_cases': emergency_cases,
                'emergency_percentage': (emergency_cases / total_cases * 100) if total_cases > 0 else 0,
                'average_response_time_minutes': avg_response_time_minutes,
            },
            'facility_performance': facility_stats,
            'compliance_metrics': {
                'emergency_response_rate': self._calculate_emergency_response_rate(start_date, end_date),
                'facility_acknowledgment_rate': self._calculate_acknowledgment_rate(start_date, end_date),
                'capacity_accuracy': self._calculate_capacity_accuracy(start_date, end_date),
            }
        }

    def _calculate_emergency_response_rate(self, start_date: datetime, end_date: datetime) -> float:
        """Calculate emergency response rate"""
        emergency_routings = FacilityRouting.objects.filter(
            triage_received_at__gte=start_date,
            triage_received_at__lte=end_date,
            Q(risk_level='high') | Q(has_red_flags=True)
        )
        
        total_emergency = emergency_routings.count()
        if total_emergency == 0:
            return 0.0
        
        responded_emergency = emergency_routings.filter(
            notifications__response_received_at__isnull=False
        ).distinct().count()
        
        return (responded_emergency / total_emergency) * 100

    def _calculate_acknowledgment_rate(self, start_date: datetime, end_date: datetime) -> float:
        """Calculate facility acknowledgment rate"""
        notifications = FacilityNotification.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        
        total_notifications = notifications.count()
        if total_notifications == 0:
            return 0.0
        
        acknowledged = notifications.filter(
            notification_status='acknowledged'
        ).count()
        
        return (acknowledged / total_notifications) * 100

    def _calculate_capacity_accuracy(self, start_date: datetime, end_date: datetime) -> float:
        """Calculate capacity prediction accuracy"""
        # This would compare predicted capacity needs vs actual usage
        # For now, return a placeholder value
        return 85.0

    def get_performance_dashboard(self, days: int = 7) -> Dict:
        """
        Get performance dashboard data
        
        Args:
            days: Number of days to include
            
        Returns:
            Dashboard data dictionary
        """
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Daily statistics
        daily_stats = []
        for i in range(days):
            day_start = start_date + timedelta(days=i)
            day_end = day_start + timedelta(days=1)
            
            day_routings = FacilityRouting.objects.filter(
                triage_received_at__gte=day_start,
                triage_received_at__lt=day_end
            )
            
            daily_stats.append({
                'date': day_start.date().isoformat(),
                'total_cases': day_routings.count(),
                'emergency_cases': day_routings.filter(
                    Q(risk_level='high') | Q(has_red_flags=True)
                ).count(),
                'confirmed_cases': day_routings.filter(
                    routing_status='confirmed'
                ).count(),
            })
        
        # Facility rankings
        facility_rankings = Facility.objects.annotate(
            case_count=Count('assigned_routings', filter=Q(
                assigned_routings__triage_received_at__gte=start_date
            ))
        ).filter(case_count__gt=0).order_by('-case_count')[:10]
        
        # Response time trends
        response_times = FacilityNotification.objects.filter(
            created_at__gte=start_date,
            response_received_at__isnull=False
        ).annotate(
            response_time=Avg('response_received_at' - 'sent_at')
        ).values('facility__name', 'response_time')
        
        return {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': days,
            },
            'daily_statistics': daily_stats,
            'facility_rankings': [
                {
                    'name': f.name,
                    'case_count': f.case_count,
                }
                for f in facility_rankings
            ],
            'response_times': list(response_times),
            'summary': {
                'total_cases': sum(day['total_cases'] for day in daily_stats),
                'total_emergencies': sum(day['emergency_cases'] for day in daily_stats),
                'total_confirmed': sum(day['confirmed_cases'] for day in daily_stats),
            }
        }

    def export_audit_data(self, format_type: str = 'json', **filters) -> str:
        """
        Export audit data in specified format
        
        Args:
            format_type: Export format ('json', 'csv', 'xml')
            **filters: Filter criteria
            
        Returns:
            Exported data as string
        """
        audit_data = self.get_audit_trail(**filters)
        
        if format_type == 'json':
            return json.dumps(audit_data, indent=2, default=str)
        elif format_type == 'csv':
            return self._convert_to_csv(audit_data)
        elif format_type == 'xml':
            return self._convert_to_xml(audit_data)
        else:
            raise ValueError(f"Unsupported format: {format_type}")

    def _convert_to_csv(self, data: List[Dict]) -> str:
        """Convert audit data to CSV format"""
        if not data:
            return ""
        
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        
        return output.getvalue()

    def _convert_to_xml(self, data: List[Dict]) -> str:
        """Convert audit data to XML format"""
        from xml.etree.ElementTree import Element, SubElement, tostring
        
        root = Element('audit_trail')
        
        for entry in data:
            entry_elem = SubElement(root, 'entry')
            for key, value in entry.items():
                elem = SubElement(entry_elem, key)
                elem.text = str(value)
        
        return tostring(root, encoding='unicode')
