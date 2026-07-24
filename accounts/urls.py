"""Account URL routes."""

from django.urls import path

from accounts import views
from accounts import views_employee_accounts as ea_views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile_view, name="profile"),
    path("change-password/", views.change_password_view, name="change_password"),
    path("force-password-change/", ea_views.force_password_change_view, name="force_password_change"),
    path("access-denied/", ea_views.permission_denied_view, name="access_denied"),
    # Public registration disabled — admin-only account creation
    path("register/", views.register_disabled_view, name="register"),
    path("users/", views.user_list_view, name="user_list"),
    path("users/<int:pk>/toggle-active/", views.user_toggle_active_view, name="user_toggle_active"),
    path("users/<int:pk>/delete/", views.user_delete_view, name="user_delete"),
    # Employee account management (administrator only)
    path("employee-accounts/", ea_views.employee_account_list_view, name="employee_account_list"),
    path("employee-accounts/add/", ea_views.employee_account_create_view, name="employee_account_create"),
    path("employee-accounts/created/", ea_views.employee_account_created_view, name="employee_account_created"),
    path("employee-accounts/<int:pk>/", ea_views.employee_account_detail_view, name="employee_account_detail"),
    path("employee-accounts/<int:pk>/edit/", ea_views.employee_account_edit_view, name="employee_account_edit"),
    path("employee-accounts/<int:pk>/reset-password/", ea_views.employee_account_reset_password_view, name="employee_account_reset_password"),
    path("employee-accounts/<int:pk>/toggle-active/", ea_views.employee_account_toggle_active_view, name="employee_account_toggle_active"),
    path("employee-accounts/<int:pk>/delete/", ea_views.employee_account_delete_view, name="employee_account_delete"),
    path("employee-accounts/<int:pk>/send-credentials/", ea_views.employee_account_send_credentials_view, name="employee_account_send_credentials"),
    path(
        "password-reset/",
        views.CustomPasswordResetView.as_view(),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        views.CustomPasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "password-reset/confirm/<uidb64>/<token>/",
        views.CustomPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "password-reset/complete/",
        views.CustomPasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
]
