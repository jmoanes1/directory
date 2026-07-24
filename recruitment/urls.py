"""Recruitment URL routes."""

from django.urls import path

from recruitment import views

app_name = "recruitment"

urlpatterns = [
    path("", views.job_list_view, name="job_list"),
    path("pipeline/", views.pipeline_view, name="pipeline"),
    path("jobs/create/", views.job_create_view, name="job_create"),
    path("jobs/<int:pk>/", views.job_detail_view, name="job_detail"),
    path("jobs/<int:pk>/edit/", views.job_edit_view, name="job_edit"),
    path("jobs/<int:pk>/apply/", views.job_apply_view, name="job_apply"),
    path("applications/<int:pk>/", views.application_detail_view, name="application_detail"),
    path("onboarding/<int:pk>/toggle/", views.onboarding_task_toggle, name="onboarding_toggle"),
    path("candidates/<int:pk>/resume/", views.resume_download_view, name="resume_download"),
]
