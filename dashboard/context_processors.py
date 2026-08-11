"""Dashboard context processors for notifications and global layout data."""

from datetime import date

from django.db.models import Q
from django.utils import timezone

from attendance.services import count_employees_on_leave, sync_leave_employment_statuses
from employees.models import Employee


def notifications(request):
    """Provide birthday and work anniversary notifications."""
    if not request.user.is_authenticated:
        return {}

    today = date.today()
    birthdays = Employee.objects.filter(
        is_active=True,
        date_of_birth__month=today.month,
        date_of_birth__day=today.day,
    ).select_related("department")[:10]

    anniversaries = Employee.objects.filter(
        is_active=True,
        date_hired__month=today.month,
        date_hired__day=today.day,
    ).exclude(date_hired__year=today.year).select_related("department")[:10]

    return {
        "birthday_employees": birthdays,
        "anniversary_employees": anniversaries,
    }


def directory_layout(request):
    """Global sidebar team list and headline workforce stats."""
    if not request.user.is_authenticated:
        return {}

    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    today = now.date()
    sync_leave_employment_statuses(today)

    return {
        "sidebar_team_members": Employee.objects.filter(is_active=True).order_by("first_name")[:6],
        "site_total_employees": Employee.objects.count(),
        "site_new_hires": Employee.objects.filter(created_at__gte=month_start).count(),
        "site_on_leave_count": count_employees_on_leave(today),
    }
