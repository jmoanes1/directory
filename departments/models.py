"""Department model and related logic."""

from django.core.exceptions import ValidationError
from django.db import models


class Department(models.Model):
    """Organizational department with optional department head."""

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True, blank=True)
    description = models.TextField(blank=True)
    head = models.ForeignKey(
        "employees.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="headed_departments",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["is_active", "name"]),
        ]
        verbose_name = "Department"
        verbose_name_plural = "Departments"

    def __str__(self):
        return self.name

    def clean(self):
        """Ensure department head belongs to this department."""
        super().clean()
        if self.head and self.head.department_id and self.head.department_id != self.pk:
            if self.pk and self.head.department_id != self.pk:
                raise ValidationError(
                    {"head": "Department head must belong to this department."}
                )

    @property
    def employee_count(self):
        return self.employees.filter(is_active=True).count()

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.name[:3].upper().replace(" ", "")
        super().save(*args, **kwargs)
