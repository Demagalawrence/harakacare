from django.contrib import admin
from .models import (
    Facility, FacilityRouting, FacilityCandidate,
    FacilityNotification, FacilityCapacityLog
)
from .forms import FacilityForm


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    """
    Admin configuration for Facility model.

    Provides comprehensive admin interface for managing healthcare facilities
    with filtering, searching, and ordering capabilities.
    """

    form = FacilityForm
    
    list_display = (
        'name', 'facility_type', 'district', 'phone_number',
        'total_beds', 'available_beds', 'staff_count',
        'average_wait_time_minutes', 'ambulance_available',
        'get_services_list', 'is_active', 'created_at',
    )
    list_filter = ('facility_type', 'is_active', 'ambulance_available', 'district', 'created_at')
    search_fields = ('name', 'address', 'district', 'phone_number')
    ordering = ('name',)
    readonly_fields = ('created_at', 'updated_at')

    def get_services_list(self, obj):
        """Display services as a comma-separated list"""
        services = obj.get_services_display()
        if services:
            return ', '.join(services[:3]) + ('...' if len(services) > 3 else '')
        return 'None'
    get_services_list.short_description = 'Services'

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'facility_type', 'address', 'district', 'phone_number')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('Capacity', {
            'fields': ('total_beds', 'available_beds', 'staff_count'),
            'classes': ('collapse',)
        }),
        ('Services & Operations', {
            'fields': ('services_offered', 'average_wait_time_minutes', 'ambulance_available'),
            'classes': ('collapse',)
        }),
        ('Communication', {
            'fields': ('notification_endpoint',),
            'classes': ('collapse',)
        }),
        ('Status & Timestamps', {
            'fields': ('is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        """Show all facilities in admin, including inactive ones."""
        return super().get_queryset(request)


@admin.register(FacilityRouting)
class FacilityRoutingAdmin(admin.ModelAdmin):
    list_display = (
        'patient_token', 'risk_level', 'primary_symptom', 'has_red_flags',
        'patient_district', 'assigned_facility', 'booking_type',
        'routing_status', 'facility_match_score', 'distance_km',
        'triage_received_at',
    )
    list_filter = ('routing_status', 'risk_level', 'booking_type', 'has_red_flags', 'triage_received_at')
    search_fields = ('patient_token', 'triage_session_id', 'primary_symptom', 'patient_district')
    ordering = ('-triage_received_at',)
    readonly_fields = ('triage_received_at', 'created_at', 'updated_at')

    fieldsets = (
        ('Patient Information', {
            'fields': (
                'patient_token', 'triage_session_id', 'risk_level',
                'primary_symptom', 'secondary_symptoms',
                'has_red_flags', 'chronic_conditions',
            )
        }),
        ('Location', {
            'fields': ('patient_district', 'patient_location_lat', 'patient_location_lng'),
            'classes': ('collapse',)
        }),
        ('Routing Decision', {
            'fields': (
                'assigned_facility', 'booking_type', 'routing_status',
                'facility_match_score', 'distance_km',
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': (
                'triage_received_at', 'facility_notified_at',
                'facility_confirmed_at', 'created_at', 'updated_at',
            ),
            'classes': ('collapse',)
        }),
    )


@admin.register(FacilityCandidate)
class FacilityCandidateAdmin(admin.ModelAdmin):
    list_display = (
        'routing', 'facility', 'match_score', 'distance_km',
        'has_capacity', 'offers_required_service', 'can_handle_emergency', 'created_at',
    )
    list_filter = ('has_capacity', 'offers_required_service', 'can_handle_emergency')
    search_fields = ('facility__name', 'routing__patient_token', 'selection_reason')
    ordering = ('-match_score',)
    readonly_fields = ('created_at',)

    fieldsets = (
        ('Routing & Facility', {
            'fields': ('routing', 'facility')
        }),
        ('Scores', {
            'fields': ('match_score', 'distance_km'),
        }),
        ('Compatibility', {
            'fields': ('has_capacity', 'offers_required_service', 'can_handle_emergency'),
        }),
        ('Details', {
            'fields': ('selection_reason', 'created_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(FacilityNotification)
class FacilityNotificationAdmin(admin.ModelAdmin):
    list_display = (
        'facility', 'routing', 'notification_type', 'notification_status',
        'subject', 'retry_count', 'sent_at', 'acknowledged_at', 'created_at',
    )
    list_filter = ('notification_type', 'notification_status', 'created_at')
    search_fields = ('facility__name', 'routing__patient_token', 'subject', 'message')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Routing & Facility', {
            'fields': ('routing', 'facility')
        }),
        ('Notification', {
            'fields': ('notification_type', 'notification_status', 'subject', 'message', 'payload'),
        }),
        ('Response', {
            'fields': ('facility_response', 'response_received_at', 'acknowledged_at'),
            'classes': ('collapse',)
        }),
        ('Delivery', {
            'fields': ('sent_at', 'retry_count', 'error_message'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(FacilityCapacityLog)
class FacilityCapacityLogAdmin(admin.ModelAdmin):
    list_display = (
        'facility', 'total_beds', 'available_beds', 'staff_count',
        'average_wait_time', 'beds_change', 'change_reason', 'source', 'created_at',
    )
    list_filter = ('source', 'change_reason', 'created_at')
    search_fields = ('facility__name', 'change_reason', 'change_notes')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)

    fieldsets = (
        ('Facility', {
            'fields': ('facility',)
        }),
        ('Capacity Snapshot', {
            'fields': ('total_beds', 'available_beds', 'staff_count', 'average_wait_time'),
        }),
        ('Change Details', {
            'fields': ('beds_change', 'change_reason', 'change_notes', 'source'),
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
