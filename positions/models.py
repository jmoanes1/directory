"""Position model linked to departments."""

from django.db import models


class Position(models.Model):
    """Job position within a department."""

    title = models.CharField(max_length=100)
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.CASCADE,
        related_name="positions",
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]
        unique_together = [("title", "department")]
        indexes = [
            models.Index(fields=["department", "is_active"]),
            models.Index(fields=["title"]),
        ]
        verbose_name = "Position"
        verbose_name_plural = "Positions"

    def __str__(self):
        return f"{self.title} ({self.department.name})"

    @property
    def employee_count(self):
        return self.employees.filter(is_active=True).count()
