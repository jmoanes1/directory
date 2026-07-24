from django.contrib import admin

from recruitment.models import Application, Candidate, Interview, JobOpening, OnboardingTask


@admin.register(JobOpening)
class JobOpeningAdmin(admin.ModelAdmin):
    list_display = ("title", "department", "status", "employment_type", "opens_at", "closes_at")
    list_filter = ("status", "employment_type", "department")
    search_fields = ("title", "description")


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ("full_name", "email", "phone", "source", "created_at")
    search_fields = ("first_name", "last_name", "email")


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("candidate", "job", "status", "applied_at", "reviewed_by")
    list_filter = ("status", "job")
    raw_id_fields = ("candidate", "job", "reviewed_by")


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ("application", "scheduled_at", "interview_type", "status", "interviewer")
    list_filter = ("status", "interview_type")


@admin.register(OnboardingTask)
class OnboardingTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "application", "employee", "is_completed", "due_date")
    list_filter = ("is_completed",)
