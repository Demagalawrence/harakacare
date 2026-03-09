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