"""Admin for attendance models."""

from django.contrib import admin

from attendance.models import AttendanceRecord, LeaveRequest, LeaveType


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "max_days_per_year", "is_paid", "is_active")


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ("employee", "leave_type", "start_date", "end_date", "status", "reviewed_by")
    list_filter = ("status", "leave_type")
    raw_id_fields = ("employee", "reviewed_by")


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = (
        "employee",
        "date",
        "work_mode",
        "time_in_morning",
        "break_lunch",
        "time_in_noon",
        "time_out_afternoon",
        "status",
    )
    list_filter = ("status", "work_mode", "date")
    raw_id_fields = ("employee",)
