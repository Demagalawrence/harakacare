from django.contrib import admin
from .models import Facility, FacilityRouting

@admin.register(FacilityRouting)
class FacilityRoutingAdmin(admin.ModelAdmin):
    """Admin configuration for FacilityRouting model"""
    list_display = ('patient_token', 'assigned_facility', 'primary_symptom', 'risk_level', 'routing_status', 'patient_village', 'patient_district', 'triage_received_at')
    list_filter = ('routing_status', 'risk_level', 'assigned_facility')
    search_fields = ('patient_token', 'primary_symptom', 'patient_village', 'patient_district')
    ordering = ('-triage_received_at',)
    readonly_fields = ('triage_received_at',)

@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    """
    Admin configuration for Facility model.
    
    Provides comprehensive admin interface for managing healthcare facilities
    with filtering, searching, and ordering capabilities.
    """
    
    list_display = ('name', 'facility_type', 'district', 'phone_number', 'user', 'is_active', 'created_at')
    list_filter = ('facility_type', 'is_active', 'created_at')
    search_fields = ('name', 'address', 'district', 'phone_number')
    ordering = ('name',)
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'facility_type', 'district', 'address', 'phone_number', 'user')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """
        Show all facilities in admin, including inactive ones.
        """
        return super().get_queryset(request)
