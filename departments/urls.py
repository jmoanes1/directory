"""Department URL routes."""

from django.urls import path

from departments import views

app_name = "departments"

urlpatterns = [
    path("", views.department_list_view, name="list"),
    path("create/", views.department_create_view, name="create"),
    path("<int:pk>/edit/", views.department_edit_view, name="edit"),
    path("<int:pk>/delete/", views.department_delete_view, name="delete"),
]
