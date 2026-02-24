"""
Facility Agent API Views
Handles inter-agent communication and facility routing operations
Based on: HarakaCare Facility Agent Data Requirements
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone
from datetime import timedelta

from .models import (
    Facility, FacilityRouting, FacilityCandidate, FacilityNotification, FacilityCapacityLog
)
from .tools.facility_matching import FacilityMatchingTool
from .tools.prioritization import PrioritizationTool
from .tools.notification_dispatch import NotificationDispatchTool
from .tools.logging_monitoring import LoggingMonitoringTool
from .serializers_facility_agent import (
    FacilityRoutingSerializer, FacilityCandidateSerializer,
    FacilityNotificationSerializer, FacilityCapacityLogSerializer,
    TriageIntakeSerializer, FacilityResponseSerializer
)


class FacilityAgentViewSet(viewsets.ModelViewSet):
    """
    Main Facility Agent API endpoint
    Handles routing requests from Triage Agent and facility communications
    """
    
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['routing_status', 'risk_level', 'booking_type']
    search_fields = ['patient_token', 'primary_symptom', 'patient_district']
    ordering_fields = ['triage_received_at', 'risk_level', 'priority_score']
    ordering = ['-triage_received_at']
    
    def get_queryset(self):
        return FacilityRouting.objects.all().select_related(
            'assigned_facility'
        ).prefetch_related(
            'candidates__facility', 'notifications__facility'
        )
    
    def get_serializer_class(self):
        if self.action == 'create':
            return TriageIntakeSerializer
        return FacilityRoutingSerializer
    
    def create(self, request, *args, **kwargs):
        """
        Handle new triage case from Triage Agent
        Creates routing and finds suitable facilities
        """
        serializer = TriageIntakeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create routing record
        routing = serializer.save()
        
        # Initialize tools
        matching_tool = FacilityMatchingTool()
        prioritization_tool = PrioritizationTool()
        
        # Find candidate facilities
        candidates = matching_tool.find_candidate_facilities(routing)
        
        # Prioritize candidates
        prioritized_candidates = prioritization_tool.prioritize_candidates(candidates, routing)
        
        # Save candidates
        for candidate in prioritized_candidates:
            candidate.save()
        
        # Determine booking type and get recommendation
        booking_type = prioritization_tool.determine_booking_type(routing)
        routing.booking_type = booking_type
        routing.save()
        
        recommendation = prioritization_tool.get_booking_recommendation(routing, prioritized_candidates)
        
        # Log routing decision
        logging_tool = LoggingMonitoringTool()
        logging_tool.log_routing_decision(
            routing, prioritized_candidates, 
            recommendation.get('recommended_facility'),
            recommendation.get('reason', '')
        )
        
        # Send notifications if automatic booking
        if booking_type == 'automatic' and recommendation.get('recommended_facility'):
            notification_tool = NotificationDispatchTool()
            notification = notification_tool.send_case_notification(
                routing, recommendation['recommended_facility']
            )
            
            # Update routing status
            routing.assigned_facility = recommendation['recommended_facility']
            routing.routing_status = FacilityRouting.RoutingStatus.NOTIFIED
            routing.facility_notified_at = timezone.now()
            routing.save()
        
        response_data = {
            'routing_id': routing.id,
            'patient_token': routing.patient_token,
            'booking_type': booking_type,
            'routing_status': routing.routing_status,
            'candidates_found': len(prioritized_candidates),
            'recommendation': recommendation,
        }
        
        return Response(response_data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def confirm_facility(self, request, pk=None):
        """
        Confirm facility assignment and send notifications
        Used for manual booking confirmation
        """
        routing = self.get_object()
        facility_id = request.data.get('facility_id')
        
        if not facility_id:
            return Response(
                {'error': 'facility_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            facility = Facility.objects.get(id=facility_id)
        except Facility.DoesNotExist:
            return Response(
                {'error': 'Facility not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Update routing
        routing.assigned_facility = facility
        routing.routing_status = FacilityRouting.RoutingStatus.NOTIFIED
        routing.facility_notified_at = timezone.now()
        routing.save()
        
        # Send notification
        notification_tool = NotificationDispatchTool()
        notification = notification_tool.send_case_notification(routing, facility)
        
        # Log action
        logging_tool = LoggingMonitoringTool()
        logging_tool.log_routing_decision(
            routing, [], facility, 
            f"Manual confirmation: {facility.name}"
        )
        
        return Response({
            'message': 'Facility confirmed and notified',
            'facility': facility.name,
            'notification_id': notification.id,
        })
    
    @action(detail=True, methods=['post'])
    def facility_response(self, request, pk=None):
        """
        Handle response from facility
        Updates routing status based on facility confirmation/rejection
        """
        routing = self.get_object()
        serializer = FacilityResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        response_data = serializer.validated_data
        facility_id = response_data.get('facility_id')
        response_type = response_data.get('response_type')  # 'confirm' or 'reject'
        
        # Find the notification
        try:
            notification = FacilityNotification.objects.get(
                routing=routing,
                facility_id=facility_id,
                notification_type='new_case'
            )
        except FacilityNotification.DoesNotExist:
            return Response(
                {'error': 'Notification not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Update notification with facility response
        notification.facility_response = response_data
        notification.response_received_at = timezone.now()
        
        if response_type == 'confirm':
            notification.notification_status = FacilityNotification.NotificationStatus.ACKNOWLEDGED
            notification.acknowledged_at = timezone.now()
            routing.routing_status = FacilityRouting.RoutingStatus.CONFIRMED
            routing.facility_confirmed_at = timezone.now()
            
            # Update facility capacity
            if response_data.get('beds_reserved', 0) > 0:
                facility = notification.facility
                facility.update_capacity(-response_data['beds_reserved'])
                
                # Log capacity change
                logging_tool = LoggingMonitoringTool()
                logging_tool.log_capacity_change(facility, {
                    'beds_change': -response_data['beds_reserved'],
                    'reason': 'patient_admission',
                    'source': 'facility_response',
                    'notes': f'Patient {routing.patient_token[:8]} admitted',
                })
        
        elif response_type == 'reject':
            notification.notification_status = FacilityRouting.RoutingStatus.REJECTED
            routing.routing_status = FacilityRouting.RoutingStatus.REJECTED
            
            # Try next facility if available
            self._try_alternative_facility(routing)
        
        notification.save()
        routing.save()
        
        # Log facility response
        logging_tool = LoggingMonitoringTool()
        logging_tool.log_facility_response(notification, response_data)
        
        return Response({
            'message': f'Facility response processed: {response_type}',
            'routing_status': routing.routing_status,
        })
    
    def _try_alternative_facility(self, routing: FacilityRouting):
        """Try to assign to alternative facility"""
        candidates = FacilityCandidate.objects.filter(
            routing=routing
        ).exclude(
            facility_id=routing.assigned_facility.id if routing.assigned_facility else None
        ).order_by('-match_score')
        
        if candidates.exists():
            next_candidate = candidates.first()
            routing.assigned_facility = next_candidate.facility
            routing.routing_status = FacilityRouting.RoutingStatus.PENDING
            
            # Send notification to alternative facility
            notification_tool = NotificationDispatchTool()
            notification_tool.send_case_notification(
                routing, next_candidate.facility
            )
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get facility agent statistics
        """
        days = int(request.query_params.get('days', 7))
        start_date = timezone.now() - timedelta(days=days)
        
        # Basic statistics
        total_routings = FacilityRouting.objects.filter(
            triage_received_at__gte=start_date
        ).count()
        
        emergency_routings = FacilityRouting.objects.filter(
            triage_received_at__gte=start_date,
            risk_level='high'
        ).count()
        
        confirmed_routings = FacilityRouting.objects.filter(
            triage_received_at__gte=start_date,
            routing_status='confirmed'
        ).count()
        
        # Notification statistics
        notification_tool = NotificationDispatchTool()
        notification_stats = notification_tool.get_notification_statistics(days=days)
        
        # Performance dashboard
        logging_tool = LoggingMonitoringTool()
        dashboard = logging_tool.get_performance_dashboard(days=days)
        
        return Response({
            'period': f'Last {days} days',
            'summary': {
                'total_routings': total_routings,
                'emergency_routings': emergency_routings,
                'confirmed_routings': confirmed_routings,
                'confirmation_rate': (confirmed_routings / total_routings * 100) if total_routings > 0 else 0,
            },
            'notifications': notification_stats,
            'performance': dashboard,
        })
    
    @action(detail=False, methods=['get'])
    def audit_trail(self, request):
        """
        Get audit trail for compliance and monitoring
        """
        patient_token = request.query_params.get('patient_token')
        facility_id = request.query_params.get('facility_id')
        days = int(request.query_params.get('days', 7))
        
        start_date = timezone.now() - timedelta(days=days)
        
        logging_tool = LoggingMonitoringTool()
        audit_data = logging_tool.get_audit_trail(
            patient_token=patient_token,
            facility_id=int(facility_id) if facility_id else None,
            start_date=start_date,
        )
        
        return Response({
            'audit_trail': audit_data,
            'period': f'Last {days} days',
        })
    
    @action(detail=False, methods=['post'])
    def update_capacity(self, request):
        """
        Update facility capacity (called by facilities or admin)
        """
        facility_id = request.data.get('facility_id')
        capacity_data = request.data.get('capacity', {})
        
        if not facility_id:
            return Response(
                {'error': 'facility_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            facility = Facility.objects.get(id=facility_id)
        except Facility.DoesNotExist:
            return Response(
                {'error': 'Facility not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Update facility capacity
        old_capacity = {
            'available_beds': facility.available_beds,
            'staff_count': facility.staff_count,
            'average_wait_time_minutes': facility.average_wait_time_minutes,
        }
        
        if 'available_beds' in capacity_data:
            facility.available_beds = capacity_data['available_beds']
        if 'staff_count' in capacity_data:
            facility.staff_count = capacity_data['staff_count']
        if 'average_wait_time_minutes' in capacity_data:
            facility.average_wait_time_minutes = capacity_data['average_wait_time_minutes']
        
        facility.save()
        
        # Log capacity change
        logging_tool = LoggingMonitoringTool()
        logging_tool.log_capacity_change(facility, {
            'beds_change': capacity_data.get('available_beds', facility.available_beds) - old_capacity['available_beds'],
            'reason': capacity_data.get('reason', 'manual_update'),
            'source': capacity_data.get('source', 'api_update'),
            'notes': capacity_data.get('notes', ''),
        })
        
        return Response({
            'message': 'Capacity updated successfully',
            'facility': facility.name,
            'old_capacity': old_capacity,
            'new_capacity': {
                'available_beds': facility.available_beds,
                'staff_count': facility.staff_count,
                'average_wait_time_minutes': facility.average_wait_time_minutes,
            }
        })


class FacilityNotificationViewSet(viewsets.ModelViewSet):
    """
    API for managing facility notifications
    """
    
    queryset = FacilityNotification.objects.all().select_related('routing', 'facility')
    serializer_class = FacilityNotificationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['notification_type', 'notification_status', 'facility', 'routing']
    search_fields = ['subject', 'facility__name', 'routing__patient_token']
    ordering_fields = ['created_at', 'sent_at', 'response_received_at']
    ordering = ['-created_at']
    
    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """Retry failed notification"""
        notification = self.get_object()
        
        if notification.notification_status != FacilityNotification.NotificationStatus.FAILED:
            return Response(
                {'error': 'Only failed notifications can be retried'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        notification_tool = NotificationDispatchTool()
        success = notification_tool.retry_failed_notifications()
        
        return Response({
            'message': 'Retry initiated',
            'retried_count': success,
        })
    
    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """Manually acknowledge notification"""
        notification = self.get_object()
        
        notification.notification_status = FacilityNotification.NotificationStatus.ACKNOWLEDGED
        notification.acknowledged_at = timezone.now()
        notification.save()
        
        return Response({
            'message': 'Notification acknowledged',
            'acknowledged_at': notification.acknowledged_at,
        })


class FacilityCapacityLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API for viewing facility capacity logs
    """
    
    queryset = FacilityCapacityLog.objects.all().select_related('facility')
    serializer_class = FacilityCapacityLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['facility', 'change_reason', 'source']
    search_fields = ['facility__name', 'change_notes']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
