"""Notification context for topbar badge and dropdown."""

from notifications.models import Notification


def notification_context(request):
    """Expose unread count and recent notifications in every authenticated page."""
    if not request.user.is_authenticated:
        return {}

    unread = Notification.objects.filter(recipient=request.user, is_read=False)
    return {
        "unread_notification_count": unread.count(),
        "recent_notifications": Notification.objects.filter(recipient=request.user)[:8],
    }
