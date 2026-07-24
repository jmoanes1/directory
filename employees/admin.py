"""Admin configuration for employee models."""

from django.contrib import admin

from employees.models import (
    ActivityLog, CompanyAnnouncement, Employee,
    EmployeeDocument, EmployeeRecognition, EmployeeSkill,
    EmployeeTimelineEvent, Skill,
)


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "is_active")
    list_filter = ("category", "is_active")


@admin.register(EmployeeSkill)
class EmployeeSkillAdmin(admin.ModelAdmin):
    list_display = ("employee", "skill", "proficiency", "years_experience")
    list_filter = ("proficiency", "skill__category")
    raw_id_fields = ("employee", "skill")


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        "employee_id", "full_name", "email", "department", "position",
        "employment_status", "is_active", "date_hired",
    )
    list_filter = ("employment_status", "is_active", "department", "gender")
    search_fields = ("employee_id", "first_name", "last_name", "email")
    readonly_fields = ("employee_id", "created_at", "updated_at")
    raw_id_fields = ("manager", "user", "department", "position")


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("action", "user", "model_name", "object_repr", "ip_address", "created_at")
    list_filter = ("action", "model_name", "created_at")
    search_fields = ("description", "object_repr", "user__username")
    readonly_fields = ("user", "action", "model_name", "object_id", "object_repr", "description", "ip_address", "user_agent", "created_at")


@admin.register(CompanyAnnouncement)
class CompanyAnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "created_by", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("title", "content")


@admin.register(EmployeeDocument)
class EmployeeDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "employee", "document_type", "uploaded_by", "created_at")
    list_filter = ("document_type", "is_confidential")
    raw_id_fields = ("employee", "uploaded_by")


@admin.register(EmployeeTimelineEvent)
class EmployeeTimelineEventAdmin(admin.ModelAdmin):
    list_display = ("title", "employee", "event_type", "event_date")
    list_filter = ("event_type",)
    raw_id_fields = ("employee", "created_by")


@admin.register(EmployeeRecognition)
class EmployeeRecognitionAdmin(admin.ModelAdmin):
    list_display = ("title", "employee", "category", "awarded_date")
    list_filter = ("category",)
    raw_id_fields = ("employee", "awarded_by")
