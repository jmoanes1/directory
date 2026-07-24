"""Admin configuration for Department model."""

from django.contrib import admin

from departments.models import Department


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "head", "employee_count", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "code", "description")
    raw_id_fields = ("head",)
