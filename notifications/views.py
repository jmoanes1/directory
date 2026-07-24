"""Notification center views."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from notifications.models import Notification


@login_required
def notification_list_view(request):
    """Full notification inbox with read/unread filter."""
    status = request.GET.get("status", "all")
    qs = Notification.objects.filter(recipient=request.user)
    if status == "unread":
        qs = qs.filter(is_read=False)
    elif status == "read":
        qs = qs.filter(is_read=True)

    return render(request, "notifications/list.html", {
        "notifications": qs[:100],
        "status": status,
        "unread_count": Notification.objects.filter(recipient=request.user, is_read=False).count(),
    })


@login_required
@require_POST
def notification_mark_read_view(request, pk):
    """Mark a single notification as read."""
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    if notification.link:
        return redirect(notification.link)
    return redirect("notifications:list")


@login_required
@require_POST
def notification_mark_all_read_view(request):
    """Mark all notifications as read for the current user."""
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return redirect("notifications:list")
