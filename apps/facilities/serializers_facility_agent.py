"""
Facility Agent Serializers
Serializers for facility routing, booking, and inter-agent communication
Based on: HarakaCare Facility Agent Data Requirements
"""

from rest_framework import serializers
from django.utils import timezone
from .models import (
    Facility, FacilityRouting, FacilityCandidate, FacilityNotification, FacilityCapacityLog
)


class TriageIntakeSerializer(serializers.ModelSerializer):
    """
    Serializer for receiving triage data from Triage Agent
    Handles initial case intake and routing creation
    """
    
    class Meta:
        model = FacilityRouting
        fields = [
            'patient_token',
            'triage_session_id',
            'risk_level',
            'primary_symptom',
            'secondary_symptoms',
            'has_red_flags',
            'chronic_conditions',
            'patient_district',
            'patient_location_lat',
            'patient_location_lng',
        ]
    
    def validate_risk_level(self, value):
        """Validate risk level"""
        valid_levels = ['low', 'medium', 'high']
        if value not in valid_levels:
            raise serializers.ValidationError(f"Risk level must be one of: {valid_levels}")
        return value
    
    def validate_patient_token(self, value):
        """Validate patient token format"""
        if not value or len(value) < 8:
            raise serializers.ValidationError("Patient token must be at least 8 characters")
        return value
    
    def validate(self, data):
        """Cross-field validation"""
        # If location coordinates are provided, both must be present
        lat = data.get('patient_location_lat')
        lng = data.get('patient_location_lng')
        
        if (lat is not None and lng is None) or (lat is None and lng is not None):
            raise serializers.ValidationError(
                "Both latitude and longitude must be provided together"
            )
        
        # Validate coordinate ranges
        if lat is not None:
            if not (-90 <= lat <= 90):
                raise serializers.ValidationError("Latitude must be between -90 and 90")
            if not (-180 <= lng <= 180):
                raise serializers.ValidationError("Longitude must be between -180 and 180")
        
        return data


class FacilityCandidateSerializer(serializers.ModelSerializer):
    """
    Serializer for facility candidate information
    """
    facility_name = serializers.CharField(source='facility.name', read_only=True)
    facility_type = serializers.CharField(source='facility.facility_type', read_only=True)
    facility_address = serializers.CharField(source='facility.address', read_only=True)
    
    class Meta:
        model = FacilityCandidate
        fields = [
            'id',
            'facility',
            'facility_name',
            'facility_type',
            'facility_address',
            'match_score',
            'distance_km',
            'has_capacity',
            'offers_required_service',
            'can_handle_emergency',
            'selection_reason',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class FacilityRoutingSerializer(serializers.ModelSerializer):
    """
    Serializer for facility routing records
    """
    assigned_facility_name = serializers.CharField(
        source='assigned_facility.name', read_only=True
    )
    assigned_facility_address = serializers.CharField(
        source='assigned_facility.address', read_only=True
    )
    candidates = FacilityCandidateSerializer(
        many=True, read_only=True, source='candidates.all'
    )
    priority_score = serializers.FloatField(read_only=True)
    is_emergency = serializers.BooleanField(read_only=True)
    requires_manual_confirmation = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = FacilityRouting
        fields = [
            'id',
            'patient_token',
            'triage_session_id',
            'risk_level',
            'primary_symptom',
            'secondary_symptoms',
            'has_red_flags',
            'chronic_conditions',
            'patient_district',
            'patient_location_lat',
            'patient_location_lng',
            'assigned_facility',
            'assigned_facility_name',
            'assigned_facility_address',
            'booking_type',
            'routing_status',
            'facility_match_score',
            'distance_km',
            'triage_received_at',
            'facility_notified_at',
            'facility_confirmed_at',
            'candidates',
            'priority_score',
            'is_emergency',
            'requires_manual_confirmation',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'triage_received_at', 'facility_notified_at', 
            'facility_confirmed_at', 'created_at', 'updated_at'
        ]


class FacilityNotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for facility notifications
    """
    facility_name = serializers.CharField(source='facility.name', read_only=True)
    patient_token = serializers.CharField(source='routing.patient_token', read_only=True)
    risk_level = serializers.CharField(source='routing.risk_level', read_only=True)
    
    class Meta:
        model = FacilityNotification
        fields = [
            'id',
            'routing',
            'facility',
            'facility_name',
            'patient_token',
            'risk_level',
            'notification_type',
            'notification_status',
            'subject',
            'message',
            'payload',
            'facility_response',
            'response_received_at',
            'sent_at',
            'acknowledged_at',
            'retry_count',
            'error_message',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'response_received_at',
            'sent_at', 'acknowledged_at', 'retry_count'
        ]


class FacilityResponseSerializer(serializers.Serializer):
    """
    Serializer for handling facility responses to notifications
    """
    facility_id = serializers.IntegerField(required=True)
    response_type = serializers.ChoiceField(
        choices=['confirm', 'reject'],
        required=True
    )
    response_message = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000
    )
    beds_reserved = serializers.IntegerField(
        required=False,
        min_value=0,
        default=0
    )
    estimated_arrival = serializers.DateTimeField(
        required=False,
        allow_null=True
    )
    capacity_confirmed = serializers.BooleanField(
        required=False,
        default=True
    )
    additional_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000
    )
    
    def validate_facility_id(self, value):
        """Validate facility exists"""
        if not Facility.objects.filter(id=value).exists():
            raise serializers.ValidationError("Facility not found")
        return value


class FacilityCapacityUpdateSerializer(serializers.Serializer):
    """
    Serializer for facility capacity updates
    """
    facility_id = serializers.IntegerField(required=True)
    capacity = serializers.DictField(required=False)
    
    def validate_capacity(self, value):
        """Validate capacity fields"""
        if 'available_beds' in value:
            beds = value['available_beds']
            if beds < 0:
                raise serializers.ValidationError("Available beds cannot be negative")
        
        if 'staff_count' in value:
            staff = value['staff_count']
            if staff < 0:
                raise serializers.ValidationError("Staff count cannot be negative")
        
        if 'average_wait_time_minutes' in value:
            wait_time = value['average_wait_time_minutes']
            if wait_time < 0:
                raise serializers.ValidationError("Wait time cannot be negative")
        
        return value


class FacilityCapacityLogSerializer(serializers.ModelSerializer):
    """
    Serializer for facility capacity logs
    """
    facility_name = serializers.CharField(source='facility.name', read_only=True)
    facility_type = serializers.CharField(source='facility.facility_type', read_only=True)
    
    class Meta:
        model = FacilityCapacityLog
        fields = [
            'id',
            'facility',
            'facility_name',
            'facility_type',
            'total_beds',
            'available_beds',
            'staff_count',
            'average_wait_time',
            'beds_change',
            'change_reason',
            'change_notes',
            'source',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class FacilityBookingRequestSerializer(serializers.Serializer):
    """
    Serializer for booking requests from external systems
    """
    patient_token = serializers.CharField(max_length=64, required=True)
    facility_id = serializers.IntegerField(required=True)
    booking_type = serializers.ChoiceField(
        choices=['automatic', 'manual'],
        required=True
    )
    urgency_level = serializers.ChoiceField(
        choices=['routine', 'urgent', 'emergency'],
        required=True
    )
    special_requirements = serializers.JSONField(
        required=False,
        default=list
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000
    )


class FacilityStatusSerializer(serializers.ModelSerializer):
    """
    Serializer for facility status information
    """
    capacity_utilization = serializers.SerializerMethodField()
    can_accept_emergency = serializers.SerializerMethodField()
    services_offered_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Facility
        fields = [
            'id',
            'name',
            'facility_type',
            'address',
            'latitude',
            'longitude',
            'phone_number',
            'total_beds',
            'available_beds',
            'staff_count',
            'services_offered',
            'services_offered_display',
            'average_wait_time_minutes',
            'ambulance_available',
            'capacity_utilization',
            'can_accept_emergency',
            'is_active',
            'created_at',
        ]
    
    def get_capacity_utilization(self, obj):
        """Calculate capacity utilization percentage"""
        if obj.total_beds and obj.available_beds is not None:
            utilized = obj.total_beds - obj.available_beds
            return round((utilized / obj.total_beds) * 100, 1)
        return None
    
    def get_can_accept_emergency(self, obj):
        """Check if facility can accept emergency cases"""
        return obj.can_handle_emergency()
    
    def get_services_offered_display(self, obj):
        """Get human-readable services list"""
        if not obj.services_offered:
            return []
        
        service_map = {
            'general_medicine': 'General Medicine',
            'emergency': 'Emergency Care',
            'obstetrics': 'Obstetrics & Gynecology',
            'pediatrics': 'Pediatrics',
            'surgery': 'Surgery',
            'mental_health': 'Mental Health',
            'diagnostics': 'Diagnostics',
            'pharmacy': 'Pharmacy Services',
            'ambulance': 'Ambulance Services',
        }
        
        return [service_map.get(service, service) for service in obj.services_offered]


class FacilityMatchRequestSerializer(serializers.Serializer):
    """
    Serializer for facility matching requests
    """
    patient_token = serializers.CharField(max_length=64, required=True)
    risk_level = serializers.ChoiceField(
        choices=['low', 'medium', 'high'],
        required=True
    )
    primary_symptom = serializers.CharField(max_length=100, required=True)
    secondary_symptoms = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=list
    )
    has_red_flags = serializers.BooleanField(default=False)
    chronic_conditions = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=list
    )
    patient_district = serializers.CharField(max_length=100, required=True)
    patient_location_lat = serializers.FloatField(
        required=False,
        allow_null=True
    )
    patient_location_lng = serializers.FloatField(
        required=False,
        allow_null=True
    )
    max_distance_km = serializers.FloatField(
        required=False,
        default=50.0,
        min_value=1.0,
        max_value=200.0
    )
    max_candidates = serializers.IntegerField(
        required=False,
        default=5,
        min_value=1,
        max_value=20
    )


class FacilityMatchResponseSerializer(serializers.Serializer):
    """
    Serializer for facility matching responses
    """
    patient_token = serializers.CharField()
    request_timestamp = serializers.DateTimeField()
    candidates = FacilityCandidateSerializer(many=True)
    recommendation = serializers.DictField()
    processing_time_ms = serializers.IntegerField()
