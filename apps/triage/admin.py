"""
HarakaCare Custom Admin Interface
Purpose-built clinical dashboard for medical triage system
"""

from django.contrib import admin
from django.contrib.admin import AdminSite, ModelAdmin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.utils.html import format_html
from django.db.models import Count, Q, F
from django.utils import timezone
from datetime import datetime, timedelta
import csv
from django.http import HttpResponse

from .models import (
    TriageSession, TriageDecision, RedFlagDetection, 
    RiskClassification, ClinicalContext, AgentCommunicationLog
)
from apps.conversations.models import Conversation
from apps.facilities.models import (
    Facility, FacilityRouting, FacilityCandidate, 
    FacilityNotification, FacilityCapacityLog
)
from apps.core.models import UserProfile

class HarakaCareAdminSite(AdminSite):
    """Custom admin site for HarakaCare Clinical Dashboard"""
    
    site_header = "HarakaCare Clinical Dashboard"
    site_title = "HarakaCare Admin"
    index_title = "Dashboard"
    
    def index(self, request, extra_context=None):
        """Custom dashboard with clinical metrics"""
        if extra_context is None:
            extra_context = {}
        
        # Get today's metrics
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        
        # Dashboard metrics
        extra_context.update({
            'total_sessions_today': TriageSession.objects.filter(
                created_at__date=today
            ).count(),
            'high_risk_today': TriageSession.objects.filter(
                created_at__date=today,
                risk_level='high'
            ).count(),
            'emergency_today': TriageSession.objects.filter(
                created_at__date=today,
                red_flag_detection__isnull=False
            ).distinct().count(),
            'completed_this_week': TriageSession.objects.filter(
                session_status='completed',
                updated_at__date__gte=week_ago
            ).count(),
            'district_breakdown': self._get_district_breakdown(week_ago),
            'complaint_breakdown': self._get_complaint_breakdown(week_ago),
        })
        
        return super().index(request, extra_context)
    
    def _get_district_breakdown(self, since_date):
        """Get breakdown of cases by district"""
        return (
            TriageSession.objects.filter(
                created_at__date__gte=since_date,
                district__isnull=False
            )
            .values('district')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )
    
    def _get_complaint_breakdown(self, since_date):
        """Get breakdown of cases by complaint group"""
        return (
            TriageSession.objects.filter(
                created_at__date__gte=since_date,
                complaint_group__isnull=False
            )
            .values('complaint_group')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )


# Create custom admin site
harakacare_admin = HarakaCareAdminSite(name='harakacare_admin')


@admin.register(TriageSession, site=harakacare_admin)
class TriageSessionAdmin(ModelAdmin):
    """Custom admin for Triage Sessions with clinical dashboard feel"""
    
    list_display = [
        'patient_token_link', 'age_group', 'sex', 'complaint_group', 
        'risk_level_colored', 'follow_up_priority', 'district', 
        'channel', 'session_status', 'created_at'
    ]
    
    list_filter = [
        'risk_level', 'complaint_group', 'district', 'channel', 
        'session_status', 'created_at'
    ]
    
    search_fields = ['patient_token', 'district']
    
    ordering = ['-risk_level', '-created_at']
    
    readonly_fields = [
        'patient_token', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Patient Information', {
            'fields': ('patient_token', 'age_group', 'sex', 'patient_relation')
        }),
        ('Clinical Assessment', {
            'fields': (
                'complaint_text', 'complaint_group', 'risk_level', 
                'follow_up_priority', 'session_status'
            )
        }),
        ('Location & Contact', {
            'fields': ('district', 'village', 'patient_phone_number')
        }),
        ('Channel Information', {
            'fields': ('channel', 'session_metadata')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['export_to_csv']
    
    def patient_token_link(self, obj):
        """Make patient token clickable linking to detail view"""
        url = reverse('harakacare_admin:triage_triagesession_change', args=[obj.id])
        return format_html('<a href="{}" style="color: #075e54; font-weight: bold;">{}</a>', 
                          url, obj.patient_token[:12] + '...')
    patient_token_link.short_description = 'Patient Token'
    
    def risk_level_colored(self, obj):
        """Color coded risk level"""
        colors = {
            'high': '#dc3545',
            'medium': '#ffc107', 
            'low': '#28a745'
        }
        color = colors.get(obj.risk_level, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; '
            'border-radius: 12px; font-weight: bold;">{}</span>',
            color, obj.get_risk_level_display().upper()
        )
    risk_level_colored.short_description = 'Risk Level'
    
    def export_to_csv(self, request, queryset):
        """Export filtered results to CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="triage_sessions.csv"'
        
        writer = csv.writer(response)
        headers = [
            'Patient Token', 'Age Group', 'Sex', 'Complaint Group', 
            'Risk Level', 'Follow Up Priority', 'District', 'Channel', 
            'Session Status', 'Created At'
        ]
        writer.writerow(headers)
        
        for obj in queryset:
            writer.writerow([
                obj.patient_token,
                obj.get_age_group_display(),
                obj.get_sex_display(),
                obj.get_complaint_group_display() or 'N/A',
                obj.get_risk_level_display(),
                obj.get_follow_up_priority_display(),
                obj.district or 'N/A',
                obj.channel,
                obj.get_session_status_display(),
                obj.created_at
            ])
        
        return response
    export_to_csv.short_description = 'Export to CSV'
    
    def get_queryset(self, request):
        """Filter by assigned facility for facility users"""
        qs = super().get_queryset(request)
        
        # Check if user has a facility assignment
        try:
            user_profile = request.user.profile
            if user_profile.facility:
                # Filter to only show cases assigned to user's facility
                qs = qs.filter(assigned_facility=user_profile.facility)
        except UserProfile.DoesNotExist:
            # No profile means no restriction (for superusers/admins)
            pass
        
        return qs


@admin.register(TriageDecision, site=harakacare_admin)
class TriageDecisionAdmin(ModelAdmin):
    """Custom admin for Triage Decisions"""
    
    list_display = [
        'patient_token_link', 'facility_type_recommendation', 
        'recommended_action_truncated', 'final_risk_level', 'decision_timestamp'
    ]
    
    list_filter = ['facility_type_recommendation', 'final_risk_level']
    
    search_fields = ['triage_session__patient_token']
    
    readonly_fields = ['triage_session', 'decision_timestamp']
    
    def patient_token_link(self, obj):
        """Link back to triage session"""
        if obj.triage_session:
            url = reverse('harakacare_admin:triage_triagesession_change', args=[obj.triage_session.id])
            return format_html('<a href="{}">{}</a>', 
                              url, obj.triage_session.patient_token[:12] + '...')
        return 'N/A'
    patient_token_link.short_description = 'Patient Token'
    
    def recommended_action_truncated(self, obj):
        """Truncate recommended action to 100 characters"""
        if obj.recommended_action:
            action = obj.recommended_action[:100]
            if len(obj.recommended_action) > 100:
                action += '...'
            return action
        return 'N/A'
    recommended_action_truncated.short_description = 'Recommended Action'


@admin.register(Conversation, site=harakacare_admin)
class ConversationAdmin(ModelAdmin):
    """Custom admin for Conversations"""
    
    list_display = [
        'patient_token_link', 'turn_number', 'intent', 
        'completed_colored', 'created_at'
    ]
    
    list_filter = ['completed', 'intent']
    
    search_fields = ['patient_token']
    
    readonly_fields = ['created_at', 'updated_at']
    
    def patient_token_link(self, obj):
        """Link to patient token"""
        if obj.patient_token:
            # Try to find the related triage session
            try:
                from .models import TriageSession
                session = TriageSession.objects.filter(patient_token=obj.patient_token).first()
                if session:
                    url = reverse('harakacare_admin:triage_triagesession_change', args=[session.id])
                    return format_html('<a href="{}">{}</a>', 
                                      url, obj.patient_token[:12] + '...')
            except:
                pass
            return obj.patient_token[:12] + '...'
        return 'N/A'
    patient_token_link.short_description = 'Patient Token'
    
    def completed_colored(self, obj):
        """Show incomplete conversations in amber"""
        if obj.completed:
            return format_html('<span style="color: #28a745;">{}</span>', '✓ Completed')
        else:
            return format_html('<span style="color: #ffc107; font-weight: bold;">{}</span>', '⚠ Incomplete')
    completed_colored.short_description = 'Status'


# Inline admin classes for patient journey view
class TriageDecisionInline(admin.TabularInline):
    model = TriageDecision
    extra = 0
    readonly_fields = ['decision_timestamp']
    can_delete = False


class RedFlagDetectionInline(admin.TabularInline):
    model = RedFlagDetection
    extra = 0
    readonly_fields = ['created_at']
    can_delete = False


# Enhanced TriageSession admin with inline panels
class TriageSessionAdminWithInlines(TriageSessionAdmin):
    """Triage Session admin with inline panels for full patient journey"""
    
    inlines = [
        TriageDecisionInline,
        RedFlagDetectionInline
    ]
    
    # Note: ConversationInline removed because Conversation model
    # doesn't have a direct ForeignKey to TriageSession
    # Conversations are linked by patient_token, not by FK


# Register the enhanced version
harakacare_admin.unregister(TriageSession)
harakacare_admin.register(TriageSession, TriageSessionAdminWithInlines)


# Register other models
harakacare_admin.register(User, UserAdmin)
harakacare_admin.register(Group)


# Create admin groups and permissions
def create_admin_groups():
    """Create Facility Staff and HarakaCare Admin groups with appropriate permissions"""
    
    # Create groups if they don't exist
    facility_staff, created = Group.objects.get_or_create(name='Facility Staff')
    harakacare_admin_group, created = Group.objects.get_or_create(name='HarakaCare Admin')
    
    # Note: In a real implementation, you would assign specific permissions here
    # This would involve checking model permissions and assigning them appropriately

# FACILITY ADMIN CLASSES
# ============================================================================

@admin.register(Facility, site=harakacare_admin)
class FacilityAdmin(ModelAdmin):
    """Custom admin for Healthcare Facilities"""
    
    list_display = [
        'name', 'facility_type', 'district', 'capacity_status', 
        'emergency_capable', 'contact_info', 'is_active_status'
    ]
    
    list_filter = [
        'facility_type', 'district', 'is_active', 'ambulance_available',
        'created_at'
    ]
    
    search_fields = ['name', 'district', 'address']
    
    ordering = ['name']
    
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        """Filter to show only user's assigned facility"""
        qs = super().get_queryset(request)
        
        # Check if user has a facility assignment
        try:
            user_profile = request.user.profile
            if user_profile.facility:
                # Only show user's assigned facility
                qs = qs.filter(id=user_profile.facility.id)
        except UserProfile.DoesNotExist:
            # No profile means no restriction (for superusers/admins)
            pass
        
        return qs
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'facility_type', 'user', 'is_active')
        }),
        ('Location & Contact', {
            'fields': ('address', 'district', 'phone_number')
        }),
        ('GPS Coordinates', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('Capacity Information', {
            'fields': ('total_beds', 'available_beds', 'staff_count')
        }),
        ('Services & Operations', {
            'fields': (
                'services_offered', 'average_wait_time_minutes', 
                'ambulance_available'
            )
        }),
        ('Technical Settings', {
            'fields': ('notification_endpoint',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['export_to_csv', 'mark_active', 'mark_inactive']
    
    def capacity_status(self, obj):
        """Show capacity status with color coding"""
        if obj.total_beds is None or obj.available_beds is None:
            return format_html('<span style="color: #6c757d;">Unknown</span>')
        
        capacity_ratio = obj.available_beds / obj.total_beds if obj.total_beds > 0 else 0
        
        if capacity_ratio >= 0.5:
            color = '#28a745'  # Green
            status = 'Good'
        elif capacity_ratio >= 0.2:
            color = '#ffc107'  # Yellow
            status = 'Limited'
        else:
            color = '#dc3545'  # Red
            status = 'Critical'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} ({}/{})</span>',
            color, status, obj.available_beds, obj.total_beds
        )
    capacity_status.short_description = 'Capacity Status'
    
    def emergency_capable(self, obj):
        """Show if facility can handle emergencies"""
        if obj.can_handle_emergency():
            return format_html('<span style="color: #28a745;">{}</span>', '✓ Emergency Ready')
        return format_html('<span style="color: #dc3545;">{}</span>', '✗ Not Emergency Ready')
    emergency_capable.short_description = 'Emergency Ready'
    
    def contact_info(self, obj):
        """Show contact information"""
        if obj.phone_number:
            return format_html('<span>{}</span>', obj.phone_number)
        return 'N/A'
    contact_info.short_description = 'Phone'
    
    def is_active_status(self, obj):
        """Show active status with color"""
        if obj.is_active:
            return format_html('<span style="color: #28a745;">{}</span>', '● Active')
        return format_html('<span style="color: #dc3545;">{}</span>', '● Inactive')
    is_active_status.short_description = 'Status'
    
    def export_to_csv(self, request, queryset):
        """Export facilities to CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="facilities.csv"'
        
        writer = csv.writer(response)
        headers = [
            'Name', 'Type', 'District', 'Address', 'Phone', 
            'Total Beds', 'Available Beds', 'Staff Count', 
            'Ambulance Available', 'Is Active', 'Created At'
        ]
        writer.writerow(headers)
        
        for obj in queryset:
            writer.writerow([
                obj.name,
                obj.get_facility_type_display(),
                obj.district,
                obj.address,
                obj.phone_number,
                obj.total_beds,
                obj.available_beds,
                obj.staff_count,
                obj.ambulance_available,
                obj.is_active,
                obj.created_at
            ])
        
        return response
    export_to_csv.short_description = 'Export to CSV'
    
    def mark_active(self, request, queryset):
        """Mark selected facilities as active"""
        queryset.update(is_active=True)
    mark_active.short_description = 'Mark selected as active'
    
    def mark_inactive(self, request, queryset):
        """Mark selected facilities as inactive"""
        queryset.update(is_active=False)
    mark_inactive.short_description = 'Mark selected as inactive'


@admin.register(FacilityRouting, site=harakacare_admin)
class FacilityRoutingAdmin(ModelAdmin):
    """Custom admin for Facility Routing records"""
    
    list_display = [
        'patient_token_link', 'risk_level_badge', 'primary_symptom',
        'assigned_facility_link', 'routing_status_badge', 'priority_score',
        'triage_received_at'
    ]
    
    list_filter = [
        'risk_level', 'routing_status', 'booking_type', 'has_red_flags',
        'assigned_facility__facility_type', 'triage_received_at'
    ]
    
    search_fields = ['patient_token', 'primary_symptom', 'assigned_facility__name']
    
    ordering = ['-triage_received_at']
    
    readonly_fields = [
        'patient_token', 'triage_session_id', 'triage_received_at',
        'facility_notified_at', 'facility_confirmed_at', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Patient Information', {
            'fields': (
                'patient_token', 'triage_session_id', 'risk_level',
                'primary_symptom', 'secondary_symptoms', 'has_red_flags'
            )
        }),
        ('Demographics', {
            'fields': ('age_group', 'sex', 'patient_village', 'patient_district')
        }),
        ('Location', {
            'fields': ('patient_location_lat', 'patient_location_lng'),
            'classes': ('collapse',)
        }),
        ('Routing Decision', {
            'fields': (
                'assigned_facility', 'booking_type', 'routing_status',
                'facility_match_score', 'distance_km'
            )
        }),
        ('Timestamps', {
            'fields': (
                'triage_received_at', 'facility_notified_at',
                'facility_confirmed_at', 'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    actions = ['export_to_csv', 'mark_confirmed', 'mark_cancelled']
    
    def patient_token_link(self, obj):
        """Link to triage session if available"""
        if obj.triage_session_id:
            try:
                session = TriageSession.objects.filter(
                    patient_token=obj.patient_token
                ).first()
                if session:
                    url = reverse('harakacare_admin:triage_triagesession_change', args=[session.id])
                    return format_html(
                        '<a href="{}" style="color: #075e54; font-weight: bold;">{}</a>',
                        url, obj.patient_token[:12] + '...'
                    )
            except:
                pass
        return obj.patient_token[:12] + '...'
    patient_token_link.short_description = 'Patient Token'
    
    def risk_level_badge(self, obj):
        """Show risk level with color coding"""
        colors = {
            'high': '#dc3545',
            'medium': '#ffc107',
            'low': '#28a745'
        }
        color = colors.get(obj.risk_level, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; '
            'border-radius: 12px; font-weight: bold;">{}</span>',
            color, obj.get_risk_level_display().upper()
        )
    risk_level_badge.short_description = 'Risk Level'
    
    def assigned_facility_link(self, obj):
        """Link to assigned facility"""
        if obj.assigned_facility:
            url = reverse('harakacare_admin:facilities_facility_change', args=[obj.assigned_facility.id])
            return format_html(
                '<a href="{}" style="color: #007bff;">{}</a>',
                url, obj.assigned_facility.name
            )
        return 'Unassigned'
    assigned_facility_link.short_description = 'Assigned Facility'
    
    def routing_status_badge(self, obj):
        """Show routing status with color coding"""
        colors = {
            'pending': '#6c757d',
            'matching': '#17a2b8',
            'notified': '#ffc107',
            'confirmed': '#28a745',
            'rejected': '#dc3545',
            'completed': '#28a745',
            'cancelled': '#6c757d'
        }
        color = colors.get(obj.routing_status, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; '
            'border-radius: 12px; font-weight: bold;">{}</span>',
            color, obj.get_routing_status_display()
        )
    routing_status_badge.short_description = 'Status'
    
    def priority_score(self, obj):
        """Calculate and display priority score"""
        score = obj.get_priority_score()
        if score >= 200:
            color = '#dc3545'  # Emergency
        elif score >= 100:
            color = '#ffc107'  # High
        else:
            color = '#28a745'  # Normal
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, score
        )
    priority_score.short_description = 'Priority'
    
    def export_to_csv(self, request, queryset):
        """Export routing records to CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="facility_routings.csv"'
        
        writer = csv.writer(response)
        headers = [
            'Patient Token', 'Risk Level', 'Primary Symptom', 'Has Red Flags',
            'Assigned Facility', 'Routing Status', 'Booking Type',
            'Match Score', 'Distance (km)', 'Triage Received At'
        ]
        writer.writerow(headers)
        
        for obj in queryset:
            writer.writerow([
                obj.patient_token,
                obj.get_risk_level_display(),
                obj.primary_symptom,
                obj.has_red_flags,
                obj.assigned_facility.name if obj.assigned_facility else 'Unassigned',
                obj.get_routing_status_display(),
                obj.get_booking_type_display(),
                obj.facility_match_score,
                obj.distance_km,
                obj.triage_received_at
            ])
        
        return response
    export_to_csv.short_description = 'Export to CSV'
    
    def mark_confirmed(self, request, queryset):
        """Mark selected routings as confirmed"""
        queryset.update(routing_status='confirmed')
    mark_confirmed.short_description = 'Mark selected as confirmed'
    
    def mark_cancelled(self, request, queryset):
        """Mark selected routings as cancelled"""
        queryset.update(routing_status='cancelled')
    mark_cancelled.short_description = 'Mark selected as cancelled'


@admin.register(FacilityCandidate, site=harakacare_admin)
class FacilityCandidateAdmin(ModelAdmin):
    """Custom admin for Facility Candidates"""
    
    list_display = [
        'facility_link', 'routing_link', 'match_score_badge',
        'distance_display', 'compatibility_status', 'selection_reason'
    ]
    
    list_filter = [
        'has_capacity', 'offers_required_service', 'can_handle_emergency',
        'created_at'
    ]
    
    search_fields = ['facility__name', 'routing__patient_token']
    
    ordering = ['-match_score']
    
    readonly_fields = ['created_at']
    
    def facility_link(self, obj):
        """Link to facility"""
        url = reverse('harakacare_admin:facilities_facility_change', args=[obj.facility.id])
        return format_html(
            '<a href="{}" style="color: #007bff;">{}</a>',
            url, obj.facility.name
        )
    facility_link.short_description = 'Facility'
    
    def routing_link(self, obj):
        """Link to routing record"""
        url = reverse('harakacare_admin:facilities_facilityrouting_change', args=[obj.routing.id])
        return format_html(
            '<a href="{}" style="color: #075e54;">{}</a>',
            url, str(obj.routing.patient_token[:12]) + '...'
        )
    routing_link.short_description = 'Routing'
    
    def match_score_badge(self, obj):
        """Show match score with color coding"""
        try:
            score = float(obj.match_score) if obj.match_score is not None else 0.0
        except (ValueError, TypeError):
            score = 0.0
            
        if score >= 0.8:
            color = '#28a745'  # Excellent
        elif score >= 0.6:
            color = '#ffc107'  # Good
        elif score >= 0.4:
            color = '#fd7e14'  # Fair
        else:
            color = '#dc3545'  # Poor
        
        score_text = f"{score:.3f}"
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; '
            'border-radius: 12px; font-weight: bold;">{}</span>',
            color, score_text
        )
    match_score_badge.short_description = 'Match Score'
    
    def distance_display(self, obj):
        """Show distance with unit"""
        if obj.distance_km is not None:
            try:
                distance = float(obj.distance_km)
                distance_text = f"{distance:.1f} km"
                return distance_text
            except (ValueError, TypeError):
                return 'Unknown'
        return 'Unknown'
    distance_display.short_description = 'Distance'
    
    def compatibility_status(self, obj):
        """Show compatibility status"""
        checks = []
        if obj.has_capacity:
            checks.append(format_html('<span style="color: #28a745;">{}</span>', '✓ Capacity'))
        if obj.offers_required_service:
            checks.append(format_html('<span style="color: #28a745;">{}</span>', '✓ Service'))
        if obj.can_handle_emergency:
            checks.append(format_html('<span style="color: #28a745;">{}</span>', '✓ Emergency'))
        
        if checks:
            return ' '.join(checks)  # Join with spaces, no format_html needed
        return format_html('<span style="color: #dc3545;">{}</span>', '✗ No Compatibility')
    compatibility_status.short_description = 'Compatibility'


@admin.register(FacilityNotification, site=harakacare_admin)
class FacilityNotificationAdmin(ModelAdmin):
    """Custom admin for Facility Notifications"""
    
    list_display = [
        'facility_link', 'routing_link', 'notification_type_badge',
        'notification_status_badge', 'subject', 'sent_status', 'created_at'
    ]
    
    list_filter = [
        'notification_type', 'notification_status', 'facility',
        'created_at', 'sent_at'
    ]
    
    search_fields = ['facility__name', 'routing__patient_token', 'subject']
    
    ordering = ['-created_at']
    
    readonly_fields = [
        'routing', 'facility', 'notification_type', 'subject', 'message',
        'payload', 'facility_response', 'response_received_at',
        'acknowledged_at', 'sent_at', 'retry_count', 'error_message',
        'created_at', 'updated_at'
    ]
    
    def facility_link(self, obj):
        """Link to facility"""
        url = reverse('harakacare_admin:facilities_facility_change', args=[obj.facility.id])
        return format_html(
            '<a href="{}" style="color: #007bff;">{}</a>',
            url, obj.facility.name
        )
    facility_link.short_description = 'Facility'
    
    def routing_link(self, obj):
        """Link to routing record"""
        url = reverse('harakacare_admin:facilities_facilityrouting_change', args=[obj.routing.id])
        return format_html(
            '<a href="{}" style="color: #075e54;">{}</a>',
            url, obj.routing.patient_token[:12] + '...'
        )
    routing_link.short_description = 'Routing'
    
    def notification_type_badge(self, obj):
        """Show notification type with color"""
        colors = {
            'new_case': '#007bff',
            'confirmation': '#28a745',
            'cancellation': '#dc3545',
            'update': '#17a2b8',
            'reminder': '#ffc107'
        }
        color = colors.get(obj.notification_type, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; '
            'border-radius: 12px; font-weight: bold;">{}</span>',
            color, obj.get_notification_type_display()
        )
    notification_type_badge.short_description = 'Type'
    
    def notification_status_badge(self, obj):
        """Show notification status with color"""
        colors = {
            'pending': '#6c757d',
            'sent': '#28a745',
            'acknowledged': '#007bff',
            'failed': '#dc3545',
            'retrying': '#ffc107'
        }
        color = colors.get(obj.notification_status, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; '
            'border-radius: 12px; font-weight: bold;">{}</span>',
            color, obj.get_notification_status_display()
        )
    notification_status_badge.short_description = 'Status'
    
    def sent_status(self, obj):
        """Show sent status with timestamp"""
        if obj.sent_at:
            return format_html(
                '<span style="color: #28a745;">{}</span>', 
                f'✓ Sent {obj.sent_at.strftime("%H:%M")}'
            )
        return format_html('<span style="color: #6c757d;">{}</span>', 'Pending')
    sent_status.short_description = 'Sent'


@admin.register(FacilityCapacityLog, site=harakacare_admin)
class FacilityCapacityLogAdmin(ModelAdmin):
    """Custom admin for Facility Capacity Logs"""
    
    list_display = [
        'facility_link', 'capacity_snapshot', 'change_info',
        'change_reason', 'source', 'created_at'
    ]
    
    list_filter = [
        'facility', 'change_reason', 'source', 'created_at'
    ]
    
    search_fields = ['facility__name', 'change_reason', 'change_notes']
    
    ordering = ['-created_at']
    
    readonly_fields = ['created_at']
    
    def facility_link(self, obj):
        """Link to facility"""
        url = reverse('harakacare_admin:facilities_facility_change', args=[obj.facility.id])
        return format_html(
            '<a href="{}" style="color: #007bff;">{}</a>',
            url, obj.facility.name
        )
    facility_link.short_description = 'Facility'
    
    def capacity_snapshot(self, obj):
        """Show capacity snapshot"""
        if obj.total_beds is not None and obj.available_beds is not None:
            ratio = obj.available_beds / obj.total_beds if obj.total_beds > 0 else 0
            return format_html(
                '{}/{} beds ({}%)',
                obj.available_beds, obj.total_beds, int(ratio * 100)
            )
        return 'N/A'
    capacity_snapshot.short_description = 'Capacity'
    
    def change_info(self, obj):
        """Show change information"""
        if obj.beds_change != 0:
            change_type = '+' if obj.beds_change > 0 else ''
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}{}</span>',
                '#28a745' if obj.beds_change > 0 else '#dc3545',
                change_type, obj.beds_change
            )
        return 'No change'
    change_info.short_description = 'Bed Change'


# Call the function when admin is loaded - with error handling
try:
    create_admin_groups()
except Exception as e:
    print(f"⚠️  Could not create admin groups on startup: {e}")
    # Don't fail deployment - groups will be created when needed


# ============================================================================
# USER PROFILE ADMIN
# ============================================================================

@admin.register(UserProfile, site=harakacare_admin)
class UserProfileAdmin(ModelAdmin):
    """Custom admin for User Profiles - manages facility assignments"""
    
    list_display = [
        'user_info', 'facility_link', 'role_badge', 'department', 
        'phone_number', 'is_active_staff', 'created_at'
    ]
    
    list_filter = [
        'role', 'facility', 'is_active_staff', 'can_view_all_facilities', 
        'created_at'
    ]
    
    search_fields = [
        'user__username', 'user__first_name', 'user__last_name', 
        'user__email', 'facility__name', 'department'
    ]
    
    ordering = ['facility', 'role', 'user__first_name']
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'role', 'is_active_staff')
        }),
        ('Facility Assignment', {
            'fields': ('facility', 'department', 'can_view_all_facilities')
        }),
        ('Contact Information', {
            'fields': ('phone_number',)
        }),
        ('Professional Information', {
            'fields': ('license_number',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['mark_active', 'mark_inactive', 'grant_all_facilities', 'revoke_all_facilities']
    
    def user_info(self, obj):
        """Display user information with link to user admin"""
        user_url = reverse('harakacare_admin:auth_user_change', args=[obj.user.id])
        full_name = obj.user.get_full_name() or obj.user.username
        return format_html(
            '<a href="{}" style="color: #007bff;">{}</a><br><small>{}</small>',
            user_url, full_name, obj.user.email
        )
    user_info.short_description = 'User'
    
    def facility_link(self, obj):
        """Link to facility if assigned"""
        if obj.facility:
            facility_url = reverse('harakacare_admin:facilities_facility_change', args=[obj.facility.id])
            return format_html(
                '<a href="{}" style="color: #28a745;">{}</a>',
                facility_url, obj.facility.name
            )
        return format_html('<span style="color: #6c757d;">Unassigned</span>')
    facility_link.short_description = 'Facility'
    
    def role_badge(self, obj):
        """Show role with color coding"""
        colors = {
            'admin': '#dc3545',
            'facility_admin': '#6f42c1',
            'doctor': '#0d6efd',
            'nurse': '#198754',
            'clinical_officer': '#fd7e14',
            'receptionist': '#6c757d',
            'staff': '#6c757d'
        }
        color = colors.get(obj.role, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; '
            'border-radius: 12px; font-weight: bold;">{}</span>',
            color, obj.get_role_display()
        )
    role_badge.short_description = 'Role'
    
    def mark_active(self, request, queryset):
        """Mark selected profiles as active"""
        queryset.update(is_active_staff=True)
    mark_active.short_description = 'Mark selected as active'
    
    def mark_inactive(self, request, queryset):
        """Mark selected profiles as inactive"""
        queryset.update(is_active_staff=False)
    mark_inactive.short_description = 'Mark selected as inactive'
    
    def grant_all_facilities(self, request, queryset):
        """Grant all facilities view permission"""
        queryset.update(can_view_all_facilities=True)
    grant_all_facilities.short_description = 'Grant all facilities access'
    
    def revoke_all_facilities(self, request, queryset):
        """Revoke all facilities view permission"""
        queryset.update(can_view_all_facilities=False)
    revoke_all_facilities.short_description = 'Revoke all facilities access'
    
    def get_queryset(self, request):
        """Show staff from user's facility only (or all for superusers)"""
        qs = super().get_queryset(request)
        
        if not request.user.is_superuser:
            try:
                user_profile = request.user.profile
                if user_profile.facility:
                    # Only show staff from the same facility
                    qs = qs.filter(facility=user_profile.facility)
                else:
                    # No facility assigned - show none
                    qs = qs.none()
            except UserProfile.DoesNotExist:
                qs = qs.none()
        
        return qs