"""Account security middleware."""

from django.shortcuts import redirect
from django.urls import reverse


class ForcePasswordChangeMiddleware:
    """Redirect users who must change their password before using the app."""

    ALLOWED_PREFIXES = (
        "/accounts/force-password-change/",
        "/accounts/logout/",
        "/static/",
        "/media/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated and getattr(user, "must_change_password", False):
            path = request.path
            if not any(path.startswith(prefix) for prefix in self.ALLOWED_PREFIXES):
                return redirect(reverse("accounts:force_password_change"))
        return self.get_response(request)
