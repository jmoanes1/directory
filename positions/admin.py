"""Admin configuration for Position model."""

from django.contrib import admin

from positions.models import Position


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ("title", "department", "employee_count", "is_active", "created_at")
    list_filter = ("is_active", "department")
    search_fields = ("title", "description")
