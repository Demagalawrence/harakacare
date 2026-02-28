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