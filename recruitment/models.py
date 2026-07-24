"""Recruitment models — job openings, candidates, pipeline, onboarding."""

import os
import uuid

from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone


def candidate_resume_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"recruitment/resumes/{uuid.uuid4().hex}{ext}"


class JobOpening(models.Model):
    """Published job vacancy."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"

    class EmploymentType(models.TextChoices):
        FULL_TIME = "full_time", "Full-time"
        PART_TIME = "part_time", "Part-time"
        CONTRACT = "contract", "Contract"
        INTERN = "intern", "Internship"

    title = models.CharField(max_length=200)
    department = models.ForeignKey(
        "departments.Department", on_delete=models.PROTECT, related_name="job_openings"
    )
    position = models.ForeignKey(
        "positions.Position", on_delete=models.SET_NULL, null=True, blank=True, related_name="job_openings"
    )
    description = models.TextField()
    requirements = models.TextField(blank=True)
    location = models.CharField(max_length=100, blank=True)
    employment_type = models.CharField(
        max_length=20, choices=EmploymentType.choices, default=EmploymentType.FULL_TIME
    )
    salary_range = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="job_postings"
    )
    opens_at = models.DateField(default=timezone.now)
    closes_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def application_count(self):
        return self.applications.count()


class Candidate(models.Model):
    """Applicant profile."""

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True, db_index=True)
    phone = models.CharField(max_length=20, blank=True)
    resume = models.FileField(
        upload_to=candidate_resume_path,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=["pdf", "doc", "docx"])],
    )
    linkedin_url = models.URLField(blank=True)
    source = models.CharField(max_length=100, blank=True, help_text="e.g. LinkedIn, Referral, Website")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} ({self.email})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class Application(models.Model):
    """Candidate application to a job — hiring pipeline stage."""

    class Status(models.TextChoices):
        APPLIED = "applied", "Applied"
        SCREENING = "screening", "Screening"
        INTERVIEW = "interview", "Interview"
        OFFER = "offer", "Offer"
        HIRED = "hired", "Hired"
        REJECTED = "rejected", "Rejected"

    job = models.ForeignKey(JobOpening, on_delete=models.CASCADE, related_name="applications")
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="applications")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.APPLIED, db_index=True)
    cover_letter = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_applications"
    )
    hr_notes = models.TextField(blank=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-applied_at"]
        unique_together = [("job", "candidate")]

    def __str__(self):
        return f"{self.candidate.full_name} → {self.job.title}"


class Interview(models.Model):
    """Scheduled interview for an application."""

    class Type(models.TextChoices):
        PHONE = "phone", "Phone"
        VIDEO = "video", "Video"
        ONSITE = "onsite", "On-site"

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="interviews")
    scheduled_at = models.DateTimeField()
    interview_type = models.CharField(max_length=20, choices=Type.choices, default=Type.VIDEO)
    location_or_link = models.CharField(max_length=300, blank=True)
    interviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="interviews"
    )
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["scheduled_at"]

    def __str__(self):
        return f"Interview: {self.application.candidate.full_name} @ {self.scheduled_at}"


class OnboardingTask(models.Model):
    """Checklist item for new hire onboarding."""

    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="onboarding_tasks", null=True, blank=True
    )
    employee = models.ForeignKey(
        "employees.Employee", on_delete=models.CASCADE, related_name="onboarding_tasks", null=True, blank=True
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_completed = models.BooleanField(default=False)
    due_date = models.DateField(null=True, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.title
