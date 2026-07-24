"""Account forms for authentication and user management."""

import logging

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)

from accounts.password_reset_email import find_reset_users, send_password_reset_emails
from employees.models import Employee

logger = logging.getLogger(__name__)
User = get_user_model()


def resolve_login_username(identifier: str) -> str:
    """Map email (or employee email) to the account username for authentication."""
    identifier = (identifier or "").strip()
    if not identifier:
        return identifier

    if User.objects.filter(username__iexact=identifier).exists():
        return User.objects.get(username__iexact=identifier).get_username()

    user = User.objects.filter(email__iexact=identifier, is_active=True).first()
    if user:
        return user.get_username()

    employee = (
        Employee.objects.filter(
            email__iexact=identifier,
            is_active=True,
            user__isnull=False,
            user__is_active=True,
        )
        .select_related("user")
        .first()
    )
    if employee:
        return employee.user.get_username()

    return identifier


class StyledFormMixin:
    """Apply consistent CSS classes to form widgets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            css = "form-control"
            if isinstance(field.widget, forms.CheckboxInput):
                css = "form-check-input"
            elif isinstance(field.widget, forms.Select):
                css = "form-control form-select"
            field.widget.attrs.setdefault("class", css)
            if field.required and field.label:
                field.widget.attrs.setdefault("placeholder", field.label)


class LoginForm(StyledFormMixin, AuthenticationForm):
    """Allow sign-in with username or registered email (same as password reset)."""

    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": (
            "Incorrect username/email or password. "
            "Use the same email you used for password reset, or your account username."
        ),
    }

    username = forms.CharField(
        label="Username or email",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Username or email address",
                "autocomplete": "username",
            }
        ),
    )

    def clean(self):
        identifier = self.cleaned_data.get("username")
        if identifier:
            self.cleaned_data["username"] = resolve_login_username(identifier)
        return super().clean()


class UserRegistrationForm(StyledFormMixin, UserCreationForm):
    pass


class UserProfileForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        from django.contrib.auth import get_user_model

        model = get_user_model()
        fields = ("first_name", "last_name", "email", "phone", "avatar")
        widgets = {
            "avatar": forms.FileInput(attrs={"accept": "image/*", "class": "avatar-file-input"}),
        }

    def clean_avatar(self):
        avatar = self.cleaned_data.get("avatar")
        if avatar and hasattr(avatar, "size") and avatar.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Avatar must be under 5 MB.")
        return avatar


class CustomPasswordChangeForm(StyledFormMixin, PasswordChangeForm):
    pass


class CustomPasswordResetForm(StyledFormMixin, PasswordResetForm):
    email = forms.EmailField(
        label="Email address",
        widget=forms.EmailInput(
            attrs={"placeholder": "Your registered email address"},
        ),
    )

    def get_users(self, email):
        """Match active accounts by user or linked employee email."""
        return find_reset_users(email)

    def save(
        self,
        domain_override=None,
        subject_template_name=None,
        email_template_name=None,
        use_https=False,
        token_generator=None,
        from_email=None,
        request=None,
        html_email_template_name=None,
        extra_email_context=None,
    ):
        email = self.cleaned_data["email"]
        users = list(self.get_users(email))
        send_password_reset_emails(
            users=users,
            form_email=email,
            request=request,
            from_email=from_email,
            subject_template_name=subject_template_name
            or "accounts/emails/password_reset_subject.txt",
            email_template_name=email_template_name
            or "accounts/emails/password_reset_email.txt",
            html_email_template_name=html_email_template_name
            or "accounts/emails/password_reset_email.html",
            domain_override=domain_override,
            use_https=use_https,
            token_generator=token_generator,
            extra_email_context=extra_email_context,
        )


class CustomSetPasswordForm(StyledFormMixin, SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            "new_password1": "New password",
            "new_password2": "Confirm new password",
        }
        for name, placeholder in placeholders.items():
            if name in self.fields:
                self.fields[name].widget.attrs["placeholder"] = placeholder
        # Hide default validator help text on the set-password form.
        for field in self.fields.values():
            field.help_text = ""

    def save(self, commit=True):
        user = super().save(commit=commit)
        if not commit:
            return user
        update_fields = []
        if getattr(user, "must_change_password", False):
            user.must_change_password = False
            update_fields.append("must_change_password")
        if update_fields:
            user.save(update_fields=update_fields)
        user.refresh_from_db()
        return user
