"""Portal URL routes."""

from django.urls import path

from portal import views

app_name = "portal"

urlpatterns = [
    path("", views.self_service_home, name="home"),
    path("profile/", views.self_service_profile, name="profile"),
    path("documents/", views.self_service_documents, name="documents"),
    path("documents/<int:pk>/download/", views.document_download, name="document_download"),
    path("documents/<int:pk>/delete/", views.document_delete, name="document_delete"),
    path("manager/", views.manager_dashboard, name="manager"),
]
