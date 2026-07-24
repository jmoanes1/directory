"""Dashboard URL routes."""

from django.urls import path

from dashboard import views

app_name = "dashboard"

urlpatterns = [
    path("", views.dashboard_home, name="home"),
    path("settings/", views.settings_view, name="settings"),
]
