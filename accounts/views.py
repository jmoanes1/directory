"""Account views: login, logout, registration, profile, password management."""

import logging

from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.contrib.auth.views import (
    INTERNAL_RESET_SESSION_TOKEN,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST

from accounts.password_reset_email import password_reset_sender_email
from accounts.forms import (
    CustomPasswordChangeForm,
    CustomPasswordResetForm,
    CustomSetPasswordForm,
    LoginForm,
    UserProfileForm,
    UserRegistrationForm,
)
from accounts.permissions import user_manager_required
from accounts.services_user_accounts import (
    delete_user_account,
    set_user_active,
    validate_user_account_action,
)
from employees.utils import log_activity

logger = logging.getLogger(__name__)


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard:home")

    form = LoginForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)
        log_activity(request, "login", f"User {user.username} logged in", "User", user.pk, str(user))
        if user.must_change_password:
            messages.warning(request, "You must change your temporary password before continuing.")
            return redirect("accounts:force_password_change")
        messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
        next_url = request.GET.get("next", "dashboard:home")
        return redirect(next_url)

    return render(request, "accounts/login.html", {"form": form})


@require_POST
def logout_view(request):
    username = request.user.username
    log_activity(request, "logout", f"User {username} logged out", "User", request.user.pk, username)
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect("accounts:login")


@login_required
def profile_view(request):
    user = request.user
    if request.method == "POST":
        # Remove photo when requested and no new file is being uploaded
        if request.POST.get("avatar_clear") == "1" and not request.FILES.get("avatar"):
            if user.avatar:
                user.avatar.delete(save=False)
            user.avatar = None
            user.save(update_fields=["avatar"])

    form = UserProfileForm(request.POST or None, request.FILES or None, instance=user)
    if request.method == "POST" and form.is_valid():
        form.save()
        log_activity(request, "update", "Updated user profile", "User", user.pk, user.username)
        messages.success(request, "Profile updated successfully.")
        return redirect("accounts:profile")

    return render(request, "accounts/profile.html", {"form": form})


@login_required
def change_password_view(request):
    form = CustomPasswordChangeForm(user=request.user, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        log_activity(request, "update", "Changed password", "User", user.pk, user.username)
        messages.success(request, "Password changed successfully.")
        return redirect("accounts:profile")

    return render(request, "accounts/change_password.html", {"form": form})


def register_disabled_view(request):
    """Public self-registration is disabled."""
    raise PermissionDenied(
        "Self-registration is disabled. Contact an administrator to create your account."
    )


@user_manager_required
def register_user_view(request):
    form = UserRegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        log_activity(request, "create", f"Registered user {user.username}", "User", user.pk, user.username)
        messages.success(request, f"User {user.username} registered successfully.")
        return redirect("accounts:user_list")

    return render(request, "accounts/register.html", {"form": form})


@user_manager_required
def user_list_view(request):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    users = (
        User.objects.select_related("employee_profile", "employee_profile__position")
        .order_by("-date_joined")
    )
    return render(request, "accounts/user_list.html", {"users": users})


@user_manager_required
@require_POST
def user_toggle_active_view(request, pk):
    from django.contrib.auth import get_user_model
    from django.shortcuts import get_object_or_404

    User = get_user_model()
    target = get_object_or_404(User, pk=pk)
    active = not target.is_active
    action = "deactivate" if not active else "activate"

    try:
        if not active:
            validate_user_account_action(actor=request.user, target=target, action="deactivate")
        set_user_active(target_user=target, active=active)
    except PermissionDenied as exc:
        messages.error(request, str(exc))
        return redirect("accounts:user_list")

    log_activity(
        request,
        "update",
        f"{action.title()}d user account @{target.username}",
        "User",
        target.pk,
        target.username,
    )
    messages.success(
        request,
        f"Account @{target.username} is now {'active' if active else 'inactive'}.",
    )
    return redirect("accounts:user_list")


@user_manager_required
@require_POST
def user_delete_view(request, pk):
    from django.contrib.auth import get_user_model
    from django.shortcuts import get_object_or_404

    User = get_user_model()
    target = get_object_or_404(User, pk=pk)
    username = target.username
    display = target.get_full_name() or username

    try:
        validate_user_account_action(actor=request.user, target=target, action="delete")
        delete_user_account(target)
    except PermissionDenied as exc:
        messages.error(request, str(exc))
        return redirect("accounts:user_list")

    log_activity(
        request,
        "delete",
        f"Deleted user account @{username}",
        "User",
        pk,
        username,
    )
    messages.success(request, f"User account for {display} (@{username}) has been deleted.")
    return redirect("accounts:user_list")


class StandaloneAuthLayoutMixin:
    """Use full-page auth layout even when a session is already active."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["standalone_auth"] = True
        return context


class PasswordResetEmailContextMixin(StandaloneAuthLayoutMixin):
    """Expose verified Brevo sender on password reset pages."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["password_reset_sender_email"] = password_reset_sender_email()
        return context


class CustomPasswordResetView(PasswordResetEmailContextMixin, PasswordResetView):
    template_name = "accounts/password_reset.html"
    email_template_name = "accounts/emails/password_reset_email.txt"
    html_email_template_name = "accounts/emails/password_reset_email.html"
    subject_template_name = "accounts/emails/password_reset_subject.txt"
    form_class = CustomPasswordResetForm
    success_url = reverse_lazy("accounts:password_reset_done")

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except Exception:
            logger.exception("Password reset email could not be delivered via Brevo")
            messages.error(
                self.request,
                "We could not send the reset email right now. "
                "Please try again in a few minutes or contact your administrator.",
            )
            return self.form_invalid(form)


class CustomPasswordResetDoneView(PasswordResetEmailContextMixin, PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class CustomPasswordResetConfirmView(StandaloneAuthLayoutMixin, PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    form_class = CustomSetPasswordForm
    success_url = reverse_lazy("accounts:password_reset_complete")

    def dispatch(self, request, *args, **kwargs):
        """
        Restore reset token from POST when the session cookie was lost
        (common when switching localhost / 127.0.0.1 or opening the link twice).
        """
        if request.method == "POST":
            reset_token = request.POST.get("reset_token", "").strip()
            uidb64 = kwargs.get("uidb64")
            if reset_token and uidb64:
                user = self.get_user(uidb64)
                if user is not None and default_token_generator.check_token(user, reset_token):
                    request.session[INTERNAL_RESET_SESSION_TOKEN] = reset_token
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if getattr(self, "validlink", False) and getattr(self, "user", None):
            context["reset_username"] = self.user.get_username()
            context["reset_token"] = self.request.session.get(
                INTERNAL_RESET_SESSION_TOKEN, ""
            )
        return context

    def form_valid(self, form):
        self.request.session["password_reset_username"] = form.user.get_username()
        self.request.session["password_reset_success"] = True
        logger.info("Password reset completed for user %s", form.user.username)
        return super().form_valid(form)


class CustomPasswordResetCompleteView(StandaloneAuthLayoutMixin, PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.session.get("password_reset_success"):
            messages.warning(
                request,
                "Complete the password reset form first. If your link expired, request a new one.",
            )
            return redirect("accounts:password_reset")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["reset_username"] = self.request.session.pop(
            "password_reset_username", ""
        )
        self.request.session.pop("password_reset_success", None)
        return context
