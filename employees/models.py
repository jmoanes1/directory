"""Employee, activity log, and announcement models."""

import os
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import Max
from django.utils import timezone

from positions.models import Position


def employee_photo_path(instance, filename):
    """Generate secure upload path for employee photos."""
    ext = os.path.splitext(filename)[1].lower()
    return f"employees/photos/{instance.employee_id or uuid.uuid4().hex}{ext}"


def employee_document_path(instance, filename):
    """Secure path for employee document uploads."""
    ext = os.path.splitext(filename)[1].lower()
    emp_id = instance.employee.employee_id if instance.employee_id else uuid.uuid4().hex
    return f"employees/documents/{emp_id}/{instance.document_type}/{uuid.uuid4().hex}{ext}"


class Employee(models.Model):
    """Core employee record with full profile information."""

    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        OTHER = "other", "Other"
        PREFER_NOT = "prefer_not", "Prefer not to say"

    class EmploymentStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        ON_LEAVE = "on_leave", "On Leave"
        TERMINATED = "terminated", "Terminated"

    class WorkLocation(models.TextChoices):
        OFFICE = "office", "Office"
        REMOTE = "remote", "Remote"
        HYBRID = "hybrid", "Hybrid"

    class AvailabilityStatus(models.TextChoices):
        AVAILABLE = "available", "Available"
        BUSY = "busy", "Busy"
        ON_LEAVE = "on_leave", "On Leave"
        AWAY = "away", "Away"

    class EmployeeType(models.TextChoices):
        REGULAR = "regular", "Regular"
        PROBATIONARY = "probationary", "Probationary"
        CONTRACTUAL = "contractual", "Contractual"
        INTERN = "intern", "Intern"

    employee_id = models.CharField(max_length=20, unique=True, editable=False, db_index=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employee_profile",
    )
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    suffix = models.CharField(max_length=20, blank=True)
    email = models.EmailField(unique=True, db_index=True)
    phone_number = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, choices=Gender.choices, blank=True)
    address = models.TextField(blank=True)
    date_hired = models.DateField(default=timezone.now)
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.PROTECT,
        related_name="employees",
    )
    position = models.ForeignKey(
        "positions.Position",
        on_delete=models.PROTECT,
        related_name="employees",
    )
    manager = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="direct_reports",
    )
    employment_status = models.CharField(
        max_length=20,
        choices=EmploymentStatus.choices,
        default=EmploymentStatus.ACTIVE,
        db_index=True,
    )
    employee_type = models.CharField(
        max_length=20,
        choices=EmployeeType.choices,
        default=EmployeeType.REGULAR,
        db_index=True,
    )
    profile_photo = models.ImageField(
        upload_to=employee_photo_path,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "gif", "webp"])],
    )
    emergency_contact = models.CharField(max_length=200, blank=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    emergency_contact_relationship = models.CharField(max_length=50, blank=True)
    work_location = models.CharField(
        max_length=20,
        choices=WorkLocation.choices,
        default=WorkLocation.OFFICE,
        db_index=True,
    )
    availability_status = models.CharField(
        max_length=20,
        choices=AvailabilityStatus.choices,
        default=AvailabilityStatus.AVAILABLE,
        db_index=True,
    )
    bio = models.TextField(blank=True)
    linkedin_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    website_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        indexes = [
            models.Index(fields=["last_name", "first_name"]),
            models.Index(fields=["department", "is_active"]),
            models.Index(fields=["position", "is_active"]),
            models.Index(fields=["employment_status", "is_active"]),
            models.Index(fields=["date_hired"]),
        ]
        verbose_name = "Employee"
        verbose_name_plural = "Employees"

    def __str__(self):
        return f"{self.full_name} ({self.employee_id})"

    @property
    def full_name(self):
        parts = [self.first_name, self.middle_name, self.last_name, self.suffix]
        return " ".join(p for p in parts if p).strip()

    @property
    def initials(self):
        first = self.first_name[:1].upper() if self.first_name else ""
        last = self.last_name[:1].upper() if self.last_name else ""
        return f"{first}{last}"

    @property
    def profile_completion(self):
        """Percentage of key profile fields completed (portfolio dashboard metric)."""
        checks = [
            bool(self.first_name and self.last_name),
            bool(self.email),
            bool(self.phone_number),
            bool(self.date_of_birth),
            bool(self.gender),
            bool(self.address),
            bool(self.profile_photo),
            bool(self.bio),
            bool(self.emergency_contact or (self.emergency_contact_name and self.emergency_contact_phone)),
            bool(self.department_id and self.position_id),
            bool(self.work_location),
            bool(self.linkedin_url or self.github_url or self.website_url),
            self.documents.filter(document_type=EmployeeDocument.DocumentType.RESUME).exists(),
        ]
        return round((sum(checks) / len(checks)) * 100)

    @property
    def profile_completion_label(self):
        pct = self.profile_completion
        if pct >= 90:
            return "Complete"
        if pct >= 60:
            return "Good"
        if pct >= 30:
            return "In Progress"
        return "Needs Attention"

    @property
    def has_social_links(self):
        return bool(self.linkedin_url or self.github_url or self.twitter_url or self.website_url)

    def clean(self):
        super().clean()
        if self.position_id and self.department_id:
            position_dept_id = (
                Position.objects.filter(pk=self.position_id)
                .values_list("department_id", flat=True)
                .first()
            )
            if position_dept_id is None:
                raise ValidationError({"position": "Select a valid position."})
            if position_dept_id != self.department_id:
                raise ValidationError(
                    {"position": "Position must belong to the selected department."}
                )
        if self.manager_id and self.manager_id == self.pk:
            raise ValidationError({"manager": "Employee cannot be their own manager."})

    def save(self, *args, **kwargs):
        if not self.employee_id:
            self.employee_id = self._generate_employee_id()
        super().save(*args, **kwargs)

    @classmethod
    def _generate_employee_id(cls):
        """Auto-generate sequential employee ID (EMP-000001)."""
        last = cls.objects.aggregate(max_id=Max("employee_id"))["max_id"]
        if last and last.startswith("EMP-"):
            try:
                num = int(last.split("-")[1]) + 1
            except (IndexError, ValueError):
                num = cls.objects.count() + 1
        else:
            num = cls.objects.count() + 1
        return f"EMP-{num:06d}"


class ActivityLog(models.Model):
    """Audit trail for user and system actions."""

    class Action(models.TextChoices):
        CREATE = "create", "Create"
        UPDATE = "update", "Update"
        DELETE = "delete", "Delete"
        LOGIN = "login", "Login"
        LOGOUT = "logout", "Logout"
        VIEW = "view", "View"
        EXPORT = "export", "Export"
        ACTIVATE = "activate", "Activate"
        DEACTIVATE = "deactivate", "Deactivate"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_logs",
    )
    action = models.CharField(max_length=20, choices=Action.choices, db_index=True)
    model_name = models.CharField(max_length=50, blank=True)
    object_id = models.CharField(max_length=50, blank=True)
    object_repr = models.CharField(max_length=200, blank=True)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["model_name", "object_id"]),
        ]
        verbose_name = "Activity Log"
        verbose_name_plural = "Activity Logs"

    def __str__(self):
        return f"{self.get_action_display()} - {self.description[:50]}"


class CompanyAnnouncement(models.Model):
    """Company-wide announcements displayed on dashboard."""

    title = models.CharField(max_length=200)
    content = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="announcements",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Company Announcement"
        verbose_name_plural = "Company Announcements"

    def __str__(self):
        return self.title


class Skill(models.Model):
    """Skill catalog for the employee skills matrix."""

    class Category(models.TextChoices):
        TECHNICAL = "technical", "Technical"
        SOFT = "soft", "Soft Skills"
        LANGUAGE = "language", "Language"
        CERTIFICATION = "certification", "Certification"
        OTHER = "other", "Other"

    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.TECHNICAL, db_index=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return self.name


class EmployeeSkill(models.Model):
    """Links employees to skills with proficiency levels."""

    class Proficiency(models.TextChoices):
        BEGINNER = "1", "Beginner"
        INTERMEDIATE = "2", "Intermediate"
        ADVANCED = "3", "Advanced"
        EXPERT = "4", "Expert"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="skills")
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="employee_skills")
    proficiency = models.CharField(max_length=1, choices=Proficiency.choices, default=Proficiency.INTERMEDIATE)
    years_experience = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    notes = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("employee", "skill")]
        ordering = ["-proficiency", "skill__name"]

    def __str__(self):
        return f"{self.employee.full_name} - {self.skill.name} ({self.get_proficiency_display()})"

    @property
    def proficiency_level(self):
        return int(self.proficiency)


class EmployeeDocument(models.Model):
    """Employee file storage — resume, contracts, certificates, etc."""

    class DocumentType(models.TextChoices):
        RESUME = "resume", "Resume/CV"
        CONTRACT = "contract", "Contract"
        CERTIFICATE = "certificate", "Certificate"
        GOVERNMENT_ID = "government_id", "Government ID"
        TRAINING = "training", "Training Record"
        PERFORMANCE = "performance", "Performance Document"
        OTHER = "other", "Other"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="documents")
    document_type = models.CharField(max_length=20, choices=DocumentType.choices, db_index=True)
    title = models.CharField(max_length=200)
    file = models.FileField(
        upload_to=employee_document_path,
        validators=[FileExtensionValidator(
            allowed_extensions=["pdf", "doc", "docx", "jpg", "jpeg", "png", "webp"]
        )],
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_documents",
    )
    is_confidential = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.get_document_type_display()})"


class EmployeeTimelineEvent(models.Model):
    """Career timeline — promotions, transfers, awards, milestones."""

    class EventType(models.TextChoices):
        HIRE = "hire", "Hired"
        PROMOTION = "promotion", "Promotion"
        TRANSFER = "transfer", "Transfer"
        AWARD = "award", "Award"
        CERTIFICATION = "certification", "Certification"
        REVIEW = "review", "Performance Review"
        OTHER = "other", "Other"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="timeline_events")
    event_type = models.CharField(max_length=20, choices=EventType.choices, db_index=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    event_date = models.DateField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="timeline_events_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-event_date", "-created_at"]

    def __str__(self):
        return f"{self.employee.full_name} — {self.title}"


class EmployeeRecognition(models.Model):
    """Employee awards, kudos, and recognition records."""

    class Category(models.TextChoices):
        EXCELLENCE = "excellence", "Excellence"
        TEAMWORK = "teamwork", "Teamwork"
        INNOVATION = "innovation", "Innovation"
        LEADERSHIP = "leadership", "Leadership"
        MILESTONE = "milestone", "Milestone"
        OTHER = "other", "Other"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="recognitions")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.EXCELLENCE)
    awarded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recognitions_given",
    )
    awarded_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-awarded_date", "-created_at"]

    def __str__(self):
        return f"{self.title} — {self.employee.full_name}"
