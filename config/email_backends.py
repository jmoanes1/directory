"""Email backends with Brevo support and local development fallback."""

import logging

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.backends.console import EmailBackend as ConsoleEmailBackend
from django.core.mail.backends.smtp import EmailBackend as SmtpEmailBackend

from config.brevo_email_backend import BrevoAPIEmailBackend

logger = logging.getLogger(__name__)


class VerboseConsoleEmailBackend(ConsoleEmailBackend):
    """Console backend that highlights password-reset links in the terminal."""

    def write_message(self, message):
        super().write_message(message)
        body = message.message().as_string()
        if "password-reset/confirm" in body or "password_reset_confirm" in body:
            for line in body.splitlines():
                if "password-reset" in line or "password_reset" in line:
                    if line.startswith("http"):
                        print("\n" + "=" * 60)
                        print("PASSWORD RESET LINK (copy into browser):")
                        print(line.strip())
                        print("=" * 60 + "\n")


def _brevo_smtp_backend(fail_silently=False):
    """Brevo SMTP relay (xsmtpsib- key + SMTP login)."""
    if not settings.EMAIL_HOST_USER and not settings.EMAIL_HOST_PASSWORD:
        return None
    return SmtpEmailBackend(fail_silently=fail_silently)


def _brevo_api_backend(fail_silently=False):
    """Brevo REST API (xkeysib- API key only)."""
    api_key = getattr(settings, "BREVO_API_KEY", "") or settings.EMAIL_HOST_PASSWORD
    if api_key.startswith("xkeysib"):
        return BrevoAPIEmailBackend(fail_silently=fail_silently)
    return None


def _should_use_console_fallback() -> bool:
    return getattr(settings, "EMAIL_CONSOLE_FALLBACK", False) and settings.DEBUG


class ResilientEmailBackend(BaseEmailBackend):
    """
    Deliver mail through Brevo SMTP (primary). Optionally try the Brevo API,
    then console output only when EMAIL_CONSOLE_FALLBACK=True in DEBUG.
    """

    def __init__(self, *args, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self._smtp = _brevo_smtp_backend(fail_silently=fail_silently)
        self._api = _brevo_api_backend(fail_silently=fail_silently)
        self._console = VerboseConsoleEmailBackend(fail_silently=fail_silently)

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        errors = []

        if self._smtp:
            try:
                sent = self._smtp.send_messages(email_messages)
                if sent:
                    logger.info("Email sent via Brevo SMTP.")
                    print("[Email] Sent via Brevo SMTP.")
                    return sent
            except Exception as exc:
                errors.append(f"SMTP: {exc}")
                logger.warning("Brevo SMTP failed: %s", exc)
                print(f"[Email] Brevo SMTP failed: {exc}")

        if self._api:
            try:
                sent = self._api.send_messages(email_messages)
                if sent:
                    logger.info("Email sent via Brevo API.")
                    print("[Email] Sent via Brevo API.")
                    return sent
            except Exception as exc:
                errors.append(f"API: {exc}")
                logger.warning("Brevo API failed: %s", exc)
                print(f"[Email] Brevo API failed: {exc}")

        if _should_use_console_fallback():
            logger.warning(
                "EMAIL_CONSOLE_FALLBACK is enabled — email was NOT delivered to inbox."
            )
            print(
                "\n[Email] WARNING: Brevo delivery failed. Printing to console only "
                "(set EMAIL_CONSOLE_FALLBACK=false and fix Brevo credentials/IP).\n"
            )
            return self._console.send_messages(email_messages)

        detail = "; ".join(errors) or "Brevo is not configured."
        if self.fail_silently:
            return 0
        raise ConnectionError(
            f"Could not send email via Brevo. {detail} "
            "Check EMAIL_HOST_USER, EMAIL_HOST_PASSWORD (xsmtpsib-...), and "
            "authorize your IP in Brevo (Settings -> Security -> Authorized IPs). "
            "Run: python manage.py brevo_email_setup"
        )
