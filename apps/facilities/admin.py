from django.contrib import admin
from .models import Facility


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    """
    Admin configuration for Facility model.
    
    Provides comprehensive admin interface for managing healthcare facilities
    with filtering, searching, and ordering capabilities.
    """
    
    list_display = ('name', 'facility_type', 'phone_number', 'is_active', 'created_at')
    list_filter = ('facility_type', 'is_active', 'created_at')
    search_fields = ('name', 'address', 'phone_number')
    ordering = ('name',)
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'facility_type', 'address', 'phone_number')
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
