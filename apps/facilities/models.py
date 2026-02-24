from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


# Create your models here.


class Facility(models.Model):
    """
    Model representing a healthcare facility in the HarakaCare system.
    
    Stores information about medical facilities including hospitals, clinics,
    and other healthcare service providers.
    """
    
    FACILITY_TYPES = [
        ('hospital', 'Hospital'),
        ('clinic', 'Clinic'),
        ('urgent_care', 'Urgent Care'),
        ('specialty_center', 'Specialty Center'),
        ('diagnostic_center', 'Diagnostic Center'),
    ]
    
    name = models.CharField(
        'facility name',
        max_length=200,
        help_text='Official name of the healthcare facility'
    )
    
    facility_type = models.CharField(
        'facility type',
        max_length=20,
        choices=FACILITY_TYPES,
        default='clinic',
        help_text='Type of healthcare facility'
    )
    
    address = models.TextField(
        'address',
        help_text='Physical address of the facility'
    )
    
    phone_number = models.CharField(
        'phone number',
        max_length=20,
        blank=True,
        default='',
        help_text='Primary contact phone number'
    )
    
    # Location data
    latitude = models.FloatField(
        'latitude',
        null=True,
        blank=True,
        validators=[MinValueValidator(-90.0), MaxValueValidator(90.0)],
        help_text='GPS latitude coordinate'
    )
    
    longitude = models.FloatField(
        'longitude',
        null=True,
        blank=True,
        validators=[MinValueValidator(-180.0), MaxValueValidator(180.0)],
        help_text='GPS longitude coordinate'
    )
    
    # Capacity management
    total_beds = models.IntegerField(
        'total beds',
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text='Total number of beds available at the facility'
    )
    
    available_beds = models.IntegerField(
        'available beds',
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text='Number of beds currently available'
    )
    
    staff_count = models.IntegerField(
        'staff count',
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text='Number of medical staff on duty'
    )
    
    # Services offered
    services_offered = models.JSONField(
        'services offered',
        default=list,
        blank=True,
        help_text='List of medical services offered at the facility'
    )
    
    # Operational data
    average_wait_time_minutes = models.IntegerField(
        'average wait time (minutes)',
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text='Average patient wait time in minutes'
    )
    
    ambulance_available = models.BooleanField(
        'ambulance available',
        default=False,
        help_text='Whether ambulance service is available'
    )
    
    # Communication
    notification_endpoint = models.URLField(
        'notification endpoint',
        max_length=500,
        blank=True,
        null=True,
        default='',
        help_text='API endpoint for receiving notifications'
    )
    
    # Status
    is_active = models.BooleanField(
        'is active',
        default=True,
        help_text='Whether the facility is currently operational'
    )
    
    created_at = models.DateTimeField(
        'created at',
        auto_now_add=True
    )
    
    updated_at = models.DateTimeField(
        'updated at',
        auto_now=True
    )
    
    class Meta:
        verbose_name = 'facility'
        verbose_name_plural = 'facilities'
        ordering = ['name']
        indexes = [
            models.Index(fields=['facility_type']),
            models.Index(fields=['is_active']),
            models.Index(fields=['latitude', 'longitude']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_facility_type_display()})"
    
    def has_capacity(self, required_beds=1):
        """Check if facility has capacity for required beds"""
        if self.available_beds is None:
            return True
        return self.available_beds >= required_beds
    
    def offers_service(self, service):
        """Check if facility offers a specific service"""
        return service in self.services_offered
    
    def can_handle_emergency(self):
        """Check if facility can handle emergency cases"""
        return self.ambulance_available and self.offers_service('emergency')
    
    def distance_to(self, lat, lng):
        """Calculate distance to given coordinates using Haversine formula"""
        if not self.latitude or not self.longitude or lat is None or lng is None:
            return None
        
        from math import radians, cos, sin, asin, sqrt
        # Haversine formula to calculate distance
        lat1, lon1 = radians(self.latitude), radians(self.longitude)
        lat2, lon2 = radians(lat), radians(lng)
        
        dlat, dlon = lat2 - lat1, lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        km = 6371 * c
        return round(km, 2)
    
    def update_capacity(self, beds_change=0):
        """Update available beds count"""
        if self.available_beds is not None:
            self.available_beds = max(0, self.available_beds + beds_change)
            self.save()


# ============================================================================
# FACILITY AGENT MODELS
# ============================================================================

class FacilityRouting(models.Model):
    """
    Main routing record for patient case to facility
    Tracks complete routing workflow from triage to facility assignment
    """

    class BookingType(models.TextChoices):
        AUTOMATIC = 'automatic', 'Automatic'
        MANUAL = 'manual', 'Manual'

    class RoutingStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        MATCHING = 'matching', 'Matching Facilities'
        NOTIFIED = 'notified', 'Facility Notified'
        CONFIRMED = 'confirmed', 'Confirmed by Facility'
        REJECTED = 'rejected', 'Rejected by Facility'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    class RiskLevel(models.TextChoices):
        LOW = 'low', 'Low Risk'
        MEDIUM = 'medium', 'Medium Risk'
        HIGH = 'high', 'High Risk'

    # Patient case information (from Triage Agent)
    patient_token = models.CharField(
        'patient token',
        max_length=64,
        db_index=True,
        help_text='Anonymous patient identifier from Triage Agent'
    )

    triage_session_id = models.CharField(
        'triage session ID',
        max_length=100,
        blank=True,
        help_text='Reference to triage session'
    )

    # Triage data
    risk_level = models.CharField(
        'risk level',
        max_length=20,
        choices=RiskLevel.choices,
        help_text='Risk level from Triage Agent'
    )

    primary_symptom = models.CharField(
        'primary symptom',
        max_length=100,
        help_text='Primary symptom from triage'
    )

    secondary_symptoms = models.JSONField(
        'secondary symptoms',
        default=list,
        blank=True,
        help_text='Secondary symptoms from triage'
    )

    has_red_flags = models.BooleanField(
        'has red flags',
        default=False,
        help_text='Emergency red flags detected'
    )

    chronic_conditions = models.JSONField(
        'chronic conditions',
        default=list,
        blank=True,
        help_text='Chronic conditions from triage'
    )

    # Location information
    patient_district = models.CharField(
        'patient district',
        max_length=100,
        help_text='Patient district/area'
    )

    patient_location_lat = models.FloatField(
        'patient latitude',
        null=True,
        blank=True,
        help_text='Patient GPS latitude'
    )

    patient_location_lng = models.FloatField(
        'patient longitude',
        null=True,
        blank=True,
        help_text='Patient GPS longitude'
    )

    # Routing decisions
    assigned_facility = models.ForeignKey(
        'Facility',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_routings',
        verbose_name='assigned facility'
    )

    booking_type = models.CharField(
        'booking type',
        max_length=20,
        choices=BookingType.choices,
        help_text='Whether booking is automatic or manual'
    )

    routing_status = models.CharField(
        'routing status',
        max_length=20,
        choices=RoutingStatus.choices,
        default=RoutingStatus.PENDING
    )

    # Matching scores
    facility_match_score = models.FloatField(
        'facility match score',
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text='AI or rule-based matching score (0-1)'
    )

    distance_km = models.FloatField(
        'distance',
        null=True,
        blank=True,
        help_text='Distance to facility in kilometers'
    )

    # Timestamps
    triage_received_at = models.DateTimeField(
        'triage received at',
        auto_now_add=True,
        help_text='When triage data was received'
    )

    facility_notified_at = models.DateTimeField(
        'facility notified at',
        null=True,
        blank=True,
        help_text='When facility was notified'
    )

    facility_confirmed_at = models.DateTimeField(
        'facility confirmed at',
        null=True,
        blank=True,
        help_text='When facility confirmed booking'
    )

    created_at = models.DateTimeField(
        'created at',
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        'updated at',
        auto_now=True
    )

    class Meta:
        verbose_name = 'facility routing'
        verbose_name_plural = 'facility routings'
        ordering = ['-triage_received_at']
        indexes = [
            models.Index(fields=['patient_token']),
            models.Index(fields=['routing_status', 'triage_received_at']),
            models.Index(fields=['assigned_facility', 'routing_status']),
            models.Index(fields=['risk_level', 'triage_received_at']),
        ]

    def __str__(self):
        return f"Routing {self.patient_token[:8]} → {self.assigned_facility or 'Pending'} ({self.routing_status})"

    @property
    def is_emergency(self):
        """Check if this is an emergency case"""
        return self.has_red_flags or self.risk_level == self.RiskLevel.HIGH

    @property
    def requires_manual_confirmation(self):
        """Check if case requires manual facility confirmation"""
        return self.booking_type == self.BookingType.MANUAL and not self.is_emergency

    def get_priority_score(self):
        """Calculate routing priority score"""
        score = 0.0
        if self.risk_level == self.RiskLevel.HIGH:
            score += 100
        elif self.risk_level == self.RiskLevel.MEDIUM:
            score += 50
        else:
            score += 10

        if self.has_red_flags:
            score += 200

        return score


class FacilityCandidate(models.Model):
    """
    Candidate facility for routing with matching scores
    """

    routing = models.ForeignKey(
        FacilityRouting,
        on_delete=models.CASCADE,
        related_name='candidates'
    )

    facility = models.ForeignKey(
        'Facility',
        on_delete=models.CASCADE
    )

    # Matching scores
    match_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text='Overall match score (0-1)'
    )

    distance_km = models.FloatField(
        null=True,
        blank=True,
        help_text='Distance to patient in kilometers'
    )

    # Compatibility
    has_capacity = models.BooleanField(
        default=False,
        help_text='Facility has available capacity'
    )

    offers_required_service = models.BooleanField(
        default=False,
        help_text='Facility offers required services'
    )

    can_handle_emergency = models.BooleanField(
        default=False,
        help_text='Facility can handle emergency cases'
    )

    selection_reason = models.TextField(
        blank=True,
        help_text='Reason for facility selection'
    )

    created_at = models.DateTimeField(
        'created at',
        auto_now_add=True
    )

    class Meta:
        verbose_name = 'facility candidate'
        verbose_name_plural = 'facility candidates'
        unique_together = ['routing', 'facility']
        ordering = ['-match_score']

    def __str__(self):
        return f"{self.facility.name} - Score: {self.match_score:.3f}"


class FacilityNotification(models.Model):
    """
    Notification sent to facility with tracking
    """

    class NotificationType(models.TextChoices):
        NEW_CASE = 'new_case', 'New Case'
        CONFIRMATION = 'confirmation', 'Confirmation'
        CANCELLATION = 'cancellation', 'Cancellation'
        UPDATE = 'update', 'Update'
        REMINDER = 'reminder', 'Reminder'

    class NotificationStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SENT = 'sent', 'Sent'
        ACKNOWLEDGED = 'acknowledged', 'Acknowledged'
        FAILED = 'failed', 'Failed'
        RETRYING = 'retrying', 'Retrying'

    routing = models.ForeignKey(
        FacilityRouting,
        on_delete=models.CASCADE,
        related_name='notifications'
    )

    facility = models.ForeignKey(
        'Facility',
        on_delete=models.CASCADE
    )

    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.NEW_CASE
    )

    notification_status = models.CharField(
        max_length=20,
        choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING
    )

    subject = models.CharField(
        max_length=200,
        help_text='Notification subject line'
    )

    message = models.TextField(
        help_text='Notification message content'
    )

    payload = models.JSONField(
        default=dict,
        blank=True,
        help_text='Structured payload for API notifications'
    )

    # Response tracking
    facility_response = models.JSONField(
        null=True,
        blank=True,
        help_text='Response data from facility'
    )

    response_received_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When facility response was received'
    )

    acknowledged_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When notification was acknowledged'
    )

    # Delivery tracking
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When notification was sent'
    )

    retry_count = models.IntegerField(
        default=0,
        help_text='Number of retry attempts'
    )

    error_message = models.TextField(
        blank=True,
        help_text='Error message if sending failed'
    )

    created_at = models.DateTimeField(
        'created at',
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        'updated at',
        auto_now=True
    )

    class Meta:
        verbose_name = 'facility notification'
        verbose_name_plural = 'facility notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['facility', 'notification_status']),
            models.Index(fields=['routing', 'notification_type']),
            models.Index(fields=['notification_status', 'created_at']),
        ]

    def __str__(self):
        return f"{self.facility.name} - {self.get_notification_type_display()}"


class FacilityCapacityLog(models.Model):
    """
    Log of facility capacity changes for audit trail
    """

    facility = models.ForeignKey(
        'Facility',
        on_delete=models.CASCADE,
        related_name='capacity_logs'
    )

    # Capacity snapshot
    total_beds = models.IntegerField(
        null=True,
        help_text='Total beds at time of logging'
    )

    available_beds = models.IntegerField(
        null=True,
        help_text='Available beds at time of logging'
    )

    staff_count = models.IntegerField(
        null=True,
        help_text='Staff count at time of logging'
    )

    average_wait_time = models.IntegerField(
        null=True,
        help_text='Average wait time at time of logging'
    )

    # Change details
    beds_change = models.IntegerField(
        default=0,
        help_text='Number of beds added/removed'
    )

    change_reason = models.CharField(
        max_length=100,
        blank=True,
        help_text='Reason for capacity change'
    )

    change_notes = models.TextField(
        blank=True,
        help_text='Additional notes about the change'
    )

    source = models.CharField(
        max_length=50,
        default='manual',
        help_text='Source of the capacity update'
    )

    created_at = models.DateTimeField(
        'created at',
        auto_now_add=True
    )

    class Meta:
        verbose_name = 'facility capacity log'
        verbose_name_plural = 'facility capacity logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['facility', 'created_at']),
            models.Index(fields=['change_reason']),
            models.Index(fields=['source']),
        ]

    def __str__(self):
        return f"{self.facility.name} - {self.change_reason or 'Update'}"
