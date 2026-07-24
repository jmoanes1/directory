"""Company calendar entries — holidays and company events."""

from django.conf import settings
from django.db import models


class CalendarEntry(models.Model):
    """A single holiday or company event on the shared calendar."""

    class EventType(models.TextChoices):
        HOLIDAY = "holiday", "Holiday"
        COMPANY_EVENT = "company_event", "Company Event"

    title = models.CharField(max_length=200)
    date = models.DateField(db_index=True)
    description = models.TextField(blank=True)
    event_type = models.CharField(
        max_length=20,
        choices=EventType.choices,
        default=EventType.HOLIDAY,
        db_index=True,
    )
    is_active = models.BooleanField(default=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="calendar_entries_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date", "title"]
        indexes = [
            models.Index(fields=["date", "event_type"]),
            models.Index(fields=["is_active", "date"]),
        ]
        verbose_name = "calendar entry"
        verbose_name_plural = "calendar entries"

    def __str__(self):
        return f"{self.title} ({self.date})"

    @property
    def type_css_class(self):
        """CSS modifier for color-coded calendar chips."""
        return f"cal-event--{self.event_type}"
