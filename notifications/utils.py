"""Helpers for creating in-app notifications."""

from django.contrib.auth import get_user_model
from django.db.models import Q

from notifications.models import Notification

User = get_user_model()


def notify_user(user, title, message, notification_type=Notification.Type.INFO, link=""):
    """Create a single notification for one user."""
    if not user or not user.is_active:
        return None
    return Notification.objects.create(
        recipient=user,
        title=title,
        message=message,
        notification_type=notification_type,
        link=link,
    )


def notify_users(users, title, message, notification_type=Notification.Type.INFO, link=""):
    """Bulk-create identical notifications for multiple users."""
    active_users = [u for u in users if u and u.is_active]
    if not active_users:
        return []
    return Notification.objects.bulk_create([
        Notification(
            recipient=user,
            title=title,
            message=message,
            notification_type=notification_type,
            link=link,
        )
        for user in active_users
    ])


def notify_hr_managers(title, message, notification_type=Notification.Type.INFO, link=""):
    """Notify all HR managers and super admins."""
    managers = User.objects.filter(is_active=True).filter(
        Q(role__in=["super_admin", "hr_manager"]) | Q(is_superuser=True)
    )
    return notify_users(managers, title, message, notification_type, link)


def notify_all_users(title, message, notification_type=Notification.Type.INFO, link=""):
    """Broadcast to every active user account."""
    users = User.objects.filter(is_active=True)
    return notify_users(users, title, message, notification_type, link)
