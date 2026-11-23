from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class BaseModel(models.Model):
    """Abstract base model with common fields"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_created'
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_updated'
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']

    def delete(self, *args, **kwargs):
        """Soft delete"""
        self.is_active = False
        self.save()

    def hard_delete(self, *args, **kwargs):
        """Permanent delete"""
        super().delete(*args, **kwargs)


class StatusModel(BaseModel):  # Inherits from BaseModel
    """Model with status tracking"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('failed', 'Failed'),
        ('archived', 'Archived'),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )
    status_changed_at = models.DateTimeField(auto_now=True)
    status_reason = models.TextField(blank=True, null=True)

    class Meta:
        abstract = True

    def set_status(self, new_status, reason=''):
        """Update status with reason"""
        self.status = new_status
        self.status_reason = reason
        self.save()


class UserProfile(models.Model):
    """Extended user profile for facility association and roles"""
    
    class UserRole(models.TextChoices):
        ADMIN = 'admin', 'System Administrator'
        FACILITY_ADMIN = 'facility_admin', 'Facility Administrator'
        DOCTOR = 'doctor', 'Doctor'
        NURSE = 'nurse', 'Nurse'
        CLINICAL_OFFICER = 'clinical_officer', 'Clinical Officer'
        RECEPTIONIST = 'receptionist', 'Receptionist'
        STAFF = 'staff', 'General Staff'
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    
    facility = models.ForeignKey(
        'facilities.Facility',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff_members',
        help_text='Facility where this user works'
    )
    
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.STAFF,
        help_text='User role within the facility'
    )
    
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text='Contact phone number'
    )
    
    license_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Professional license number (for medical staff)'
    )
    
    department = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Department within the facility'
    )
    
    is_active_staff = models.BooleanField(
        default=True,
        help_text='Whether this staff member is currently active'
    )
    
    can_view_all_facilities = models.BooleanField(
        default=False,
        help_text='Can view cases from all facilities (admin only)'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
    
    def __str__(self):
        facility_name = self.facility.name if self.facility else 'No Facility'
        return f"{self.user.get_full_name() or self.user.username} - {facility_name}"
    
    def get_facility_cases_qs(self):
        """Get queryset of cases for this user's facility"""
        if not self.facility:
            return None
        from apps.triage.models import TriageSession
        return TriageSession.objects.filter(assigned_facility=self.facility)
    
    def can_view_case(self, case):
        """Check if user can view a specific case"""
        if self.can_view_all_facilities:
            return True
        if not self.facility:
            return False
        return case.assigned_facility == self.facility


class AuditLog(models.Model):
    """
    Audit trail for all sensitive actions in the system.
    Records who did what, when, and on which resource.
    """
    
    class ActionType(models.TextChoices):
        CREATE = 'create', 'Create'
        READ = 'read', 'Read'
        UPDATE = 'update', 'Update'
        DELETE = 'delete', 'Delete'
        LOGIN = 'login', 'Login'
        LOGOUT = 'logout', 'Logout'
        OVERRIDE = 'override', 'AI Recommendation Override'
        ESCALATE = 'escalate', 'Case Escalation'
        ASSIGN = 'assign', 'Case Assignment'
    
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        help_text='User who performed the action'
    )
    action = models.CharField(
        max_length=20,
        choices=ActionType.choices,
        help_text='Type of action performed'
    )
    resource_type = models.CharField(
        max_length=50,
        help_text='Type of resource (e.g., TriageSession, Facility, User)'
    )
    resource_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='ID of the affected resource'
    )
    resource_identifier = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='Human-readable identifier (e.g., patient token, not medical data)'
    )
    details = models.JSONField(
        default=dict,
        blank=True,
        help_text='Additional context (no sensitive medical data)'
    )
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        help_text='IP address of the client'
    )
    user_agent = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text='Client user agent string'
    )
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['resource_type', 'resource_id']),
            models.Index(fields=['action', '-timestamp']),
        ]
    
    def __str__(self):
        user = self.user.username if self.user else 'system'
        return f"{user} - {self.action} - {self.resource_type} - {self.timestamp}"