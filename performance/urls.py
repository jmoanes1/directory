"""Performance URL routes."""

from django.urls import path

from performance import views

app_name = "performance"

urlpatterns = [
    path("", views.performance_dashboard, name="dashboard"),
    path("reviews/create/", views.review_create_view, name="review_create"),
    path("reviews/<int:pk>/", views.review_detail_view, name="review_detail"),
    path("goals/", views.goal_list_view, name="goals"),
    path("goals/create/", views.goal_create_view, name="goal_create"),
]
