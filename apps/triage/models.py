from django.db import models

# Create your models here.


from apps.patients.models import Patient
from apps.facilities.models import Facility

class Triage(models.Model):
    URGENCY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    facility = models.ForeignKey(Facility, on_delete=models.SET_NULL, null=True, blank=True)
    symptoms = models.TextField()
    urgency = models.CharField(max_length=10, choices=URGENCY_CHOICES, default='low')
    recommendation = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Triage for {self.patient} - {self.urgency}"
