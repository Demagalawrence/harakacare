from django.db import models

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
        ('pharmacy', 'Pharmacy'),
        ('laboratory', 'Laboratory'),
        ('diagnostic_center', 'Diagnostic Center'),
        ('urgent_care', 'Urgent Care'),
        ('specialty_center', 'Specialty Center'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(
        max_length=200,
        help_text="Name of the healthcare facility"
    )
    facility_type = models.CharField(
        max_length=20,
        choices=FACILITY_TYPES,
        default='clinic',
        help_text="Type of healthcare facility"
    )
    address = models.TextField(
        help_text="Full physical address of the facility"
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="GPS latitude coordinate"
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="GPS longitude coordinate"
    )
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        help_text="Contact phone number for the facility"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the facility is currently active"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the facility was created"
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'Facility'
        verbose_name_plural = 'Facilities'

    def __str__(self):
        return f"{self.name} ({self.get_facility_type_display()})"
