"""Audit logging utilities."""

from employees.models import ActivityLog


def log_activity(request, action, description, model_name="", object_id="", object_repr=""):
    """Create an audit log entry for the current request."""
    user = request.user if request.user.is_authenticated else None
    ip_address = _get_client_ip(request)
    user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]

    ActivityLog.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        object_id=str(object_id),
        object_repr=object_repr,
        description=description,
        ip_address=ip_address,
        user_agent=user_agent,
    )


def _get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
