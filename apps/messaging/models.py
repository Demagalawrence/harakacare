from django.db import models

class SMSState(models.Model):
    patient_token = models.CharField(max_length=40, unique=True)
    step = models.CharField(max_length=30, default="start")

    age_group = models.CharField(max_length=20, null=True, blank=True)
    complaint_group = models.CharField(max_length=30, null=True, blank=True)
    duration = models.CharField(max_length=20, null=True, blank=True)
    severity = models.CharField(max_length=20, null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.patient_token} - {self.step}"
