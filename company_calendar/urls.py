"""Company calendar URL routes."""

from django.urls import path

from company_calendar import views

app_name = "company_calendar"

urlpatterns = [
    path("", views.calendar_view, name="home"),
    path("create/", views.calendar_entry_create_view, name="create"),
    path("<int:pk>/edit/", views.calendar_entry_edit_view, name="edit"),
    path("<int:pk>/delete/", views.calendar_entry_delete_view, name="delete"),
]
