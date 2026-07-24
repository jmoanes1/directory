"""Secure password reset email delivery via Brevo (registered account email only)."""

import logging
from email.utils import parseaddr

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from employees.models import Employee

logger = logging.getLogger(__name__)
User = get_user_model()


def password_reset_sender_email():
    """Verified Brevo sender address (From header)."""
    _, addr = parseaddr(settings.DEFAULT_FROM_EMAIL)
    return addr or ""


def find_reset_users(email: str):
    """
    Return active users eligible for password reset.

    Matches the login email on the user account or the email on a linked,
    active employee record.
    """
    normalized = email.strip()
    if not normalized:
        return []

    seen_ids = set()
    users = []
    email_field = User.get_email_field_name()

    for user in User.objects.filter(is_active=True, **{f"{email_field}__iexact": normalized}):
        if user.has_usable_password() and user.pk not in seen_ids:
            users.append(user)
            seen_ids.add(user.pk)

    for employee in Employee.objects.filter(
        email__iexact=normalized,
        is_active=True,
        user__isnull=False,
        user__is_active=True,
    ).select_related("user"):
        user = employee.user
        if user.has_usable_password() and user.pk not in seen_ids:
            users.append(user)
            seen_ids.add(user.pk)

    return users


def resolve_delivery_email(user, form_email: str) -> str:
    """
    Send reset mail to an inbox the employee can access.

    When the request matches the linked employee record but the User account
    has a different email (common after profile updates), deliver to the
    User.email — that is the login identity and real mailbox.
    """
    email_field = User.get_email_field_name()
    user_email = (getattr(user, email_field, "") or "").strip()
    form_email = form_email.strip()

    if user_email.lower() == form_email.lower():
        return user_email

    profile = getattr(user, "employee_profile", None)
    emp_email = (profile.email or "").strip() if profile else ""

    if emp_email.lower() == form_email.lower():
        return user_email or emp_email

    return user_email or emp_email or form_email


def send_password_reset_emails(
    *,
    users,
    form_email,
    request=None,
    from_email=None,
    subject_template_name="accounts/emails/password_reset_subject.txt",
    email_template_name="accounts/emails/password_reset_email.txt",
    html_email_template_name="accounts/emails/password_reset_email.html",
    domain_override=None,
    use_https=False,
    token_generator=None,
    extra_email_context=None,
):
    """Send time-limited reset links to each user's registered email via Brevo."""
    if not users:
        logger.info(
            "Password reset requested for unknown or ineligible email (not disclosed to client)."
        )
        return

    sender = from_email or settings.DEFAULT_FROM_EMAIL
    _, sender_addr = parseaddr(sender)
    if not sender_addr:
        raise ValueError("DEFAULT_FROM_EMAIL must be configured with a verified Brevo sender.")

    token_generator = token_generator or default_token_generator
    timeout_minutes = getattr(settings, "PASSWORD_RESET_TIMEOUT", 3600) // 60

    if domain_override:
        site_name = domain = domain_override
    elif request is not None:
        site_name = "Employee Directory"
        domain = request.get_host()
    else:
        site_name = "Employee Directory"
        domain = "localhost:8000"

    for user in users:
        delivery_email = resolve_delivery_email(user, form_email)
        if not delivery_email:
            continue

        recipient_name = (
            user.get_full_name() or user.first_name or user.username or "there"
        ).strip()

        context = {
            "email": form_email,
            "domain": domain,
            "site_name": site_name,
            "uid": urlsafe_base64_encode(force_bytes(user.pk)),
            "user": user,
            "recipient_name": recipient_name,
            "token": token_generator.make_token(user),
            "protocol": "https" if use_https else "http",
            "reset_timeout_minutes": timeout_minutes,
            **(extra_email_context or {}),
        }
        subject = render_to_string(subject_template_name, context).strip()
        body = render_to_string(email_template_name, context)
        html_body = (
            render_to_string(html_email_template_name, context)
            if html_email_template_name
            else None
        )

        msg = EmailMultiAlternatives(subject, body, sender, [delivery_email])
        if html_body:
            msg.attach_alternative(html_body, "text/html")
        try:
            msg.send(fail_silently=False)
        except Exception:
            logger.exception(
                "Failed to send password reset email to %s for user %s",
                delivery_email,
                user.username,
            )
            raise
        logger.info(
            "Password reset email sent to %s for user %s",
            delivery_email,
            user.username,
        )
