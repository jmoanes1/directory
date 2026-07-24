from django.contrib import admin

from performance.models import EmployeeGoal, PerformanceReview


@admin.register(PerformanceReview)
class PerformanceReviewAdmin(admin.ModelAdmin):
    list_display = ("employee", "review_period", "overall_rating", "status", "reviewer", "period_end")
    list_filter = ("status", "overall_rating")
    raw_id_fields = ("employee", "reviewer")


@admin.register(EmployeeGoal)
class EmployeeGoalAdmin(admin.ModelAdmin):
    list_display = ("employee", "title", "status", "progress", "target_date")
    list_filter = ("status",)
    raw_id_fields = ("employee", "created_by")
