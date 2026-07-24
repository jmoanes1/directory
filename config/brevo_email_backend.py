"""Send email through Brevo Transactional API (HTTPS — avoids SMTP IP blocks)."""

import json
import urllib.error
import urllib.request
from email.utils import parseaddr

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


def _parse_sender(from_email: str) -> dict:
    """Split 'Name <email@domain.com>' into Brevo sender dict."""
    name, email = parseaddr(from_email or settings.DEFAULT_FROM_EMAIL)
    if not email:
        email = "johnjaymoanes25@gmail.com"
    if not name:
        name = "HR"
    return {"name": name, "email": email}


class BrevoAPIEmailBackend(BaseEmailBackend):
    """
    Brevo REST API email backend.

    Uses BREVO_API_KEY from settings (xkeysib-... from Brevo dashboard).
    Prefer this over SMTP when Brevo blocks your IP with error 525.
    """

    api_url = "https://api.brevo.com/v3/smtp/email"

    def send_messages(self, email_messages):
        api_key = getattr(settings, "BREVO_API_KEY", "") or settings.EMAIL_HOST_PASSWORD
        if not api_key:
            if not self.fail_silently:
                raise ValueError("BREVO_API_KEY is not configured.")
            return 0

        sent = 0
        for message in email_messages:
            try:
                self._send_single(api_key, message)
                sent += 1
            except Exception:
                if not self.fail_silently:
                    raise
        return sent

    def _send_single(self, api_key: str, message):
        sender = _parse_sender(message.from_email)
        recipients = [{"email": addr} for addr in message.to if addr]
        if not recipients:
            return

        payload = {
            "sender": sender,
            "to": recipients,
            "subject": message.subject,
        }

        if message.body:
            if message.content_subtype == "html":
                payload["htmlContent"] = message.body
            else:
                payload["textContent"] = message.body

        if message.cc:
            payload["cc"] = [{"email": addr} for addr in message.cc if addr]
        if message.bcc:
            payload["bcc"] = [{"email": addr} for addr in message.bcc if addr]

        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.api_url,
            data=data,
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                "api-key": api_key,
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                if response.status not in (200, 201):
                    body = response.read().decode("utf-8", errors="replace")
                    raise urllib.error.HTTPError(
                        self.api_url, response.status, body, response.headers, None
                    )
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            if "unauthorized" in detail.lower() or "ip" in detail.lower():
                raise ConnectionError(
                    "Brevo rejected the request (IP or API key). "
                    "Run: python manage.py brevo_email_setup"
                ) from exc
            raise ConnectionError(f"Brevo API error {exc.code}: {detail}") from exc
