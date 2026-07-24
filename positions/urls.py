"""Position URL routes."""

from django.urls import path

from positions import views

app_name = "positions"

urlpatterns = [
    path("", views.position_list_view, name="list"),
    path("create/", views.position_create_view, name="create"),
    path("<int:pk>/edit/", views.position_edit_view, name="edit"),
    path("<int:pk>/delete/", views.position_delete_view, name="delete"),
]
