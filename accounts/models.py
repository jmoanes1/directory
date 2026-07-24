"""Custom User model with role-based access."""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Extended user model with organizational roles."""

    class Role(models.TextChoices):
        SUPER_ADMIN = "super_admin", "Super Admin"
        HR_MANAGER = "hr_manager", "HR Manager"
        EMPLOYEE = "employee", "Employee"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.EMPLOYEE,
        db_index=True,
    )
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    is_registration_approved = models.BooleanField(default=False)
    must_change_password = models.BooleanField(
        default=False,
        help_text="Require password change on next login.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["username"]
        indexes = [
            models.Index(fields=["role", "is_active"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_super_admin(self):
        return self.role == self.Role.SUPER_ADMIN or self.is_superuser

    @property
    def is_hr_manager(self):
        return self.role == self.Role.HR_MANAGER

    @property
    def is_employee_role(self):
        return self.role == self.Role.EMPLOYEE

    @property
    def initials(self):
        first = self.first_name[:1].upper() if self.first_name else ""
        last = self.last_name[:1].upper() if self.last_name else ""
        if first or last:
            return f"{first}{last}"
        return self.username[:1].upper()

    def can_manage_employees(self):
        """HR Manager and Super Admin can manage employee records."""
        return self.is_super_admin or self.is_hr_manager

    def can_manage_departments(self):
        """Only Super Admin can create/edit departments."""
        return self.is_super_admin

    def can_manage_positions(self):
        """Only Super Admin can create/edit positions."""
        return self.is_super_admin

    def can_manage_users(self):
        """Super Admin and HR Manager can manage system user accounts."""
        return self.is_super_admin or self.is_hr_manager

    def can_manage_employee_accounts(self):
        """Super Admin and HR Manager can create and manage employee login accounts."""
        return self.is_super_admin or self.is_hr_manager

    def can_manage_calendar(self):
        """HR Manager and Super Admin can manage company calendar entries."""
        return self.is_super_admin or self.is_hr_manager
