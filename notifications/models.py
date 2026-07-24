"""In-app notification center for HR events and system alerts."""

from django.conf import settings
from django.db import models


class Notification(models.Model):
    """Persistent notification delivered to a user inbox."""

    class Type(models.TextChoices):
        INFO = "info", "Info"
        LEAVE = "leave", "Leave"
        ANNOUNCEMENT = "announcement", "Announcement"
        SYSTEM = "system", "System"
        BIRTHDAY = "birthday", "Birthday"
        ANNIVERSARY = "anniversary", "Anniversary"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.INFO,
        db_index=True,
    )
    link = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read", "created_at"]),
        ]

    def __str__(self):
        return f"{self.title} → {self.recipient.username}"
