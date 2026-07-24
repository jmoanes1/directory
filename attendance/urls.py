"""Attendance URL routes."""

from django.urls import path

from attendance import views

app_name = "attendance"

urlpatterns = [
    path("", views.attendance_dashboard, name="dashboard"),
    path("punch/", views.attendance_punch, name="punch"),
    path("timesheet/", views.timesheet_view, name="timesheet"),
    path("leave/", views.leave_list_view, name="leave_list"),
    path("leave/request/", views.leave_request_view, name="leave_request"),
    path("leave/<int:pk>/review/", views.leave_review_view, name="leave_review"),
    path("report/", views.attendance_report_view, name="report"),
]
