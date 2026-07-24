"""Diagnose Brevo email and print IP whitelist instructions."""

import urllib.error
import urllib.request

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand


def fetch_public_ip() -> str:
    """Return this machine's outbound public IP."""
    for url in (
        "https://api.ipify.org",
        "https://ifconfig.me/ip",
    ):
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                return response.read().decode("utf-8").strip()
        except (urllib.error.URLError, TimeoutError):
            continue
    return "unknown"


class Command(BaseCommand):
    help = "Show your public IP for Brevo whitelist and test email sending"

    def handle(self, *args, **options):
        public_ip = fetch_public_ip()
        timeout_min = getattr(settings, "PASSWORD_RESET_TIMEOUT", 3600) // 60

        self.stdout.write(self.style.MIGRATE_HEADING("Brevo email setup"))
        self.stdout.write("")
        self.stdout.write(f"Your public IP (add this in Brevo): {self.style.WARNING(public_ip)}")
        self.stdout.write("")
        self.stdout.write("Fix SMTP error 525 — choose ONE option:")
        self.stdout.write("")
        self.stdout.write(self.style.HTTP_INFO("Option A — Authorize your IP (recommended)"))
        self.stdout.write("  1. Log in to https://app.brevo.com")
        self.stdout.write("  2. Go to Settings -> Security -> Authorized IPs")
        self.stdout.write(f"  3. Add IP address: {public_ip}")
        self.stdout.write("  4. Save, then run this command again with --test")
        self.stdout.write("")
        self.stdout.write(self.style.HTTP_INFO("Option B — Disable IP blocking (local dev only)"))
        self.stdout.write("  1. Brevo -> Settings -> Security -> Authorized IPs")
        self.stdout.write("  2. Click 'Deactivate blocking' for SMTP/API")
        self.stdout.write("  3. Run: python manage.py brevo_email_setup --test --to you@example.com")
        self.stdout.write("")
        self.stdout.write(self.style.HTTP_INFO("Option C — Use Brevo API backend (in .env)"))
        self.stdout.write("  1. Brevo -> Settings -> SMTP & API -> API Keys -> Generate")
        self.stdout.write("  2. Copy the xkeysib-... key into .env as BREVO_API_KEY")
        self.stdout.write("  3. Set EMAIL_BACKEND=config.brevo_email_backend.BrevoAPIEmailBackend")
        self.stdout.write("")
        self.stdout.write(f"Current EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
        self.stdout.write(f"FROM: {settings.DEFAULT_FROM_EMAIL}")
        self.stdout.write(f"Password reset token lifetime: {timeout_min} minutes")

        if options["test"]:
            recipient = options["to"]
            if not recipient:
                self.stdout.write(
                    self.style.ERROR(
                        "Provide --to with an email address to receive the test message."
                    )
                )
                return

            self.stdout.write("")
            self.stdout.write(f"Sending test email to {recipient}...")
            try:
                send_mail(
                    "Employee Directory — Brevo test",
                    (
                        "If you received this, Brevo SMTP is working.\n\n"
                        f"Password reset emails are sent to each employee's registered "
                        f"email address (not a shared inbox).\n"
                        f"Sent from: {settings.DEFAULT_FROM_EMAIL}\n"
                        f"Reset links expire after {timeout_min} minutes."
                    ),
                    None,
                    [recipient],
                    fail_silently=False,
                )
                self.stdout.write(
                    self.style.SUCCESS(f"Test email sent successfully to {recipient}.")
                )
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"Test failed: {exc}"))

    def add_arguments(self, parser):
        parser.add_argument(
            "--test",
            action="store_true",
            help="Send a test email after showing setup instructions",
        )
        parser.add_argument(
            "--to",
            dest="to",
            default="",
            help="Recipient for --test (required with --test)",
        )
