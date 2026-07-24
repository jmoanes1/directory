"""Attendance and leave management models."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class LeaveType(models.Model):
    """Configurable leave categories (Annual, Sick, etc.)."""

    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=10, unique=True)
    max_days_per_year = models.PositiveIntegerField(default=20)
    is_paid = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    color = models.CharField(max_length=7, default="#2563eb")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class LeaveRequest(models.Model):
    """Employee leave request with approval workflow."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="leave_requests",
    )
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT, related_name="requests")
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_leaves",
    )
    review_notes = models.TextField(blank=True)
    approval_email_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when approved-notification email was triggered.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["employee", "status"]),
            models.Index(fields=["start_date", "end_date"]),
        ]

    def __str__(self):
        return f"{self.employee.full_name} - {self.leave_type.name} ({self.status})"

    @property
    def total_days(self):
        return (self.end_date - self.start_date).days + 1

    def clean(self):
        super().clean()
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": "End date must be on or after start date."})


class AttendanceRecord(models.Model):
    """Daily attendance check-in/check-out records."""

    class Status(models.TextChoices):
        PRESENT = "present", "Present"
        ABSENT = "absent", "Absent"
        LATE = "late", "Late"
        HALF_DAY = "half_day", "Half Day"
        ON_LEAVE = "on_leave", "On Leave"

    class WorkMode(models.TextChoices):
        OFFICE = "office", "Office"
        WFH = "wfh", "Work From Home"

    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )
    date = models.DateField()
    time_in_morning = models.TimeField(null=True, blank=True)
    break_lunch = models.TimeField(null=True, blank=True)
    time_in_noon = models.TimeField(null=True, blank=True)
    time_out_afternoon = models.TimeField(null=True, blank=True)
    work_mode = models.CharField(
        max_length=20,
        choices=WorkMode.choices,
        default=WorkMode.OFFICE,
        db_index=True,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PRESENT, db_index=True)
    notes = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "employee__last_name"]
        unique_together = [("employee", "date")]
        indexes = [
            models.Index(fields=["date", "status"]),
            models.Index(fields=["employee", "date"]),
        ]

    def __str__(self):
        return f"{self.employee.full_name} - {self.date} ({self.status})"

    PUNCH_FIELDS = (
        ("time_in_morning", "Time In (Morning)"),
        ("break_lunch", "Break Lunch"),
        ("time_in_noon", "Time In (Noon)"),
        ("time_out_afternoon", "Time Out (Afternoon)"),
    )

    @property
    def next_punch_action(self):
        """Return the next attendance action key for today's workflow."""
        for field_name, _label in self.PUNCH_FIELDS:
            if not getattr(self, field_name):
                return field_name
        return None

    @property
    def is_day_complete(self):
        return self.next_punch_action is None and bool(self.time_in_morning)

    @property
    def work_mode_display(self):
        return self.get_work_mode_display()

    @property
    def is_wfh(self):
        return self.work_mode == self.WorkMode.WFH

    def _session_hours(self, start_time, end_time):
        from datetime import datetime, timedelta

        start = datetime.combine(self.date, start_time)
        end = datetime.combine(self.date, end_time)
        if end < start:
            end += timedelta(days=1)
        return (end - start).total_seconds() / 3600

    def _session_minutes(self, start_time, end_time):
        return int(round(self._session_hours(start_time, end_time) * 60))

    @property
    def morning_hours(self):
        if self.time_in_morning and self.break_lunch:
            return round(self._session_hours(self.time_in_morning, self.break_lunch), 2)
        return None

    @property
    def afternoon_hours(self):
        if self.time_in_noon and self.time_out_afternoon:
            return round(self._session_hours(self.time_in_noon, self.time_out_afternoon), 2)
        return None

    @property
    def break_minutes(self):
        if self.break_lunch and self.time_in_noon:
            return self._session_minutes(self.break_lunch, self.time_in_noon)
        return None

    @property
    def hours_worked(self):
        total = 0.0
        has_session = False

        morning = self.morning_hours
        afternoon = self.afternoon_hours
        if morning is not None:
            total += morning
            has_session = True
        if afternoon is not None:
            total += afternoon
            has_session = True

        return round(total, 2) if has_session else None

    @property
    def hours_worked_display(self):
        from attendance.time_utils import format_duration_hours
        return format_duration_hours(self.hours_worked)

    @property
    def morning_hours_display(self):
        from attendance.time_utils import format_duration_hours
        return format_duration_hours(self.morning_hours)

    @property
    def afternoon_hours_display(self):
        from attendance.time_utils import format_duration_hours
        return format_duration_hours(self.afternoon_hours)

    @property
    def break_duration_display(self):
        if self.break_minutes is None:
            return "—"
        h, m = divmod(self.break_minutes, 60)
        if h:
            return f"{h}h {m}m"
        return f"{m}m"
