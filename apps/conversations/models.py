import uuid
from django.db import models


class Conversation(models.Model):
    """
    Represents one patient chat session.
    This replaces your cache ConversationState persistence.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # same token you already use
    patient_token = models.CharField(max_length=50, db_index=True)

    # agent state
    intent = models.CharField(max_length=20, default="routine")
    turn_number = models.IntegerField(default=0)
    completed = models.BooleanField(default=False)

    # stores ExtractedInfo dataclass as JSON
    extracted_state = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Conversation {self.patient_token} ({self.intent})"


class Message(models.Model):
    """
    Each chat message (patient OR AI)
    """

    ROLE_CHOICES = [
        ("patient", "Patient"),
        ("agent", "Agent"),
    ]

    conversation = models.ForeignKey(
        Conversation,
        related_name="messages",
        on_delete=models.CASCADE
    )

    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    turn = models.IntegerField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["turn"]  # important for rebuilding context

    def __str__(self):
        return f"{self.role}: {self.content[:40]}"
